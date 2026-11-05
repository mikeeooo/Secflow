"""Assessment and review orchestration over local files plus temporary process memory.

At startup the service loads the demonstration dataset (runtime files only), the frozen model
bundle, the policy and its validated operating point, and the trusted security-evidence stream.
It replays every baseline request through the shared assessment pipeline, each one seeing only
its own event-time snapshot. Simulations then append to a temporary overlay of the same
history index; they never rewrite baseline files and never retrain a model.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np

from backend import views
from backend.analytics import ClusterGraphBuilder, dashboard
from backend.schemas import (
    AccountPage,
    AccountSummary,
    AssessmentDetail,
    Investigation,
    PartyRef,
    ReviewRequest,
    SimulationRequest,
    TransactionPage,
)
from config.settings import Settings
from ml.assess import assess_batch, assess_one, build_evidence_store
from ml.model import BundleError, ModelBundle, load_bundle, load_operating_point
from ml.policy import OperatingPoint, load_policy
from storage.dataset import Dataset, load_dataset
from storage.history import HistoryIndex
from storage.memory import (
    COMPLETED_OUTCOMES,
    OUTCOME_FOR_DECISION,
    AssessmentRecord,
    ConflictError,
    MemoryState,
    NotFoundError,
    ReviewRecord,
    utc_now_iso,
)
from storage.records import (
    KEY_SCALE,
    AuthEvent,
    Counterparty,
    PaymentEvent,
    PaymentRequest,
    format_ts,
    make_key,
)

log = logging.getLogger("secflow.service")
HISTOGRAM_BINS = 20


@dataclass(frozen=True)
class TransactionFilters:
    q: str | None = None
    decision: str | None = None
    decision_source: str | None = None
    origin: str | None = None
    review_status: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    min_score: float | None = None
    max_score: float | None = None
    sort: str = "time_desc"
    page: int = 1
    page_size: int = 25


def _fingerprint(payload: SimulationRequest) -> str:
    return hashlib.sha256(json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()


class SecFlowService:
    def __init__(self, settings: Settings) -> None:
        started = time.perf_counter()
        self.settings = settings
        self.started_at = utc_now_iso()
        self.policy = load_policy(settings.policy_path)
        self.dataset: Dataset = load_dataset(settings.demo_dir)
        self.model_error: str | None = None
        self.bundle: ModelBundle | None
        try:
            self.bundle = load_bundle(settings.models_dir)
            self.operating_point = load_operating_point(settings.models_dir, self.bundle.version)
        except BundleError as error:  # degraded mode: every request is routed to Verify
            log.warning("Model bundle unavailable: %s", error)
            self.bundle = None
            self.model_error = str(error)
            self.operating_point = OperatingPoint(
                self.policy.initial_verify, self.policy.initial_block, "initial_unvalidated", "op-initial"
            )
        self.evidence = build_evidence_store(self.dataset.security_events, self.policy)
        self.accounts = self.dataset.accounts
        self.counterparties: dict[str, Counterparty] = dict(self.dataset.counterparties)
        history, keys = HistoryIndex.from_events(
            self.dataset.requests, self.dataset.auth_events, self.dataset.payment_events
        )
        self.state = MemoryState(history)
        self._sessions: dict[str, list[AuthEvent]] = defaultdict(list)
        for event in self.dataset.auth_events:
            self._sessions[event.session_id].append(event)
        self._replay_baseline(keys)
        last_ts = max(history.max_key // KEY_SCALE, self.dataset.requests[-1].ts)
        self._sim_epoch = last_ts + 3_600
        self._wall_epoch = time.monotonic()
        self._last_ts = self._sim_epoch
        self._sim_counter = 0
        self._graph = ClusterGraphBuilder(self.bundle.dbscan) if self.bundle else None
        self.startup_seconds = round(time.perf_counter() - started, 2)
        log.info("SecFlow service ready in %.2fs", self.startup_seconds)

    # ------------------------------------------------------------------
    # startup
    # ------------------------------------------------------------------
    def _replay_baseline(self, keys: dict[str, int]) -> None:
        ordered = sorted(self.dataset.requests, key=lambda r: keys[r.request_id])
        results = assess_batch(
            ordered, keys, self.state.history, self.accounts, self.bundle, self.evidence, self.policy,
            self.operating_point,
        )
        assessed_at = utc_now_iso()
        for request, result in zip(ordered, results, strict=True):
            self.state.add_baseline(
                AssessmentRecord(
                    seq=self.state.next_seq(),
                    origin="baseline",
                    producer=None,
                    request=request,
                    key=keys[request.request_id],
                    result=result,
                    assessed_at=assessed_at,
                    fingerprint=None,
                    session_events=tuple(self._sessions.get(request.session_id, ())),
                    outcome=OUTCOME_FOR_DECISION[result.policy.decision],
                )
            )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def simulation_now(self) -> int:
        return int(self._sim_epoch + (time.monotonic() - self._wall_epoch))

    def party(self, party_id: str) -> PartyRef:
        account = self.accounts.get(party_id)
        if account:
            return PartyRef(id=party_id, name=account.display_name, kind="account")
        counterparty = self.counterparties.get(party_id)
        return PartyRef(id=party_id, name=counterparty.display_name if counterparty else party_id, kind="counterparty")

    def _record(self, request_id: str) -> AssessmentRecord:
        record = self.state.records.get(request_id)
        if record is None:
            raise NotFoundError(request_id)
        return record

    def _next_key(self, ts: int) -> int:
        history = self.state.history
        history.max_seq += 1
        key = make_key(ts, history.max_seq)
        if key <= history.max_key:
            key = make_key(history.max_key // KEY_SCALE + 1, history.max_seq)
        return key

    def _clock(self, minimum: int | None = None) -> int:
        ts = max(self.simulation_now(), self._last_ts, minimum or 0)
        self._last_ts = ts
        return ts

    def last_device(self, account_id: str) -> str | None:
        series = self.state.history.auth.get(account_id)
        return series.devices[-1] if series and series.devices else None

    # ------------------------------------------------------------------
    # simulations
    # ------------------------------------------------------------------
    def simulate(self, payload: SimulationRequest, producer: str = "manual") -> tuple[AssessmentDetail, bool]:
        if payload.sender_id not in self.accounts:
            raise NotFoundError(f"Unknown sender {payload.sender_id}")
        if payload.recipient_id and payload.recipient_id not in self.accounts and payload.recipient_id not in self.counterparties:
            raise NotFoundError(f"Unknown recipient {payload.recipient_id}")
        if payload.recipient_id == payload.sender_id:
            raise ConflictError("Sender and recipient must differ")
        record, replay = self.state.submit_once(
            payload.request_id, _fingerprint(payload), lambda: self._assess_and_commit(payload, producer)
        )
        return self._detail(record, replay), replay

    def _assess_and_commit(self, payload: SimulationRequest, producer: str) -> AssessmentRecord:
        """Runs under the state lock: append session events, assess once, commit the attempt."""
        history = self.state.history
        self._sim_counter += 1
        suffix = f"{self._sim_counter:06d}"
        account = self.accounts[payload.sender_id]
        recipient_id = payload.recipient_id
        if recipient_id is None:
            recipient_id = f"CP-SIM-{suffix}"
            self.counterparties[recipient_id] = Counterparty(recipient_id, payload.new_recipient_name or recipient_id,
                                                             "person", "simulated")
        device = payload.device_id or f"DEV-SIM-{suffix}"
        session = f"SES-SIM-{suffix}"
        ts = self._clock()
        events: list[AuthEvent] = []
        for attempt in range(payload.failed_login_attempts):
            events.append(AuthEvent(f"AE-SIM-{suffix}-{attempt}", ts + 20 * attempt, payload.sender_id, session, device,
                                    "login_failure", payload.auth_method, payload.ip_country, "invalid_credentials"))
        success_ts = ts + 20 * payload.failed_login_attempts
        events.append(AuthEvent(f"AE-SIM-{suffix}-ok", success_ts, payload.sender_id, session, device, "login_success",
                                payload.auth_method, payload.ip_country, None))
        for event in events:
            history.add_auth(event, self._next_key(event.ts))
        request = PaymentRequest(
            request_id=payload.request_id, ts=success_ts + 8, sender_id=payload.sender_id, recipient_id=recipient_id,
            recipient_type="account" if recipient_id in self.accounts else "counterparty", amount=payload.amount,
            currency=payload.currency, channel=payload.channel, device_id=device, session_id=session,
            auth_method=payload.auth_method, ip_country=payload.ip_country,
        )
        key = self._next_key(request.ts)
        started = time.perf_counter()
        result = assess_one(request, key, history, account, self.bundle, self.evidence, self.policy, self.operating_point)
        latency_ms = (time.perf_counter() - started) * 1_000
        history.add_request(request, key)  # attempted activity counts regardless of the decision
        outcome = OUTCOME_FOR_DECISION[result.policy.decision]
        if outcome == "permitted":
            self._settle(request, request.ts + 2)
        self._last_ts = request.ts + 2
        return AssessmentRecord(
            seq=self.state.next_seq(), origin="simulation", producer=producer, request=request, key=key, result=result,
            assessed_at=utc_now_iso(), fingerprint=None, session_events=tuple(events), outcome=outcome,
            latency_ms=round(latency_ms, 3),
        )

    def _settle(self, request: PaymentRequest, ts: int) -> None:
        event = PaymentEvent(f"PE-SIM-{request.request_id}", ts, "transfer_settled", request.sender_id,
                             request.recipient_id, request.amount, request.currency, request.request_id)
        self.state.history.add_payment(event, self._next_key(ts))

    # ------------------------------------------------------------------
    # reviews
    # ------------------------------------------------------------------
    def review(self, request_id: str, payload: ReviewRequest) -> Investigation:
        def build(record: AssessmentRecord) -> ReviewRecord:
            approved = payload.action == "approve"
            now = self._clock()
            if approved and record.origin == "simulation":
                self._settle(record.request, now)
            return ReviewRecord(
                review_id=f"REV-{self.state.review_count + 1:05d}", request_id=request_id, action=payload.action,
                reason=payload.reason, actor=payload.actor, created_at=utc_now_iso(), simulated_time=now,
                original_decision=record.result.policy.decision,
                original_risk_score=round(record.result.risk.total, 2) if record.result.risk else None,
                resulting_outcome="approved_after_review" if approved else "rejected_after_review",
            )

        self.state.add_review(request_id, build)
        return self.investigation(request_id)

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------
    def _detail(self, record: AssessmentRecord, replay: bool = False) -> AssessmentDetail:
        return views.detail(record, self.party, self.policy, self.operating_point,
                            self.bundle.version if self.bundle else None, replay)

    def investigation(self, request_id: str) -> Investigation:
        with self.state.lock:
            record = self._record(request_id)
            return Investigation(
                assessment=self._detail(record),
                timeline=views.timeline(record),
                reviews=[views.review_view(r) for r in record.reviews],
                can_review=record.result.policy.decision == "Verify" and not record.reviews,
            )

    def _records(self) -> list[AssessmentRecord]:
        with self.state.lock:
            return [self.state.records[rid] for rid in self.state.order]

    def transactions(self, f: TransactionFilters) -> TransactionPage:
        records = self._records()
        query = (f.q or "").strip().lower()

        def matches(r: AssessmentRecord) -> bool:
            result = r.result
            if f.decision and result.policy.decision != f.decision:
                return False
            if f.decision_source and result.policy.decision_source != f.decision_source:
                return False
            if f.origin and r.origin != f.origin:
                return False
            if f.review_status and views.review_status(r) != f.review_status:
                return False
            stamp = format_ts(r.request.ts)
            if f.date_from and stamp[:10] < f.date_from:
                return False
            if f.date_to and stamp[:10] > f.date_to:
                return False
            score = result.risk.total if result.risk else None
            if f.min_score is not None and (score is None or score < f.min_score):
                return False
            if f.max_score is not None and (score is None or score > f.max_score):
                return False
            if query:
                haystack = f"{r.request.request_id} {r.request.sender_id} {r.request.recipient_id} {self.party(r.request.sender_id).name} {self.party(r.request.recipient_id).name}".lower()
                return query in haystack
            return True

        selected = [r for r in records if matches(r)]
        if f.sort == "risk_desc":
            selected.sort(key=lambda r: (r.result.risk.total if r.result.risk else -1, r.key), reverse=True)
        else:
            selected.sort(key=lambda r: r.key, reverse=f.sort != "time_asc")
        start = (f.page - 1) * f.page_size
        items = [views.summary(r, self.party) for r in selected[start:start + f.page_size]]
        return TransactionPage(items=items, total=len(selected), page=f.page, page_size=f.page_size)

    def live_feed(self, after: int, limit: int) -> list[Any]:
        with self.state.lock:
            ids = [rid for rid in self.state.simulation_order if self.state.records[rid].seq > after]
            ids = ids[-limit:]
            return [views.summary(self.state.records[rid], self.party) for rid in ids]

    def latest_cursor(self) -> int:
        with self.state.lock:
            if not self.state.simulation_order:
                return 0
            return self.state.records[self.state.simulation_order[-1]].seq

    def overview(self) -> dict[str, Any]:
        records = self._records()
        by_label = Counter(r.result.policy.label for r in records)
        by_origin = Counter(r.origin for r in records)
        outcomes = Counter(r.outcome for r in records)
        volume = defaultdict(float)
        for r in records:
            volume[r.outcome] += r.request.amount
        days: dict[str, dict[str, Any]] = {}
        for r in records:
            day = format_ts(r.request.ts)[:10]
            bucket = days.setdefault(day, {"date": day, "requests": 0, "risk_sum": 0.0, "scored": 0,
                                           "Permit": 0, "Verify": 0, "Block": 0})
            bucket["requests"] += 1
            bucket[r.result.policy.decision] += 1
            if r.result.risk:
                bucket["risk_sum"] += r.result.risk.total
                bucket["scored"] += 1
        trend = [
            {"date": b["date"], "requests": b["requests"], "permit": b["Permit"], "verify": b["Verify"],
             "block": b["Block"], "mean_risk": round(b["risk_sum"] / b["scored"], 2) if b["scored"] else None}
            for b in sorted(days.values(), key=lambda b: b["date"])
        ]
        recent = sorted(records, key=lambda r: r.key, reverse=True)[:8]
        pending = [r for r in records if views.review_status(r) == "pending"]
        pending.sort(key=lambda r: (r.result.risk.total if r.result.risk else 0), reverse=True)
        return {
            "totals": {
                "assessed": len(records),
                "baseline": by_origin.get("baseline", 0),
                "simulations": by_origin.get("simulation", 0),
                "permitted": by_label.get("Permitted", 0),
                "needs_verification": by_label.get("Needs verification", 0),
                "preventive_blocks": by_label.get("Preventive risk block", 0),
                "confirmed_evidence_blocks": by_label.get("Confirmed fraud evidence", 0),
                "awaiting_review": len(pending),
                "reviewed": self.state.review_count,
            },
            "outcomes": dict(outcomes),
            "volumes": {
                "completed": round(sum(volume[o] for o in COMPLETED_OUTCOMES), 2),
                "pending_verification": round(volume["pending_verification"], 2),
                "blocked_attempts": round(volume["blocked_attempt"] + volume["rejected_after_review"], 2),
                "currency": "EUR",
                "note": "Completed volume counts only permitted or approved simulated outcomes. "
                "Blocked and pending attempts are excluded; no funds move through a bank.",
            },
            "trend": trend,
            "recent": [views.summary(r, self.party) for r in recent],
            "review_queue": [views.summary(r, self.party) for r in pending[:8]],
            "simulation_time": format_ts(self.simulation_now()),
        }

    # -- accounts ---------------------------------------------------------
    def accounts_page(self, q: str | None, page: int, page_size: int, account_type: str | None) -> AccountPage:
        records = self._records()
        stats: dict[str, dict[str, Any]] = {}
        for r in records:
            s = stats.setdefault(r.request.sender_id, {"requests": 0, "flagged": 0, "last": None})
            s["requests"] += 1
            s["flagged"] += int(r.result.policy.decision != "Permit")
            s["last"] = r
        query = (q or "").strip().lower()
        accounts = [
            a for a in self.accounts.values()
            if (not query or query in a.display_name.lower() or query in a.account_id.lower())
            and (not account_type or a.account_type == account_type)
        ]
        accounts.sort(key=lambda a: a.display_name)
        start = (page - 1) * page_size
        items = []
        for a in accounts[start:start + page_size]:
            s = stats.get(a.account_id, {"requests": 0, "flagged": 0, "last": None})
            last = s["last"]
            items.append(AccountSummary(
                account_id=a.account_id, display_name=a.display_name, account_type=a.account_type,
                home_country=a.home_country, created_at=format_ts(a.created_at), requests=s["requests"],
                flagged=s["flagged"], last_activity=format_ts(last.request.ts) if last else None,
                last_decision=last.result.policy.decision if last else None,
            ))
        return AccountPage(items=items, total=len(accounts), page=page, page_size=page_size)

    def account_detail(self, account_id: str) -> dict[str, Any]:
        account = self.accounts.get(account_id)
        if account is None:
            raise NotFoundError(account_id)
        records = self._records()
        sent = [r for r in records if r.request.sender_id == account_id]
        received = [r for r in records if r.request.recipient_id == account_id]
        amounts = sorted(r.request.amount for r in sent)
        recipients = Counter(r.request.recipient_id for r in sent)
        hours = [(r.request.ts % 86_400) / 3_600 for r in sent]
        devices: dict[str, dict[str, Any]] = {}
        auth = self.state.history.auth.get(account_id)
        if auth:
            for key, device in zip(auth.keys, auth.devices, strict=True):
                entry = devices.setdefault(device, {"device_id": device, "first_seen": format_ts(key // KEY_SCALE), "sign_ins": 0})
                entry["sign_ins"] += 1
                entry["last_seen"] = format_ts(key // KEY_SCALE)
        latest = max(sent, key=lambda r: r.key) if sent else None
        context = None
        if latest and latest.result.components:
            ctx = latest.result.components.context
            context = {"request_id": latest.request.request_id, "status": ctx.status, "score": ctx.score,
                       "distance": ctx.distance, "cluster": ctx.cluster, "at": format_ts(latest.request.ts)}
        context_counts = Counter(r.result.components.context.status for r in sent if r.result.components)
        linked = sorted(sent + received, key=lambda r: r.key, reverse=True)[:30]
        return {
            "account": {"account_id": account.account_id, "display_name": account.display_name,
                        "account_type": account.account_type, "home_country": account.home_country,
                        "created_at": format_ts(account.created_at)},
            "profile": {
                "requests_sent": len(sent),
                "requests_received": len(received),
                "median_amount": amounts[len(amounts) // 2] if amounts else None,
                "p90_amount": amounts[int(len(amounts) * 0.9)] if amounts else None,
                "typical_hour": round(float(np.median(hours)), 1) if hours else None,
                "decisions": dict(Counter(r.result.policy.decision for r in sent)),
                "top_recipients": [
                    {**self.party(rid).model_dump(), "payments": n} for rid, n in recipients.most_common(6)
                ],
                "devices": sorted(devices.values(), key=lambda d: d["first_seen"]),
            },
            "context": {"latest": context, "counts": dict(context_counts)},
            "activity": [views.summary(r, self.party) for r in linked],
        }

    def parties(self, q: str, limit: int) -> list[dict[str, Any]]:
        query = q.strip().lower()
        found: list[dict[str, Any]] = []
        for a in self.accounts.values():
            if not query or query in a.display_name.lower() or query in a.account_id.lower():
                found.append({"id": a.account_id, "name": a.display_name, "kind": "account", "detail": a.account_type})
        for c in self.counterparties.values():
            if query and (query in c.display_name.lower() or query in c.counterparty_id.lower()):
                found.append({"id": c.counterparty_id, "name": c.display_name, "kind": "counterparty", "detail": c.category})
        return found[:limit]

    def simulator_options(self, sender_id: str | None) -> dict[str, Any]:
        now = self.simulation_now()
        flagged = [
            {"evidence_id": e.evidence_id, "id": e.entity_id, "name": self.party(e.entity_id).name,
             "evidence_type": e.evidence_type}
            for e in self.evidence.active_entities("counterparty", now)
        ]
        sender = None
        if sender_id and sender_id in self.accounts:
            series = self.state.history.sender.get(sender_id)
            recent = list(dict.fromkeys(reversed(series.recipients[-40:]))) if series else []
            amounts = sorted(series.amounts[-30:]) if series else []
            sender = {
                "account_id": sender_id,
                "home_country": self.accounts[sender_id].home_country,
                "known_devices": list(dict.fromkeys(reversed(self.state.history.auth[sender_id].devices)))[:4]
                if sender_id in self.state.history.auth else [],
                "recent_recipients": [self.party(r).model_dump() for r in recent[:8]],
                "median_amount": amounts[len(amounts) // 2] if amounts else None,
            }
        return {
            "simulation_time": format_ts(now),
            "currencies": ["EUR"],
            "auth_methods": ["biometric", "password_otp", "otp", "password"],
            "countries": sorted({a.home_country for a in self.accounts.values()} | {"US", "GB", "AE", "TR", "UA"}),
            "flagged_beneficiaries": flagged,
            "sender": sender,
        }

    # -- algorithms -------------------------------------------------------
    def algorithms(self) -> dict[str, Any]:
        records = self._records()
        scored = [r for r in records if r.result.components]

        def histogram(values: list[float]) -> list[int]:
            counts, _ = np.histogram(values, bins=HISTOGRAM_BINS, range=(0.0, 1.0))
            return counts.tolist()

        distributions = {
            "isolation_forest": histogram([r.result.components.if_score for r in scored]),
            "lof": histogram([r.result.components.lof_score for r in scored]),
            "rules": histogram([r.result.rules.score for r in records]),
            "risk_score": np.histogram([r.result.risk.total for r in scored if r.result.risk], bins=HISTOGRAM_BINS,
                                       range=(0, 100))[0].tolist(),
        }
        daily: dict[str, Counter] = defaultdict(Counter)
        for r in scored:
            daily[format_ts(r.request.ts)[:10]][r.result.components.context.status] += 1
        context_days = [{"date": d, **dict(c)} for d, c in sorted(daily.items())]
        report_path = self.settings.models_dir / "training_report.json"
        training = json.loads(report_path.read_text()) if report_path.exists() else None
        return {
            "model": self.bundle.metadata if self.bundle else None,
            "model_error": self.model_error,
            "policy": {
                "version": self.policy.version,
                "weights": dict(self.policy.weights),
                "operating_point": {"verify": self.operating_point.verify, "block": self.operating_point.block,
                                    "source": self.operating_point.source, "version": self.operating_point.version},
                "min_corroborating_families": self.policy.min_families,
                "families": dict(self.policy.families),
                "rules": [
                    {"code": r.code, "family": r.family, "weight": r.weight, "corroborating": r.corroborating,
                     "description": r.description, "params": dict(r.params)}
                    for r in self.policy.rules
                ],
                "cold_start": {"max_amount_without_history": self.policy.cold_start_max_amount,
                               "strong_auth_methods": sorted(self.policy.strong_auth_methods)},
                "trusted_sources": list(self.policy.trusted_sources),
            },
            "distributions": distributions,
            "histogram_bins": HISTOGRAM_BINS,
            "dbscan_context": {
                "status_counts": dict(Counter(r.result.components.context.status for r in scored)),
                "daily": context_days,
            },
            "decision_sources": dict(Counter(f"{r.result.policy.decision}/{r.result.policy.decision_source}" for r in records)),
            "training": training and {
                "validation_component_average_precision": training["validation_component_average_precision"],
                "threshold_selection": {k: training["threshold_selection"][k] for k in
                                        ("chosen", "candidates_evaluated", "feasible_candidates", "frontier",
                                         "initial_candidate")},
                "search": training["search"],
            },
        }

    def dashboard(self, window: str) -> dict[str, Any]:
        return dashboard(self._records(), window, self.simulation_now(), self.operating_point, dict(self.policy.goals))

    def cluster_graph(self, max_anomalies: int) -> dict[str, Any]:
        if self._graph is None:
            raise NotFoundError("cluster graph (model bundle unavailable)")
        return self._graph.build(self._records(), self.party, max_anomalies)

    def evaluation(self) -> dict[str, Any] | None:
        path = self.settings.artifacts_dir / "evaluation.json"
        return json.loads(path.read_text()) if path.exists() else None

    def health(self, stream: dict[str, Any]) -> dict[str, Any]:
        manifest = self.dataset.manifest
        with self.state.lock:
            simulations = len(self.state.simulation_order)
            reviews = self.state.review_count
        return {
            "status": "ok" if self.bundle else "degraded",
            "started_at": self.started_at,
            "startup_seconds": self.startup_seconds,
            "data": {
                "source": "local_files",
                "dataset": manifest["dataset"],
                "generator_version": manifest["generator_version"],
                "seed": manifest["seed"],
                "requests": manifest["counts"]["requests"],
                "accounts": manifest["counts"]["accounts"],
                "hashes_verified": True,
                "date_range": manifest["date_range"],
            },
            "model": {
                "loaded": self.bundle is not None,
                "version": self.bundle.version if self.bundle else None,
                "error": self.model_error,
            },
            "policy": {
                "version": self.policy.version,
                "operating_point": {"verify": self.operating_point.verify, "block": self.operating_point.block,
                                    "source": self.operating_point.source},
            },
            "state": {
                "kind": "process_memory",
                "simulations": simulations,
                "reviews": reviews,
                "persisted": False,
                "shared_across_workers": False,
                "note": "Simulations and reviews live in this process only. A restart discards them, and separate "
                "workers or instances would not share them. Run a single backend process.",
            },
            "stream": stream,
            "simulation_time": format_ts(self.simulation_now()),
        }


def iso_now() -> str:
    return datetime.now(UTC).isoformat()


def finite_or_none(value: float | None) -> float | None:
    return value if value is not None and math.isfinite(value) else None
