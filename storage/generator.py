"""Seeded synthetic dataset generator for SecFlow.

The generator first simulates behaviour (routine payments, unusual-but-legitimate episodes,
five fraud campaign types, authentication sessions, incoming credits, and a separate stream
of simulated security evidence) and only then writes ground-truth labels into a separate
`evaluation_labels.jsonl` file. Runtime files never contain labels, scenarios, or generator
parameters; generator-only account behaviour lives in `generator_account_params.jsonl`, which
no runtime or feature code reads.

Reproducing the requested counts does not reproduce any earlier dataset byte for byte.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from storage.identities import (
    COUNTRIES,
    IDENTITY_SEED,
    AccountIdentity,
    CounterpartyIdentity,
    build_accounts,
    build_counterparties,
)

GENERATOR_VERSION = "secflow-generator-1.0.0"
SCHEMA_VERSION = "1.0"
CURRENCY = "EUR"
DAY_SECONDS = 86_400
FRAUD_CATEGORIES = ("account_takeover", "mule_flow", "velocity", "social_engineering", "coordinated")
UNUSUAL_TYPES = (
    "large_planned_purchase",
    "new_device_legitimate",
    "travel",
    "payroll_burst",
    "household_repeat",
    "business_settlement",
    "new_recipient_legitimate",
    "shared_group_payment",
    "account_recovery",
)
UNUSUAL_WEIGHTS = (0.13, 0.13, 0.12, 0.12, 0.12, 0.08, 0.13, 0.09, 0.08)
TRUSTED_SOURCES = ("bank_security_operations", "fraud_investigations_unit")
UNTRUSTED_SOURCE = "external_tip_feed"
BASE_COUNTERPARTIES = 650
POPULAR_BILLERS = 25

RUNTIME_FILES = (
    "accounts.jsonl",
    "counterparties.jsonl",
    "requests.jsonl",
    "payment_events.jsonl",
    "authentication_events.jsonl",
    "security_events.jsonl",
)
OFFLINE_FILES = ("evaluation_labels.jsonl", "generator_account_params.jsonl")


@dataclass(frozen=True)
class Partition:
    name: str
    first_day: int  # 1-based, inclusive
    last_day: int  # inclusive


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    seed: int
    start: date
    days: int
    requests_per_day: int
    request_prefix: str
    entity_prefix: str
    partitions: tuple[Partition, ...]
    fraud_per_category: dict[str, int]  # partition name -> requests per category
    unusual_per_partition: dict[str, int]
    cold_start_partition: str | None
    activity_scale: float


TRAINING_START = date(2026, 4, 6)
DEMO_START = date(2026, 7, 20)
COLD_START_ACCOUNTS = 40

TRAINING_SPEC = DatasetSpec(
    name="training",
    seed=42,
    start=TRAINING_START,
    days=100,
    requests_per_day=1000,
    request_prefix="TR",
    entity_prefix="T",
    partitions=(
        Partition("train", 1, 60),
        Partition("calibration", 61, 70),
        Partition("validation", 71, 80),
        Partition("test", 81, 100),
    ),
    fraud_per_category={"train": 120, "calibration": 20, "validation": 20, "test": 40},
    unusual_per_partition={"train": 3000, "calibration": 500, "validation": 500, "test": 1000},
    cold_start_partition="test",
    activity_scale=1.0,
)

DEMO_SPEC = DatasetSpec(
    name="demo",
    seed=43,
    start=DEMO_START,
    days=100,
    requests_per_day=100,
    request_prefix="DM",
    entity_prefix="D",
    partitions=(Partition("demo", 1, 100),),
    fraud_per_category={"demo": 20},
    unusual_per_partition={"demo": 500},
    cold_start_partition=None,
    activity_scale=0.1,
)


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_start_ts(start: date, day: int) -> int:
    moment = datetime(start.year, start.month, start.day, tzinfo=UTC) + timedelta(days=day - 1)
    return int(moment.timestamp())


# ---------------------------------------------------------------------------
# Generator-only account behaviour (never read at runtime)
# ---------------------------------------------------------------------------


@dataclass
class AccountParams:
    account_id: str
    account_type: str
    home_country: str
    created_at: int
    cold_start: bool
    activity_weight: float
    median_amount: float
    amount_sigma: float
    payees: list[str]
    payee_weights: list[float]
    payee_factors: list[float]
    employees: list[str]
    devices: list[str]
    hour_center: float
    hour_spread: float
    auth_mix: dict[str, float]
    payday: int
    employer: str
    salary: float


def _build_base_counterparties() -> list[CounterpartyIdentity]:
    rng = np.random.default_rng(IDENTITY_SEED + 1000)
    reserved = {a.display_name for a in build_accounts()}
    billers = []
    biller_kinds = ("Utilities", "Telecom", "Energy", "Insurance", "Property Management")
    from storage.identities import BUSINESS_PREFIXES

    for index in range(POPULAR_BILLERS):
        name = f"{BUSINESS_PREFIXES[index % len(BUSINESS_PREFIXES)]} {biller_kinds[index % len(biller_kinds)]}"
        if name in reserved:
            name = f"{name} Group"
        reserved.add(name)
        billers.append(CounterpartyIdentity(f"CP-{index + 1:05d}", name, "business", "biller"))
    others = build_counterparties(
        rng, BASE_COUNTERPARTIES - POPULAR_BILLERS, "CP-", POPULAR_BILLERS + 1, reserved_names=reserved
    )
    return billers + others


def _build_account_params(
    accounts: list[AccountIdentity], counterparties: list[CounterpartyIdentity]
) -> list[AccountParams]:
    rng = np.random.default_rng(IDENTITY_SEED + 2000)
    training_start = day_start_ts(TRAINING_START, 1)
    personal_ids = [a.account_id for a in accounts if a.account_type == "personal"]
    cold_start_ids = set(rng.choice(personal_ids, size=COLD_START_ACCOUNTS, replace=False).tolist())
    eligible_internal = [a for a in personal_ids if a not in cold_start_ids]
    biller_ids = [c.counterparty_id for c in counterparties[:POPULAR_BILLERS]]
    business_cps = [c.counterparty_id for c in counterparties[POPULAR_BILLERS:] if c.kind == "business"]
    person_cps = [c.counterparty_id for c in counterparties[POPULAR_BILLERS:] if c.kind == "person"]
    test_first_day = TRAINING_SPEC.partitions[-1].first_day
    params: list[AccountParams] = []
    for account in accounts:
        is_business = account.account_type == "business"
        cold = account.account_id in cold_start_ids
        if cold:
            activation_day = int(rng.integers(test_first_day, test_first_day + 12))
            created = day_start_ts(TRAINING_START, activation_day) - int(rng.integers(3_600, 20 * 3_600))
        else:
            created = training_start - int(rng.integers(120, 2_400)) * DAY_SECONDS
        payees: list[str] = []
        employees: list[str] = []
        if is_business:
            payees += rng.choice(business_cps, size=int(rng.integers(5, 11)), replace=False).tolist()
            payees += rng.choice(biller_ids, size=2, replace=False).tolist()
            for _ in range(int(rng.integers(4, 11))):
                pool = eligible_internal if rng.random() < 0.5 else person_cps
                candidate = str(rng.choice(pool))
                if candidate != account.account_id and candidate not in employees:
                    employees.append(candidate)
        else:
            payees += rng.choice(biller_ids, size=int(rng.integers(1, 4)), replace=False).tolist()
            friends = [f for f in rng.choice(eligible_internal, size=3, replace=False).tolist() if f != account.account_id]
            payees += friends[: int(rng.integers(1, 3))]
            payees += rng.choice(business_cps, size=int(rng.integers(2, 6)), replace=False).tolist()
            payees += rng.choice(person_cps, size=int(rng.integers(0, 3)), replace=False).tolist()
        order = rng.permutation(len(payees))
        payees = [payees[i] for i in order]
        weights = [1.0 / (rank + 1) ** 1.15 for rank in range(len(payees))]
        total = sum(weights)
        factors = [float(np.exp(rng.normal(0, 0.45))) for _ in payees]
        devices = [f"DEV-{account.account_id[4:]}-A"]
        if rng.random() < 0.4:
            devices.append(f"DEV-{account.account_id[4:]}-B")
        auth_choice = rng.dirichlet([6, 3, 1, 1])
        params.append(
            AccountParams(
                account_id=account.account_id,
                account_type=account.account_type,
                home_country=account.home_country,
                created_at=created,
                cold_start=cold,
                activity_weight=float(np.exp(rng.normal(0, 0.85)) * (2.2 if is_business else 1.0)),
                median_amount=float(np.exp(rng.normal(math.log(520 if is_business else 42), 0.55))),
                amount_sigma=float(rng.uniform(0.35, 0.6)),
                payees=payees,
                payee_weights=[w / total for w in weights],
                payee_factors=factors,
                employees=employees,
                devices=devices,
                hour_center=float(rng.normal(12.5, 1.5) if is_business else rng.normal(15.5, 2.8)),
                hour_spread=float(rng.uniform(1.8, 2.8) if is_business else rng.uniform(2.5, 4.2)),
                auth_mix={
                    "biometric": float(auth_choice[0]),
                    "password": float(auth_choice[1]),
                    "otp": float(auth_choice[2]),
                    "password_otp": float(auth_choice[3]),
                },
                payday=int(rng.integers(24, 29)),
                employer=str(rng.choice(business_cps)),
                salary=float(np.exp(rng.normal(math.log(2600), 0.35))),
            )
        )
    return params


# ---------------------------------------------------------------------------
# Draft records
# ---------------------------------------------------------------------------


@dataclass
class Draft:
    ts: int
    sender: str
    recipient: str
    recipient_type: str
    amount: float
    device: str
    session: str
    auth_method: str
    ip_country: str
    channel: str
    scenario: str
    is_fraud: bool
    is_anomaly: bool
    campaign_id: str | None


@dataclass
class _Plan:
    kind: str  # fraud category or unusual type
    is_fraud: bool
    day: int
    size: int
    campaign_id: str


@dataclass
class _State:
    auth_events: list[dict[str, Any]] = field(default_factory=list)
    credits: list[dict[str, Any]] = field(default_factory=list)
    security_events: list[dict[str, Any]] = field(default_factory=list)
    new_counterparties: list[CounterpartyIdentity] = field(default_factory=list)
    session_counter: int = 0
    device_counter: int = 0
    evidence_counter: int = 0
    fraud_evidence_requests: int = 0


class _Generator:
    def __init__(self, spec: DatasetSpec) -> None:
        self.spec = spec
        self.rng = np.random.default_rng(spec.seed)
        self.accounts = build_accounts()
        self.account_by_id = {a.account_id: a for a in self.accounts}
        self.base_counterparties = _build_base_counterparties()
        self.params = {p.account_id: p for p in _build_account_params(self.accounts, self.base_counterparties)}
        self.devices = {p.account_id: list(p.devices) for p in self.params.values()}
        self.employees: dict[str, list[str]] = {}
        self.state = _State()
        reserved = {a.display_name for a in self.accounts} | {c.display_name for c in self.base_counterparties}
        self._reserved_names = reserved
        self._cp_index = 1
        self.biller_ids = [c.counterparty_id for c in self.base_counterparties[:POPULAR_BILLERS]]
        self.base_ids = [c.counterparty_id for c in self.base_counterparties]

    # -- helpers ---------------------------------------------------------
    def _choice(self, values: list[Any], weights: list[float] | None = None) -> Any:
        if weights is None:
            return values[int(self.rng.integers(len(values)))]
        return values[int(self.rng.choice(len(values), p=np.asarray(weights) / sum(weights)))]

    def _new_counterparty(self, business_share: float = 0.35) -> str:
        created = build_counterparties(
            self.rng,
            1,
            f"CP-{self.spec.entity_prefix}",
            self._cp_index,
            reserved_names=self._reserved_names,
            business_share=business_share,
        )[0]
        self._cp_index += 1
        self._reserved_names.add(created.display_name)
        self.state.new_counterparties.append(created)
        return created.counterparty_id

    def _new_device(self) -> str:
        self.state.device_counter += 1
        return f"DEV-{self.spec.entity_prefix}{self.state.device_counter:05d}"

    def _active_accounts(self, ts: int) -> list[str]:
        return [p.account_id for p in self.params.values() if p.created_at <= ts - 3_600]

    def _amount(self, account: str, factor: float = 1.0, sigma: float | None = None) -> float:
        p = self.params[account]
        spread = p.amount_sigma if sigma is None else sigma
        value = p.median_amount * factor * math.exp(self.rng.normal(0, spread))
        return round(max(1.0, min(value, 250_000.0)), 2)

    def _auth_method(self, account: str) -> str:
        mix = self.params[account].auth_mix
        return self._choice(list(mix.keys()), list(mix.values()))

    def _hour_offset(self, account: str) -> int:
        p = self.params[account]
        hour = self.rng.normal(p.hour_center, p.hour_spread) % 24
        return int(hour * 3_600 + self.rng.integers(0, 60))

    def _session(
        self,
        account: str,
        device: str,
        first_request_ts: int,
        auth_method: str,
        failures: int,
        ip_country: str,
    ) -> str:
        self.state.session_counter += 1
        session_id = f"SES-{self.spec.entity_prefix}{self.state.session_counter:07d}"
        success_ts = first_request_ts - int(self.rng.integers(15, 420))
        ts = success_ts - failures * int(self.rng.integers(20, 50))
        for _ in range(failures):
            self.state.auth_events.append(
                {
                    "timestamp": ts,
                    "account_id": account,
                    "session_id": session_id,
                    "device_id": device,
                    "event_type": "login_failure",
                    "auth_method": auth_method,
                    "ip_country": ip_country,
                    "reason": "invalid_credentials",
                }
            )
            ts += int(self.rng.integers(15, 45))
        self.state.auth_events.append(
            {
                "timestamp": success_ts,
                "account_id": account,
                "session_id": session_id,
                "device_id": device,
                "event_type": "login_success",
                "auth_method": auth_method,
                "ip_country": ip_country,
                "reason": None,
            }
        )
        return session_id

    def _draft(
        self,
        ts: int,
        sender: str,
        recipient: str,
        amount: float,
        device: str,
        session: str,
        auth_method: str,
        ip_country: str,
        scenario: str,
        is_fraud: bool,
        is_anomaly: bool,
        campaign_id: str | None,
    ) -> Draft:
        recipient_type = "account" if recipient.startswith("ACC-") else "counterparty"
        channel = "mobile_app" if device.endswith("-A") or self.rng.random() < 0.6 else "web"
        return Draft(
            ts, sender, recipient, recipient_type, amount, device, session, auth_method,
            ip_country, channel, scenario, is_fraud, is_anomaly, campaign_id,
        )

    def _foreign_country(self, account: str) -> str:
        home = self.params[account].home_country
        return self._choice([c for c in COUNTRIES if c != home] + ["US", "GB", "AE", "TR", "UA"])

    def _clamp(self, ts: int, day_start: int) -> int:
        return max(day_start + 60, min(ts, day_start + DAY_SECONDS - 60))

    def _add_evidence(
        self,
        evidence_type: str,
        entity_type: str,
        entity_id: str,
        recorded_at: int,
        effective_from: int,
        effective_until: int | None,
        source: str,
        history: list[dict[str, Any]],
        note: str,
    ) -> None:
        self.state.evidence_counter += 1
        self.state.security_events.append(
            {
                "evidence_id": f"SEC-{self.spec.entity_prefix}{self.state.evidence_counter:05d}",
                "evidence_type": evidence_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "source": source,
                "recorded_at": recorded_at,
                "effective_from": effective_from,
                "effective_until": effective_until,
                "status_history": history,
                "note": note,
            }
        )

    def _confirmed_history(self, at: int) -> list[dict[str, Any]]:
        return [{"status": "confirmed", "at": at, "reason": "investigation_confirmed"}]

    # -- routine ---------------------------------------------------------
    def routine(self, count: int, day_start: int) -> list[Draft]:
        active = self._active_accounts(day_start)
        weights = [self.params[a].activity_weight for a in active]
        drafts: list[Draft] = []
        senders = self.rng.choice(len(active), size=count, p=np.asarray(weights) / sum(weights))
        for index in senders:
            sender = active[int(index)]
            p = self.params[sender]
            ts = self._clamp(day_start + self._hour_offset(sender), day_start)
            if self.rng.random() < 0.06:
                # Ordinary people also pay payees nobody in the dataset has paid before.
                recipient = self._new_counterparty(0.6) if self.rng.random() < 0.5 else self._choice(self.base_ids)
                factor = float(np.exp(self.rng.normal(0, 0.4)))
            else:
                slot = int(self.rng.choice(len(p.payees), p=p.payee_weights))
                recipient = p.payees[slot]
                factor = p.payee_factors[slot]
            if recipient.startswith("ACC-") and self.params[recipient].created_at > ts:
                recipient = self.biller_ids[0]
            if self.rng.random() < 0.0015:  # a legitimate device replacement becomes the new primary
                new_device = self._new_device()
                self.devices[sender] = [new_device] + self.devices[sender][:1]
            devices = self.devices[sender]
            device = devices[0] if len(devices) == 1 or self.rng.random() < 0.88 else devices[1]
            failures = 1 if self.rng.random() < 0.03 else (2 if self.rng.random() < 0.006 else 0)
            ip = p.home_country if self.rng.random() < 0.985 else self._foreign_country(sender)
            method = self._auth_method(sender)
            session = self._session(sender, device, ts, method, failures, ip)
            drafts.append(
                self._draft(
                    ts, sender, recipient, self._amount(sender, factor), device, session, method, ip,
                    "routine_payment", False, False, None,
                )
            )
        return drafts

    def incoming_credits(self, day: int, day_start: int) -> None:
        current = datetime.fromtimestamp(day_start, UTC)
        for p in self.params.values():
            if p.created_at > day_start:
                continue
            if p.account_type == "personal" and current.day == p.payday:
                self.state.credits.append(
                    {
                        "timestamp": day_start + int(self.rng.integers(6 * 3_600, 10 * 3_600)),
                        "from_id": p.employer,
                        "to_id": p.account_id,
                        "amount": round(p.salary * math.exp(self.rng.normal(0, 0.05)), 2),
                        "credit_type": "salary",
                    }
                )
            elif p.account_type == "business" and self.rng.random() < 0.35 * self.spec.activity_scale * 3:
                self.state.credits.append(
                    {
                        "timestamp": day_start + int(self.rng.integers(8 * 3_600, 18 * 3_600)),
                        "from_id": self._choice(self.base_ids),
                        "to_id": p.account_id,
                        "amount": self._amount(p.account_id, 2.0),
                        "credit_type": "client_payment",
                    }
                )

    # -- fraud -----------------------------------------------------------
    def fraud(self, plan: _Plan, day_start: int) -> list[Draft]:
        handler = getattr(self, f"_fraud_{plan.kind}")
        drafts: list[Draft] = handler(plan, day_start)
        if len(drafts) != plan.size:  # pragma: no cover - defensive
            raise RuntimeError(f"{plan.kind} produced {len(drafts)} instead of {plan.size}")
        return drafts

    def _victim(self, day_start: int, allow_cold: bool = True) -> str:
        candidates = [
            a for a in self._active_accounts(day_start)
            if allow_cold or not self.params[a].cold_start
        ]
        return self._choice(candidates)

    def _campaign_start(self, day_start: int, duration: int, night_bias: float = 0.0) -> int:
        latest = DAY_SECONDS - duration - 600
        if self.rng.random() < night_bias:
            offset = int(self.rng.integers(600, min(6 * 3_600, latest)))
        else:
            offset = int(self.rng.integers(7 * 3_600, max(7 * 3_600 + 1, latest)))
        return day_start + offset

    def _fraud_account_takeover(self, plan: _Plan, day_start: int) -> list[Draft]:
        victim = self._victim(day_start)
        p = self.params[victim]
        subtle = self.rng.random() < 0.2
        device = self.devices[victim][0] if subtle else self._new_device()
        failures = 0 if subtle else int(min(6, 1 + self.rng.poisson(1.6)))
        ip = p.home_country if subtle or self.rng.random() < 0.5 else self._foreign_country(victim)
        method = "otp" if subtle else self._choice(["password", "otp", "password"])
        start = self._campaign_start(day_start, plan.size * 1_800, night_bias=0.35)
        session = self._session(victim, device, start, method, failures, ip)
        beneficiary = self._new_counterparty()
        drafts = []
        ts = start
        for _ in range(plan.size):
            factor = float(self.rng.uniform(0.8, 1.5) if subtle else self.rng.uniform(2.0, 9.0))
            drafts.append(
                self._draft(
                    self._clamp(ts, day_start), victim, beneficiary, self._amount(victim, factor, 0.15),
                    device, session, method, ip, "account_takeover", True, not subtle, plan.campaign_id,
                )
            )
            ts += int(self.rng.integers(300, 1_800))
        if self.rng.random() < 0.35:
            recorded = drafts[0].ts + int(self.rng.integers(90, 280))
            self._add_evidence(
                "compromised_session", "session", session, recorded, start - 400, recorded + 30 * DAY_SECONDS,
                TRUSTED_SOURCES[0], self._confirmed_history(recorded),
                "Session confirmed compromised after customer contact (simulated).",
            )
        return drafts

    def _fraud_mule_flow(self, plan: _Plan, day_start: int) -> list[Draft]:
        mule = self._victim(day_start)
        p = self.params[mule]
        subtle = self.rng.random() < 0.2
        start = self._campaign_start(day_start, 10 * 3_600)
        total_in = float(self.rng.uniform(400, 1_500) if subtle else self.rng.uniform(1_800, 9_000))
        sources = int(self.rng.integers(2, 5))
        ts = start
        for share in self.rng.dirichlet(np.ones(sources)):
            self.state.credits.append(
                {
                    "timestamp": ts,
                    "from_id": self._new_counterparty(business_share=0.1),
                    "to_id": mule,
                    "amount": round(total_in * float(share), 2),
                    "credit_type": "incoming_transfer",
                }
            )
            ts += int(self.rng.integers(300, 3_600))
        beneficiaries = [self._new_counterparty() for _ in range(int(self.rng.integers(1, 3)))]
        device = self.devices[mule][0] if self.rng.random() < 0.6 else self._new_device()
        method = self._auth_method(mule)
        ts += int(self.rng.integers(600, 4_000))
        session = self._session(mule, device, ts, method, 0, p.home_country)
        drafts = []
        per_request = total_in * float(self.rng.uniform(0.75, 0.95)) / plan.size
        for index in range(plan.size):
            amount = round(per_request * float(self.rng.uniform(0.85, 1.15)), 2)
            drafts.append(
                self._draft(
                    self._clamp(ts, day_start), mule, beneficiaries[index % len(beneficiaries)], amount,
                    device, session, method, p.home_country, "mule_flow", True, not subtle, plan.campaign_id,
                )
            )
            ts += int(self.rng.integers(120, 1_500))
        if self.rng.random() < 0.3:
            recorded = drafts[0].ts + int(self.rng.integers(60, 400))
            self._add_evidence(
                "fraud_controlled_beneficiary", "counterparty", beneficiaries[0], recorded, recorded, None,
                TRUSTED_SOURCES[1], self._confirmed_history(recorded),
                "Beneficiary confirmed as a money-mule collection account (simulated).",
            )
        return drafts

    def _fraud_velocity(self, plan: _Plan, day_start: int) -> list[Draft]:
        victim = self._victim(day_start)
        p = self.params[victim]
        subtle = self.rng.random() < 0.2
        spacing = (1_200, 4_200) if subtle else (60, 600)
        start = self._campaign_start(day_start, plan.size * spacing[1], night_bias=0.2)
        new_device = self.rng.random() < 0.5
        device = self._new_device() if new_device else self.devices[victim][0]
        failures = int(self.rng.integers(1, 4)) if self.rng.random() < 0.3 else 0
        method = self._auth_method(victim)
        session = self._session(victim, device, start, method, failures, p.home_country)
        beneficiaries = [self._new_counterparty() for _ in range(int(self.rng.integers(1, 3)))]
        drafts = []
        ts = start
        for index in range(plan.size):
            factor = float(self.rng.uniform(0.6, 1.4) if subtle else self.rng.uniform(0.9, 2.5))
            drafts.append(
                self._draft(
                    self._clamp(ts, day_start), victim, beneficiaries[index % len(beneficiaries)],
                    self._amount(victim, factor, 0.2), device, session, method, p.home_country,
                    "velocity", True, not subtle, plan.campaign_id,
                )
            )
            ts += int(self.rng.integers(*spacing))
        if new_device and self.rng.random() < 0.25 and len(drafts) > 1:
            recorded = drafts[1].ts - int(self.rng.integers(5, 40))
            self._add_evidence(
                "compromised_device", "device", device, recorded, start - 600, recorded + 14 * DAY_SECONDS,
                TRUSTED_SOURCES[0], self._confirmed_history(recorded),
                "Device fingerprint confirmed in a malware investigation (simulated).",
            )
        return drafts

    def _fraud_social_engineering(self, plan: _Plan, day_start: int) -> list[Draft]:
        victim = self._victim(day_start, allow_cold=False)
        p = self.params[victim]
        ordinary = self.rng.random() < 0.4
        device = self.devices[victim][0]
        # Some scams route money through an established (compromised) counterparty.
        reuse = ordinary and self.rng.random() < 0.5
        beneficiary = self._choice(self.base_ids[POPULAR_BILLERS:]) if reuse else self._new_counterparty(0.3)
        start = self._campaign_start(day_start, plan.size * 5_400)
        drafts = []
        ts = start
        for _ in range(plan.size):
            method = "biometric"
            session = self._session(victim, device, ts, method, 0, p.home_country)
            factor = float(self.rng.uniform(0.6, 1.3) if ordinary else self.rng.uniform(1.5, 6.0))
            drafts.append(
                self._draft(
                    self._clamp(ts, day_start), victim, beneficiary, self._amount(victim, factor, 0.15),
                    device, session, method, p.home_country, "social_engineering", True, not ordinary,
                    plan.campaign_id,
                )
            )
            ts += int(self.rng.integers(900, 5_400))
        if not reuse and self.rng.random() < 0.15:  # never flag an established counterparty others still pay
            recorded = start - int(self.rng.integers(3_600, 3 * DAY_SECONDS))
            self._add_evidence(
                "fraud_controlled_beneficiary", "counterparty", beneficiary, recorded, recorded, None,
                TRUSTED_SOURCES[1], self._confirmed_history(recorded),
                "Beneficiary linked to a confirmed impersonation scam (simulated).",
            )
        return drafts

    def _fraud_coordinated(self, plan: _Plan, day_start: int) -> list[Draft]:
        subtle = self.rng.random() < 0.25
        window = (4 * 3_600, 8 * 3_600) if subtle else (1_800, 3 * 3_600)
        duration = int(self.rng.integers(*window))
        start = self._campaign_start(day_start, duration)
        senders = self.rng.choice(self._active_accounts(day_start), size=plan.size, replace=False).tolist()
        beneficiary = self._new_counterparty(business_share=0.2)
        base_amount = float(self.rng.uniform(150, 900))
        drafts = []
        for sender in senders:
            p = self.params[sender]
            ts = start + int(self.rng.integers(0, duration))
            device = self._new_device() if self.rng.random() < 0.45 else self.devices[sender][0]
            failures = int(self.rng.integers(0, 3)) if device.startswith(f"DEV-{self.spec.entity_prefix}") else 0
            method = self._auth_method(sender)
            session = self._session(sender, device, ts, method, failures, p.home_country)
            amount = base_amount * float(self.rng.uniform(0.5, 1.6) if subtle else self.rng.uniform(0.9, 1.1))
            drafts.append(
                self._draft(
                    self._clamp(ts, day_start), sender, beneficiary, round(amount, 2), device, session, method,
                    p.home_country, "coordinated", True, not subtle, plan.campaign_id,
                )
            )
        if self.rng.random() < 0.4:
            first = min(d.ts for d in drafts)
            recorded = first - int(self.rng.integers(1_800, 2 * DAY_SECONDS)) if self.rng.random() < 0.6 else first + 900
            self._add_evidence(
                "fraud_controlled_beneficiary", "counterparty", beneficiary, recorded, recorded, None,
                TRUSTED_SOURCES[0], self._confirmed_history(recorded),
                "Beneficiary confirmed as the collection point of a phishing campaign (simulated).",
            )
        return drafts

    # -- unusual but legitimate -----------------------------------------
    def unusual(self, plan: _Plan, day_start: int) -> list[Draft]:
        handler = getattr(self, f"_unusual_{plan.kind}")
        drafts: list[Draft] = handler(plan, day_start)
        if len(drafts) != plan.size:  # pragma: no cover - defensive
            raise RuntimeError(f"{plan.kind} produced {len(drafts)} instead of {plan.size}")
        return drafts

    def _legit(self, ts: int, sender: str, recipient: str, amount: float, plan: _Plan, **kw: Any) -> Draft:
        p = self.params[sender]
        device = kw.get("device") or self.devices[sender][0]
        method = kw.get("method") or self._auth_method(sender)
        ip = kw.get("ip") or p.home_country
        session = kw.get("session") or self._session(sender, device, ts, method, kw.get("failures", 0), ip)
        return self._draft(ts, sender, recipient, amount, device, session, method, ip, plan.kind, False, True, plan.campaign_id)

    def _known_payee(self, sender: str) -> str:
        p = self.params[sender]
        return p.payees[int(self.rng.choice(len(p.payees), p=p.payee_weights))]

    def _unusual_large_planned_purchase(self, plan: _Plan, day_start: int) -> list[Draft]:
        sender = self._victim(day_start)
        ts = self._clamp(day_start + self._hour_offset(sender), day_start)
        recipient = self._known_payee(sender) if self.rng.random() < 0.5 else self._new_counterparty(0.9)
        amount = self._amount(sender, float(self.rng.uniform(5, 22)), 0.2)
        method = self._choice(["password_otp", "biometric"])
        return [self._legit(ts, sender, recipient, amount, plan, method=method)]

    def _unusual_new_device_legitimate(self, plan: _Plan, day_start: int) -> list[Draft]:
        sender = self._victim(day_start)
        device = self._new_device()
        self.devices[sender] = [device] + self.devices[sender][:1]
        ts = self._clamp(day_start + self._hour_offset(sender), day_start)
        failures = int(self.rng.integers(1, 3)) if self.rng.random() < 0.3 else 0
        method = self._choice(["password_otp", "otp", "password"])
        session = self._session(sender, device, ts, method, failures, self.params[sender].home_country)
        drafts = []
        for _ in range(plan.size):
            drafts.append(
                self._legit(ts, sender, self._known_payee(sender), self._amount(sender), plan,
                            device=device, method=method, session=session)
            )
            ts = self._clamp(ts + int(self.rng.integers(120, 2_400)), day_start)
        return drafts

    def _unusual_travel(self, plan: _Plan, day_start: int) -> list[Draft]:
        sender = self._victim(day_start)
        ip = self._foreign_country(sender)
        device = self.devices[sender][0] if self.rng.random() < 0.7 else self._new_device()
        start = self._campaign_start(day_start, 6 * 3_600, night_bias=0.3)
        drafts = []
        ts = start
        for _ in range(plan.size):
            recipient = self._new_counterparty(0.95) if self.rng.random() < 0.6 else self._known_payee(sender)
            drafts.append(
                self._legit(self._clamp(ts, day_start), sender, recipient,
                            self._amount(sender, float(self.rng.uniform(0.6, 2.5))), plan, device=device, ip=ip)
            )
            ts += int(self.rng.integers(1_200, 5_400))
        return drafts

    def _unusual_payroll_burst(self, plan: _Plan, day_start: int) -> list[Draft]:
        businesses = [a for a in self._active_accounts(day_start) if self.params[a].account_type == "business"]
        sender = self._choice(businesses)
        p = self.params[sender]
        employees = self.employees.setdefault(sender, list(p.employees))
        while len(employees) < plan.size:  # a new hire stays on the payroll for later runs
            employees.append(self._new_counterparty(0.0))
        start = self._campaign_start(day_start, 3_600)
        device = self.devices[sender][0]
        method = self._auth_method(sender)
        session = self._session(sender, device, start, method, 0, p.home_country)
        drafts = []
        ts = start
        for index in range(plan.size):
            recipient = employees[index]
            if recipient.startswith("ACC-") and self.params[recipient].created_at > ts:
                recipient = employees[index] = self._new_counterparty(0.0)
            drafts.append(
                self._legit(self._clamp(ts, day_start), sender, recipient, round(float(self.rng.uniform(1_400, 4_200)), 2),
                            plan, device=device, method=method, session=session)
            )
            ts += int(self.rng.integers(20, 240))
        return drafts

    def _unusual_household_repeat(self, plan: _Plan, day_start: int) -> list[Draft]:
        sender = self._victim(day_start)
        recipient = self._known_payee(sender)
        start = self._campaign_start(day_start, 5 * 3_600)
        drafts = []
        ts = start
        for _ in range(plan.size):
            drafts.append(self._legit(self._clamp(ts, day_start), sender, recipient,
                                      self._amount(sender, float(self.rng.uniform(0.3, 1.0))), plan))
            ts += int(self.rng.integers(600, 4_800))
        return drafts

    def _unusual_business_settlement(self, plan: _Plan, day_start: int) -> list[Draft]:
        businesses = [a for a in self._active_accounts(day_start) if self.params[a].account_type == "business"]
        sender = self._choice(businesses)
        recipient = self._known_payee(sender)
        ts = self._clamp(day_start + self._hour_offset(sender), day_start)
        drafts = []
        for _ in range(plan.size):
            drafts.append(self._legit(ts, sender, recipient, self._amount(sender, float(self.rng.uniform(3, 10)), 0.2),
                                      plan, method="password_otp"))
            ts = self._clamp(ts + int(self.rng.integers(300, 3_600)), day_start)
        return drafts

    def _unusual_new_recipient_legitimate(self, plan: _Plan, day_start: int) -> list[Draft]:
        sender = self._victim(day_start)
        ts = self._clamp(day_start + self._hour_offset(sender), day_start)
        amount = self._amount(sender, float(self.rng.uniform(1.0, 3.5)))
        return [self._legit(ts, sender, self._new_counterparty(0.5), amount, plan)]

    def _unusual_shared_group_payment(self, plan: _Plan, day_start: int) -> list[Draft]:
        recipient = self._new_counterparty(0.4)
        senders = self.rng.choice(self._active_accounts(day_start), size=plan.size, replace=False).tolist()
        start = self._campaign_start(day_start, 5 * 3_600)
        amount = float(self.rng.uniform(25, 180))
        return [
            self._legit(self._clamp(start + int(self.rng.integers(0, 5 * 3_600)), day_start), str(sender), recipient,
                        round(amount * float(self.rng.uniform(0.95, 1.05)), 2), plan)
            for sender in senders
        ]

    def _unusual_account_recovery(self, plan: _Plan, day_start: int) -> list[Draft]:
        sender = self._victim(day_start)
        ts = self._clamp(day_start + self._hour_offset(sender), day_start)
        device = self.devices[sender][0]
        session = self._session(sender, device, ts, "password", int(self.rng.integers(2, 5)), self.params[sender].home_country)
        drafts = []
        for _ in range(plan.size):
            drafts.append(self._legit(ts, sender, self._known_payee(sender), self._amount(sender), plan,
                                      device=device, method="password", session=session))
            ts = self._clamp(ts + int(self.rng.integers(120, 1_800)), day_start)
        return drafts

    # -- non-triggering evidence fixtures -------------------------------
    def evidence_fixtures(self, first_ts: int, last_ts: int) -> dict[str, int]:
        billers = self.biller_ids
        counts: dict[str, int] = {}

        def add(kind: str, **kwargs: Any) -> None:
            counts[kind] = counts.get(kind, 0) + 1
            self._add_evidence(**kwargs)

        for index in range(2):
            target = billers[index]
            add("expired", evidence_type="fraud_controlled_beneficiary", entity_type="counterparty", entity_id=target,
                recorded_at=first_ts - 40 * DAY_SECONDS, effective_from=first_ts - 40 * DAY_SECONDS,
                effective_until=first_ts - 5 * DAY_SECONDS, source=TRUSTED_SOURCES[0],
                history=self._confirmed_history(first_ts - 40 * DAY_SECONDS),
                note="Fixture: expired before the dataset period.")
            retract_at = first_ts - 10 * DAY_SECONDS
            add("retracted", evidence_type="fraud_controlled_beneficiary", entity_type="counterparty",
                entity_id=billers[index + 2], recorded_at=first_ts - 20 * DAY_SECONDS,
                effective_from=first_ts - 20 * DAY_SECONDS, effective_until=None, source=TRUSTED_SOURCES[1],
                history=self._confirmed_history(first_ts - 20 * DAY_SECONDS)
                + [{"status": "retracted", "at": retract_at, "reason": "false_positive_confirmed"}],
                note="Fixture: retracted before the dataset period.")
            add("future", evidence_type="fraud_controlled_beneficiary", entity_type="counterparty",
                entity_id=billers[index + 4], recorded_at=last_ts + 3 * DAY_SECONDS,
                effective_from=first_ts, effective_until=None, source=TRUSTED_SOURCES[0],
                history=self._confirmed_history(last_ts + 3 * DAY_SECONDS),
                note="Fixture: recorded after every request in this dataset.")
            add("pending_review", evidence_type="fraud_controlled_beneficiary", entity_type="counterparty",
                entity_id=billers[index + 6], recorded_at=first_ts - DAY_SECONDS, effective_from=first_ts - DAY_SECONDS,
                effective_until=None, source=TRUSTED_SOURCES[0],
                history=[{"status": "pending_review", "at": first_ts - DAY_SECONDS, "reason": "tip_received"}],
                note="Fixture: never confirmed.")
            add("untrusted_source", evidence_type="fraud_controlled_beneficiary", entity_type="counterparty",
                entity_id=billers[index + 8], recorded_at=first_ts - DAY_SECONDS, effective_from=first_ts - DAY_SECONDS,
                effective_until=None, source=UNTRUSTED_SOURCE,
                history=self._confirmed_history(first_ts - DAY_SECONDS),
                note="Fixture: confirmed only by an untrusted external feed.")
        return counts

    def administrative_revocations(self, drafts: list[Draft]) -> int:
        legit = [d for d in drafts if not d.is_fraud]
        picks = self.rng.choice(len(legit), size=min(25, len(legit)), replace=False)
        for index in picks:
            draft = legit[int(index)]
            self.state.auth_events.append(
                {
                    "timestamp": draft.ts + 1_800,
                    "account_id": draft.sender,
                    "session_id": draft.session,
                    "device_id": draft.device,
                    "event_type": "session_revoked",
                    "auth_method": draft.auth_method,
                    "ip_country": draft.ip_country,
                    "reason": "administrative_logout",
                }
            )
        return len(picks)


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

FRAUD_SIZES = {
    "account_takeover": (1, 4),
    "mule_flow": (3, 6),
    "velocity": (4, 9),
    "social_engineering": (1, 3),
    "coordinated": (3, 7),
}
UNUSUAL_SIZES = {
    "large_planned_purchase": (1, 1),
    "new_device_legitimate": (1, 2),
    "travel": (2, 4),
    "payroll_burst": (5, 10),
    "household_repeat": (3, 5),
    "business_settlement": (1, 2),
    "new_recipient_legitimate": (1, 1),
    "shared_group_payment": (3, 6),
    "account_recovery": (1, 2),
}


def _split_total(rng: np.random.Generator, total: int, low: int, high: int) -> list[int]:
    sizes: list[int] = []
    remaining = total
    while remaining > 0:
        size = int(rng.integers(low, high + 1))
        size = min(size, remaining)
        sizes.append(size)
        remaining -= size
    return sizes


def _plan(spec: DatasetSpec, rng: np.random.Generator) -> list[_Plan]:
    plans: list[_Plan] = []
    counter = 0
    for partition in spec.partitions:
        days = list(range(partition.first_day, partition.last_day + 1))
        for category in FRAUD_CATEGORIES:
            low, high = FRAUD_SIZES[category]
            for size in _split_total(rng, spec.fraud_per_category[partition.name], low, high):
                counter += 1
                plans.append(_Plan(category, True, int(rng.choice(days)), size,
                                   f"CMP-{spec.entity_prefix}{counter:04d}"))
        remaining = spec.unusual_per_partition[partition.name]
        while remaining > 0:
            kind = UNUSUAL_TYPES[int(rng.choice(len(UNUSUAL_TYPES), p=UNUSUAL_WEIGHTS))]
            low, high = UNUSUAL_SIZES[kind]
            size = min(int(rng.integers(low, high + 1)), remaining)
            if kind in {"payroll_burst", "shared_group_payment", "household_repeat"} and size < 3:
                kind = "new_recipient_legitimate" if size == 1 else "travel"
            counter += 1
            plans.append(_Plan(kind, False, int(rng.choice(days)), size, f"EP-{spec.entity_prefix}{counter:05d}"))
            remaining -= size
    return plans


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False))
            handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def request_fingerprint(row: dict[str, Any]) -> str:
    material = f"{row['timestamp']}|{row['sender_id']}|{row['recipient_id']}|{row['amount']:.2f}|{row['device_id']}"
    return hashlib.sha256(material.encode()).hexdigest()


def generate_dataset(output_dir: Path, spec: DatasetSpec) -> dict[str, Any]:
    """Generate one dataset into `output_dir` and return its manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    gen = _Generator(spec)
    plans = _plan(spec, gen.rng)
    by_day: dict[int, list[_Plan]] = {}
    for plan in plans:
        by_day.setdefault(plan.day, []).append(plan)

    drafts: list[Draft] = []
    for day in range(1, spec.days + 1):
        start = day_start_ts(spec.start, day)
        gen.incoming_credits(day, start)
        scheduled: list[Draft] = []
        for plan in by_day.get(day, []):
            scheduled += gen.fraud(plan, start) if plan.is_fraud else gen.unusual(plan, start)
        routine_count = spec.requests_per_day - len(scheduled)
        if routine_count < 0:
            raise RuntimeError(f"Day {day} is over capacity ({len(scheduled)} scheduled requests)")
        drafts += scheduled + gen.routine(routine_count, start)

    first_ts = day_start_ts(spec.start, 1)
    last_ts = day_start_ts(spec.start, spec.days) + DAY_SECONDS - 1
    fixture_counts = gen.evidence_fixtures(first_ts, last_ts)
    revocations = gen.administrative_revocations(drafts)

    drafts.sort(key=lambda d: (d.ts, d.sender, d.recipient, d.amount, d.session))
    requests, labels, splits, payments = [], [], [], []
    partition_of_day = {
        day: partition.name
        for partition in spec.partitions
        for day in range(partition.first_day, partition.last_day + 1)
    }
    for index, draft in enumerate(drafts, start=1):
        request_id = f"{spec.request_prefix}-{index:06d}"
        requests.append(
            {
                "request_id": request_id,
                "timestamp": iso(draft.ts),
                "sender_id": draft.sender,
                "recipient_id": draft.recipient,
                "recipient_type": draft.recipient_type,
                "amount": draft.amount,
                "currency": CURRENCY,
                "channel": draft.channel,
                "device_id": draft.device,
                "session_id": draft.session,
                "auth_method": draft.auth_method,
                "ip_country": draft.ip_country,
            }
        )
        labels.append(
            {
                "request_id": request_id,
                "is_fraud": draft.is_fraud,
                "is_anomaly": draft.is_anomaly,
                "scenario": draft.scenario,
                "campaign_id": draft.campaign_id,
            }
        )
        day = (draft.ts - first_ts) // DAY_SECONDS + 1
        splits.append({"request_id": request_id, "partition": partition_of_day[int(day)]})
        payments.append(
            {
                "timestamp": draft.ts + int(gen.rng.integers(2, 15)),
                "event_type": "transfer_settled",
                "from_id": draft.sender,
                "to_id": draft.recipient,
                "amount": draft.amount,
                "currency": CURRENCY,
                "request_id": request_id,
            }
        )
    for credit in gen.state.credits:
        payments.append(
            {
                "timestamp": credit["timestamp"],
                "event_type": "incoming_credit",
                "from_id": credit["from_id"],
                "to_id": credit["to_id"],
                "amount": credit["amount"],
                "currency": CURRENCY,
                "request_id": None,
            }
        )
    payments.sort(key=lambda e: (e["timestamp"], e["event_type"], e["to_id"], e["amount"]))
    payment_rows = [
        {"event_id": f"PE-{spec.entity_prefix}{i:07d}", **e, "timestamp": iso(e["timestamp"])}
        for i, e in enumerate(payments, start=1)
    ]
    auth_sorted = sorted(gen.state.auth_events, key=lambda e: (e["timestamp"], e["session_id"], e["event_type"]))
    auth_rows = [
        {"event_id": f"AE-{spec.entity_prefix}{i:07d}", **e, "timestamp": iso(e["timestamp"])}
        for i, e in enumerate(auth_sorted, start=1)
    ]
    security_rows = []
    for event in sorted(gen.state.security_events, key=lambda e: e["evidence_id"]):
        security_rows.append(
            {
                **event,
                "recorded_at": iso(event["recorded_at"]),
                "effective_from": iso(event["effective_from"]),
                "effective_until": iso(event["effective_until"]) if event["effective_until"] is not None else None,
                "status_history": [{**h, "at": iso(h["at"])} for h in event["status_history"]],
            }
        )

    account_rows = [
        {
            "account_id": a.account_id,
            "display_name": a.display_name,
            "account_type": a.account_type,
            "home_country": a.home_country,
            "created_at": iso(gen.params[a.account_id].created_at),
        }
        for a in gen.accounts
    ]
    counterparty_rows = [
        {"counterparty_id": c.counterparty_id, "display_name": c.display_name, "kind": c.kind, "category": c.category}
        for c in gen.base_counterparties + gen.state.new_counterparties
    ]
    param_rows = [
        {key: value for key, value in asdict(p).items()} | {"created_at": iso(p.created_at)}
        for p in gen.params.values()
    ]

    _write_jsonl(output_dir / "accounts.jsonl", account_rows)
    _write_jsonl(output_dir / "counterparties.jsonl", counterparty_rows)
    _write_jsonl(output_dir / "requests.jsonl", requests)
    _write_jsonl(output_dir / "payment_events.jsonl", payment_rows)
    _write_jsonl(output_dir / "authentication_events.jsonl", auth_rows)
    _write_jsonl(output_dir / "security_events.jsonl", security_rows)
    _write_jsonl(output_dir / "evaluation_labels.jsonl", labels)
    _write_jsonl(output_dir / "generator_account_params.jsonl", param_rows)
    if len(spec.partitions) > 1:
        _write_jsonl(output_dir / "split_assignments.jsonl", splits)

    manifest = _manifest(spec, output_dir, requests, labels, splits, account_rows, counterparty_rows,
                         payment_rows, auth_rows, security_rows, fixture_counts, revocations, gen)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _manifest(
    spec: DatasetSpec,
    output_dir: Path,
    requests: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    splits: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
    counterparties: list[dict[str, Any]],
    payments: list[dict[str, Any]],
    auth: list[dict[str, Any]],
    security: list[dict[str, Any]],
    fixtures: dict[str, int],
    revocations: int,
    gen: _Generator,
) -> dict[str, Any]:
    partition_by_id = {s["request_id"]: s["partition"] for s in splits}
    by_partition: dict[str, dict[str, Any]] = {}
    by_scenario: dict[str, int] = {}
    for label in labels:
        part = partition_by_id[label["request_id"]]
        bucket = by_partition.setdefault(
            part,
            {"requests": 0, "fraud": 0, "legitimate": 0, "unusual_legitimate": 0, "fraud_by_category": {}},
        )
        bucket["requests"] += 1
        by_scenario[label["scenario"]] = by_scenario.get(label["scenario"], 0) + 1
        if label["is_fraud"]:
            bucket["fraud"] += 1
            cats = bucket["fraud_by_category"]
            cats[label["scenario"]] = cats.get(label["scenario"], 0) + 1
        else:
            bucket["legitimate"] += 1
            if label["scenario"] != "routine_payment":
                bucket["unusual_legitimate"] += 1
    fraud = sum(1 for l in labels if l["is_fraud"])
    unusual = sum(1 for l in labels if not l["is_fraud"] and l["scenario"] != "routine_payment")
    files = {}
    for name in RUNTIME_FILES + OFFLINE_FILES + (("split_assignments.jsonl",) if len(spec.partitions) > 1 else ()):
        path = output_dir / name
        files[name] = {
            "sha256": sha256_file(path),
            "lines": sum(1 for _ in path.open("rb")),
            "role": "runtime" if name in RUNTIME_FILES else "offline_only",
        }
    cold_start = sorted(p.account_id for p in gen.params.values() if p.cold_start)
    campaign_evidence = [e for e in security if not e["note"].startswith("Fixture")]
    return {
        "dataset": spec.name,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "seed": spec.seed,
        "identity_seed": IDENTITY_SEED,
        "provenance": (
            "Fully synthetic data produced by storage/generator.py. Accounts, counterparties, payments, "
            "sessions and security evidence are generated; they describe no real people, businesses, or "
            "confirmed fraud cases. Security evidence is a simulated trusted server-side stream."
        ),
        "date_range": {"start": requests[0]["timestamp"], "end": requests[-1]["timestamp"]},
        "days": spec.days,
        "requests_per_day": spec.requests_per_day,
        "partitions": [asdict(p) for p in spec.partitions],
        "counts": {
            "requests": len(requests),
            "accounts": len(accounts),
            "counterparties": len(counterparties),
            "payment_events": len(payments),
            "authentication_events": len(auth),
            "security_events": len(security),
            "fraud": fraud,
            "legitimate": len(labels) - fraud,
            "unusual_legitimate": unusual,
            "routine_legitimate": len(labels) - fraud - unusual,
            "by_scenario": dict(sorted(by_scenario.items())),
            "by_partition": by_partition,
            "cold_start_accounts": len(cold_start) if spec.cold_start_partition else 0,
        },
        "cold_start": {
            "partition": spec.cold_start_partition,
            "account_ids": cold_start if spec.cold_start_partition else [],
        },
        "security_evidence": {
            "campaign_evidence_events": len(campaign_evidence),
            "fixtures": fixtures,
            "administrative_session_revocations": revocations,
            "trusted_sources": list(TRUSTED_SOURCES),
            "note": "All evidence is simulated. Fixtures must never trigger a confirmed-fraud block.",
        },
        "feature_assumptions": [
            "Runtime features use only events ordered strictly before the request (timestamp, type rank, id).",
            "Labels, scenarios, campaign IDs, split assignments and generator parameters are offline-only.",
            "Payment events are the historical ledger; every historical request settled within seconds.",
        ],
        "files": files,
    }
