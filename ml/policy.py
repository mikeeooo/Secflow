"""Explainable rules, the pure risk combination, and the evidence-first action table.

Nothing here calls an estimator. `combine_scores` only combines component values that were
already computed once per assessment, and `decide_action` is a pure function of those values,
rule results, active trusted evidence, and the frozen operating point.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from storage.evidence import SecurityEvidence

COMPONENTS = ("isolation_forest", "lof", "dbscan", "rules")

DECISION_PERMIT = "Permit"
DECISION_VERIFY = "Verify"
DECISION_BLOCK = "Block"

SOURCE_EVIDENCE = "confirmed_fraud_evidence"
SOURCE_RISK = "risk_policy"
SOURCE_SAFEGUARD = "assessment_safeguard"

UNSAFE_STATUSES = frozenset({"model_unavailable", "invalid_features", "insufficient_history"})


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleSpec:
    code: str
    family: str
    weight: float
    corroborating: bool
    description: str
    params: Mapping[str, Any]


@dataclass(frozen=True)
class Policy:
    name: str
    revision: str
    version: str
    weights: Mapping[str, float]
    initial_verify: float
    initial_block: float
    threshold_search: Mapping[str, Mapping[str, float]]
    goals: Mapping[str, float]
    min_families: int
    families: Mapping[str, str]
    rules: tuple[RuleSpec, ...]
    cold_start_max_amount: float
    strong_auth_methods: frozenset[str]
    trusted_sources: tuple[str, ...]
    blocking_types: tuple[str, ...]
    raw: Mapping[str, Any] = field(repr=False, default_factory=dict)


def load_policy(path: Path) -> Policy:
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text)
    weights = raw["weights"]
    if set(weights) != set(COMPONENTS):
        raise ValueError(f"Policy weights must cover exactly {COMPONENTS}")
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError("Policy weights must sum to 1.0")
    families = raw["corroboration"]["families"]
    rules = tuple(
        RuleSpec(r["code"], r["family"], float(r["weight"]), bool(r["corroborating"]), r["description"], r["params"])
        for r in raw["rules"]
    )
    for rule in rules:
        if rule.family not in families:
            raise ValueError(f"Rule {rule.code} uses unknown family {rule.family}")
    digest = hashlib.sha256(text.encode()).hexdigest()[:8]
    return Policy(
        name=raw["policy_name"],
        revision=raw["policy_revision"],
        version=f"{raw['policy_name']}-{raw['policy_revision']}+{digest}",
        weights=weights,
        initial_verify=float(raw["initial_thresholds"]["verify"]),
        initial_block=float(raw["initial_thresholds"]["block"]),
        threshold_search=raw["threshold_search"],
        goals=raw["validation_goals"],
        min_families=int(raw["corroboration"]["min_distinct_families"]),
        families=families,
        rules=rules,
        cold_start_max_amount=float(raw["cold_start"]["max_amount_without_history"]),
        strong_auth_methods=frozenset(raw["cold_start"]["strong_auth_methods"]),
        trusted_sources=tuple(raw["evidence"]["trusted_sources"]),
        blocking_types=tuple(raw["evidence"]["blocking_types"]),
        raw=raw,
    )


@dataclass(frozen=True)
class OperatingPoint:
    verify: float
    block: float
    source: str  # "validated" | "initial"
    version: str


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TriggeredRule:
    code: str
    family: str
    weight: float
    corroborating: bool
    description: str
    detail: str


@dataclass(frozen=True)
class RuleResult:
    score: float
    triggered: tuple[TriggeredRule, ...]
    corroborating_families: tuple[str, ...]


def _money(value: float | None) -> str:
    return "n/a" if value is None else f"€{value:,.2f}"


def _rule_check(rule: RuleSpec, f: Mapping[str, Any], has_history: bool, fired: set[str]) -> str | None:
    """Return a human-readable detail when the rule fires, otherwise None."""
    p = rule.params
    z = f.get("amount_zscore_30d")
    recent_beneficiary = f.get("recipient_history_days") is None or f["recipient_history_days"] <= p.get(
        "max_recipient_history_days", 7
    )
    if rule.code == "AMOUNT_SPIKE":
        if not has_history or f.get("prior_requests_30d", 0) < 3:
            return None
        ratio = f["amount"] / f["max_amount_30d"] if f.get("max_amount_30d") else 0.0
        if (z is not None and z >= p["min_zscore"]) or ratio >= p["min_ratio_to_prior_max"]:
            return (f"{_money(f['amount'])} versus a 30-day median of {_money(f.get('median_amount_30d'))} "
                    f"(z-score {z if z is not None else 'n/a'}, {ratio:.1f}x the prior 30-day maximum)")
    elif rule.code == "AMOUNT_ELEVATED":
        if has_history and "AMOUNT_SPIKE" not in fired and z is not None and z >= p["min_zscore"]:
            return f"z-score {z} against the sender's 30-day amounts"
    elif rule.code == "VELOCITY_BURST":
        ratio = f.get("velocity_ratio_24h", 0.0)
        if (f["requests_1h"] >= p["min_requests_1h"] and ratio >= p["min_velocity_ratio"] / 2) or (
            f["requests_24h"] >= p["min_requests_24h"] and ratio >= p["min_velocity_ratio"]
        ):
            return f"{f['requests_1h']} payments in the last hour, {f['requests_24h']} in 24 hours ({ratio:.1f}x usual pace)"
    elif rule.code == "RECIPIENT_FANOUT":
        if f["unique_recipients_24h"] >= p["min_unique_recipients_24h"] and f.get("velocity_ratio_24h", 0) >= p["min_velocity_ratio"]:
            return f"{f['unique_recipients_24h']} different recipients in 24 hours"
    elif rule.code == "NEW_DEVICE_AFTER_FAILED_LOGINS":
        if has_history and f.get("device_change") and f["auth_failures_24h"] >= p["min_failures_24h"]:
            return f"device first seen {f.get('device_age_hours') or 0:.1f} h ago, {f['auth_failures_24h']} failed sign-ins in 24 h"
    elif rule.code == "REPEATED_FAILED_LOGINS":
        if f["auth_failures_24h"] >= p["min_failures_24h"]:
            return f"{f['auth_failures_24h']} failed sign-in attempts in 24 hours"
    elif rule.code == "NEW_DEVICE":
        if has_history and f.get("device_change"):
            return f"device first seen {f.get('device_age_hours') or 0:.1f} hours ago"
    elif rule.code == "FOREIGN_SESSION":
        if f["foreign_ip"]:
            return f"session from {f['ip_country']}, home country {f['home_country']}"
    elif rule.code == "SHARED_NEW_BENEFICIARY":
        if f["new_recipient"] and f["recipient_senders_24h"] >= p["min_other_senders_24h"] and recent_beneficiary:
            return f"{f['recipient_senders_24h']} other accounts paid this beneficiary in the last 24 hours"
    elif rule.code == "NEW_BENEFICIARY_HIGH_AMOUNT":
        if has_history and f["new_recipient"] and z is not None and z >= p["min_zscore"]:
            return f"z-score {z} to a beneficiary without an established payment history"
    elif rule.code == "NEW_BENEFICIARY":
        if has_history and f["new_recipient"]:
            hours = f.get("recipient_relationship_hours")
            return "first payment to this beneficiary" if hours is None else f"first paid {hours:.1f} hours ago"
    elif rule.code == "PASS_THROUGH_FUNDS":
        incoming = f.get("incoming_24h", 0.0)
        outflow = f.get("sum_24h", 0.0) + f["amount"]
        if incoming >= p["min_incoming_24h"] and outflow >= p["min_outflow_share"] * incoming and recent_beneficiary:
            return f"{_money(outflow)} sent in 24 hours after receiving {_money(incoming)}"
    return None


def evaluate_rules(facts: Mapping[str, Any], history_status: str, policy: Policy) -> RuleResult:
    has_history = history_status != "none"
    fired: set[str] = set()
    triggered: list[TriggeredRule] = []
    for rule in policy.rules:
        detail = _rule_check(rule, facts, has_history, fired)
        if detail is not None:
            fired.add(rule.code)
            triggered.append(
                TriggeredRule(rule.code, rule.family, rule.weight, rule.corroborating, rule.description, detail)
            )
    score = min(1.0, sum(t.weight for t in triggered))
    families = tuple(sorted({t.family for t in triggered if t.corroborating}))
    return RuleResult(score, tuple(triggered), families)


# ---------------------------------------------------------------------------
# Combination
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComponentScores:
    isolation_forest: float
    lof: float
    dbscan: float
    rules: float

    def __post_init__(self) -> None:
        for name in COMPONENTS:
            value = getattr(self, name)
            if not (isinstance(value, (int, float)) and math.isfinite(value) and 0.0 <= value <= 1.0):
                raise ValueError(f"Component {name} must be finite and within [0, 1], got {value!r}")


@dataclass(frozen=True)
class RiskBreakdown:
    total: float  # unrounded; used for decisions
    contributions: Mapping[str, float]
    components: ComponentScores


def combine_scores(components: ComponentScores, weights: Mapping[str, float]) -> RiskBreakdown:
    """risk = 100 * (0.35 IF + 0.25 LOF + 0.10 DBSCAN + 0.30 rules), with per-component contributions."""
    contributions = {name: 100.0 * weights[name] * getattr(components, name) for name in COMPONENTS}
    return RiskBreakdown(sum(contributions.values()), contributions, components)


def combine_arrays(
    isolation_forest: np.ndarray, lof: np.ndarray, dbscan: np.ndarray, rules: np.ndarray, weights: Mapping[str, float]
) -> np.ndarray:
    """Vectorised form of `combine_scores` for offline evaluation (same formula, tested for equality)."""
    return 100.0 * (
        weights["isolation_forest"] * isolation_forest
        + weights["lof"] * lof
        + weights["dbscan"] * dbscan
        + weights["rules"] * rules
    )


# ---------------------------------------------------------------------------
# Safeguards and decisions
# ---------------------------------------------------------------------------


def assessment_status(
    history_status: str, amount: float, auth_method: str, models_available: bool, features_finite: bool, policy: Policy
) -> tuple[str, list[str]]:
    """Classify whether a request can be assessed safely; returns (status, explanations)."""
    if not models_available:
        return "model_unavailable", ["The anomaly models are not loaded, so no risk score can be computed."]
    if not features_finite:
        return "invalid_features", ["Feature extraction produced non-finite values."]
    if history_status == "none":
        if amount > policy.cold_start_max_amount or auth_method not in policy.strong_auth_methods:
            return "insufficient_history", [
                ("The sender has no earlier payments, so behavioural comparisons are unavailable; "
                f"payments above {_money(policy.cold_start_max_amount)} or without strong authentication need verification.")
            ]
        return "limited_history", ["No earlier payments; assessed with strong authentication and a small amount."]
    if history_status == "limited":
        return "limited_history", ["Fewer than five earlier payments; behavioural baselines are less reliable."]
    return "assessed", []


@dataclass(frozen=True)
class PolicyResult:
    decision: str
    decision_source: str
    label: str
    assessment_status: str
    evidence_ids: tuple[str, ...]
    corroborating_signals: tuple[str, ...]
    explanation: str


def decide_action(
    risk: RiskBreakdown | None,
    rules: RuleResult | None,
    evidence: Sequence[SecurityEvidence],
    status: str,
    operating_point: OperatingPoint,
    policy: Policy,
) -> PolicyResult:
    """Apply the evidence-first action table (priority 1 -> 5)."""
    families = rules.corroborating_families if rules else ()
    if evidence:
        ids = tuple(e.evidence_id for e in evidence)
        kinds = ", ".join(sorted({e.evidence_type.replace("_", " ") for e in evidence}))
        return PolicyResult(
            DECISION_BLOCK, SOURCE_EVIDENCE, "Confirmed fraud evidence", status, ids, families,
            f"Blocked automatically: active trusted security evidence ({kinds}) implicates this request. "
            "The anomaly score is shown for context and did not decide this action.",
        )
    if risk is None or status in UNSAFE_STATUSES:
        return PolicyResult(
            DECISION_VERIFY, SOURCE_SAFEGUARD, "Needs verification", status, (), families,
            "Sent to verification because the request cannot be assessed safely with the information available.",
        )
    if risk.total >= operating_point.block and len(families) >= policy.min_families:
        return PolicyResult(
            DECISION_BLOCK, SOURCE_RISK, "Preventive risk block", status, (), families,
            f"Preventive block: risk {risk.total:.1f} reached the block threshold {operating_point.block:g} and "
            f"{len(families)} distinct behavioural signals corroborate it. This is a risk decision, not confirmed fraud.",
        )
    if risk.total >= operating_point.verify:
        reason = (
            "very high anomaly score without enough independent corroborating signals for a block"
            if risk.total >= operating_point.block
            else "unusual behaviour above the verification threshold"
        )
        return PolicyResult(
            DECISION_VERIFY, SOURCE_RISK, "Needs verification", status, (), families,
            f"Needs verification: {reason} (risk {risk.total:.1f}, threshold {operating_point.verify:g}).",
        )
    return PolicyResult(
        DECISION_PERMIT, SOURCE_RISK, "Permitted", status, (), families,
        f"Permitted: risk {risk.total:.1f} is below the verification threshold {operating_point.verify:g}.",
    )


def decide_arrays(
    risk: np.ndarray,
    families: np.ndarray,
    unsafe: np.ndarray,
    has_evidence: np.ndarray,
    verify: float,
    block: float,
    min_families: int,
) -> np.ndarray:
    """Vectorised `decide_action` returning 0=Permit, 1=Verify, 2=Block (tested for equivalence)."""
    block_mask = has_evidence | (~unsafe & (risk >= block) & (families >= min_families))
    verify_mask = ~block_mask & (unsafe | (risk >= verify))
    return np.where(block_mask, 2, np.where(verify_mask, 1, 0))
