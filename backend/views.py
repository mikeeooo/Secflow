"""Conversion from in-memory records to public response models."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.schemas import (
    AssessmentDetail,
    AssessmentSummary,
    ComponentBrief,
    ComponentView,
    EvidenceView,
    PartyRef,
    ReasonView,
    ReviewView,
    Thresholds,
    TimelineEntry,
)
from ml.policy import OperatingPoint, Policy
from storage.memory import AssessmentRecord, ReviewRecord
from storage.records import format_ts

COMPONENT_LABELS = {
    "isolation_forest": "Isolation Forest",
    "lof": "Local Outlier Factor",
    "dbscan": "DBSCAN account context",
    "rules": "Behaviour rules",
}

PartyLookup = Callable[[str], PartyRef]


def review_status(record: AssessmentRecord) -> str:
    if record.result.policy.decision != "Verify":
        return "not_applicable"
    if not record.reviews:
        return "pending"
    return "approved" if record.reviews[-1].action == "approve" else "rejected"


def _round(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(value, digits)


def summary(record: AssessmentRecord, party: PartyLookup) -> AssessmentSummary:
    result = record.result
    components = result.components
    risk = result.risk
    return AssessmentSummary(
        cursor=record.seq,
        request_id=record.request.request_id,
        origin=record.origin,  # type: ignore[arg-type]
        producer=record.producer,
        event_time=format_ts(record.request.ts),
        sender=party(record.request.sender_id),
        recipient=party(record.request.recipient_id),
        amount=record.request.amount,
        currency=record.request.currency,
        risk_score=_round(risk.total, 2) if risk else None,
        decision=result.policy.decision,  # type: ignore[arg-type]
        decision_source=result.policy.decision_source,  # type: ignore[arg-type]
        decision_label=result.policy.label,  # type: ignore[arg-type]
        assessment_status=result.policy.assessment_status,
        outcome=record.outcome,  # type: ignore[arg-type]
        review_status=review_status(record),  # type: ignore[arg-type]
        components=ComponentBrief(
            isolation_forest=_round(components.if_score) if components else None,
            lof=_round(components.lof_score) if components else None,
            dbscan=_round(components.context.score) if components else None,
            rules=_round(result.rules.score),
        ),
        evidence_ids=list(result.policy.evidence_ids),
        corroborating_signals=list(result.policy.corroborating_signals),
    )


def _component_details(record: AssessmentRecord, policy: Policy) -> list[ComponentView]:
    result = record.result
    c = result.components
    contributions = result.risk.contributions if result.risk else {}
    views = []
    if_score = c.if_score if c else None
    views.append(ComponentView(
        key="isolation_forest", label=COMPONENT_LABELS["isolation_forest"], score=_round(if_score),
        weight=policy.weights["isolation_forest"], contribution=_round(contributions.get("isolation_forest"), 3),
        raw=_round(c.if_raw) if c else None, status="scored" if c else "unavailable",
        detail=(f"More isolated than {if_score:.0%} of reference-period requests." if c else "Model not loaded."),
    ))
    lof_score = c.lof_score if c else None
    views.append(ComponentView(
        key="lof", label=COMPONENT_LABELS["lof"], score=_round(lof_score), weight=policy.weights["lof"],
        contribution=_round(contributions.get("lof"), 3), raw=_round(c.lof_raw) if c else None,
        status="scored" if c else "unavailable",
        detail=(f"Local density lower than for {lof_score:.0%} of reference-period requests." if c else "Model not loaded."),
    ))
    context_detail = "Model not loaded."
    if c:
        ctx = c.context
        if ctx.status == "within_context":
            context_detail = (f"The trailing 24-hour account profile lies within a frozen DBSCAN core neighbourhood "
                              f"(distance {ctx.distance:.2f}, cluster {ctx.cluster}).")
        elif ctx.status == "outside_context":
            context_detail = (f"The trailing 24-hour account profile lies outside every frozen core neighbourhood "
                              f"(nearest distance {ctx.distance:.2f}). This is context, not a fraud verdict.")
        else:
            context_detail = ("Fewer than three earlier payments: the context score is 0 and marked as "
                              "insufficient history.")
    views.append(ComponentView(
        key="dbscan", label=COMPONENT_LABELS["dbscan"], score=_round(c.context.score) if c else None,
        weight=policy.weights["dbscan"], contribution=_round(contributions.get("dbscan"), 3),
        raw=_round(c.context.distance) if c and c.context.distance is not None else None,
        status=c.context.status if c else "unavailable",
        detail=context_detail,
    ))
    triggered = len(result.rules.triggered)
    views.append(ComponentView(
        key="rules", label=COMPONENT_LABELS["rules"], score=_round(result.rules.score), weight=policy.weights["rules"],
        contribution=_round(contributions.get("rules"), 3), raw=None, status="scored",
        detail=f"{triggered} rule{'s' if triggered != 1 else ''} triggered; the rules score is the capped sum of their weights.",
    ))
    return views


def evidence_view(item: Any) -> EvidenceView:
    return EvidenceView(
        evidence_id=item.evidence_id, evidence_type=item.evidence_type, entity_type=item.entity_type,
        entity_id=item.entity_id, source=item.source, recorded_at=format_ts(item.recorded_at),
        effective_from=format_ts(item.effective_from),
        effective_until=format_ts(item.effective_until) if item.effective_until else None, note=item.note,
    )


def _jsonable(facts: dict[str, Any]) -> dict[str, Any]:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in facts.items()}


def detail(
    record: AssessmentRecord,
    party: PartyLookup,
    policy: Policy,
    point: OperatingPoint,
    model_version: str | None,
    replay: bool = False,
) -> AssessmentDetail:
    base = summary(record, party)
    result = record.result
    request = record.request
    return AssessmentDetail(
        **base.model_dump(),
        explanation=result.policy.explanation,
        status_notes=list(result.status_notes),
        component_details=_component_details(record, policy),
        reasons=[
            ReasonView(code=t.code, family=t.family, description=t.description, detail=t.detail, weight=t.weight,
                       corroborating=t.corroborating)
            for t in result.rules.triggered
        ],
        evidence=[evidence_view(e) for e in result.evidence],
        thresholds=Thresholds(verify=point.verify, block=point.block, min_corroborating_families=policy.min_families,
                              source=point.source),
        model_version=model_version,
        policy_version=policy.version,
        operating_point_version=point.version,
        assessed_at=record.assessed_at,
        device_id=request.device_id,
        session_id=request.session_id,
        auth_method=request.auth_method,
        ip_country=request.ip_country,
        channel=request.channel,
        facts=_jsonable(dict(result.snapshot.facts)),
        idempotent_replay=replay,
    )


def review_view(review: ReviewRecord) -> ReviewView:
    return ReviewView(
        review_id=review.review_id, action=review.action, reason=review.reason, actor=review.actor,  # type: ignore[arg-type]
        created_at=review.created_at, original_decision=review.original_decision,  # type: ignore[arg-type]
        original_risk_score=review.original_risk_score, resulting_outcome=review.resulting_outcome,  # type: ignore[arg-type]
    )


OUTCOME_TEXT = {
    "permitted": ("Recorded as permitted", "Simulated outcome only: no funds moved through a bank."),
    "pending_verification": ("Held for verification", "Not counted as a completed transfer until an analyst approves it."),
    "blocked_attempt": ("Recorded as a blocked attempt", "Not executed and excluded from completed-payment totals."),
    "approved_after_review": ("Approved after review", "Simulated outcome only: no funds moved through a bank."),
    "rejected_after_review": ("Rejected after review", "Not executed and excluded from completed-payment totals."),
}


def timeline(record: AssessmentRecord) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    for event in record.session_events:
        title = {
            "login_failure": "Failed sign-in attempt",
            "login_success": "Signed in",
            "session_revoked": "Session ended",
        }.get(event.event_type, event.event_type)
        entries.append(TimelineEntry(
            at=format_ts(event.ts), kind="authentication", title=title,
            detail=f"{event.auth_method} on {event.device_id} from {event.ip_country}"
            + (f" ({event.reason.replace('_', ' ')})" if event.reason else ""),
        ))
    for item in record.result.evidence:
        entries.append(TimelineEntry(at=format_ts(item.recorded_at), kind="evidence",
                                     title=f"Security evidence recorded: {item.evidence_type.replace('_', ' ')}",
                                     detail=f"{item.evidence_id} from {item.source.replace('_', ' ')}"))
    request = record.request
    entries.append(TimelineEntry(at=format_ts(request.ts), kind="request", title="Payment request received",
                                 detail=f"{request.amount:,.2f} {request.currency} via {request.channel.replace('_', ' ')}"))
    policy = record.result.policy
    entries.append(TimelineEntry(at=format_ts(request.ts), kind="decision", title=f"Automated decision: {policy.label}",
                                 detail=policy.explanation))
    original_outcome = {"Permit": "permitted", "Verify": "pending_verification", "Block": "blocked_attempt"}[policy.decision]
    title, text = OUTCOME_TEXT[original_outcome]
    entries.append(TimelineEntry(at=format_ts(request.ts), kind="outcome", title=title, detail=text))
    for review in record.reviews:
        title, text = OUTCOME_TEXT[review.resulting_outcome]
        entries.append(TimelineEntry(at=format_ts(review.simulated_time), kind="review",
                                     title=f"{title} by {review.actor}", detail=f"“{review.reason}” — {text}"))
    return sorted(entries, key=lambda e: e.at)
