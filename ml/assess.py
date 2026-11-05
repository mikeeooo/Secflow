"""The single assessment pipeline used by live scoring, baseline replay, and evaluation.

features (once) -> IF / LOF / DBSCAN context (once each) -> rules -> pure combination ->
time-aware trusted evidence -> evidence-first action table.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ml.features import FeatureSnapshot, build_features
from ml.model import ModelBundle, ModelComponents
from ml.policy import (
    ComponentScores,
    OperatingPoint,
    Policy,
    PolicyResult,
    RiskBreakdown,
    RuleResult,
    assessment_status,
    combine_scores,
    decide_action,
    evaluate_rules,
)
from storage.evidence import EvidenceStore, SecurityEvidence
from storage.history import HistoryIndex
from storage.records import Account, PaymentRequest


@dataclass(frozen=True)
class AssessmentResult:
    request: PaymentRequest
    snapshot: FeatureSnapshot
    components: ModelComponents | None
    rules: RuleResult
    risk: RiskBreakdown | None
    evidence: tuple[SecurityEvidence, ...]
    policy: PolicyResult
    status_notes: tuple[str, ...]


def finalize(
    request: PaymentRequest,
    snapshot: FeatureSnapshot,
    components: ModelComponents | None,
    evidence_store: EvidenceStore,
    policy: Policy,
    operating_point: OperatingPoint,
) -> AssessmentResult:
    rules = evaluate_rules(snapshot.facts, snapshot.history_status, policy)
    finite = all(math.isfinite(v) for v in snapshot.payment_vector + snapshot.context_vector)
    status, notes = assessment_status(
        snapshot.history_status, request.amount, request.auth_method, components is not None, finite, policy
    )
    risk = None
    if components is not None and finite:
        risk = combine_scores(
            ComponentScores(components.if_score, components.lof_score, components.context.score, rules.score),
            policy.weights,
        )
    evidence = tuple(evidence_store.active_for(request))
    decision = decide_action(risk, rules, evidence, status, operating_point, policy)
    return AssessmentResult(request, snapshot, components, rules, risk, evidence, decision, tuple(notes))


def assess_one(
    request: PaymentRequest,
    key: int,
    history: HistoryIndex,
    account: Account | None,
    bundle: ModelBundle | None,
    evidence_store: EvidenceStore,
    policy: Policy,
    operating_point: OperatingPoint,
) -> AssessmentResult:
    snapshot = build_features(request, key, history, account)
    components = bundle.score(snapshot) if bundle is not None else None
    return finalize(request, snapshot, components, evidence_store, policy, operating_point)


def assess_batch(
    requests: Sequence[PaymentRequest],
    keys: Mapping[str, int],
    history: HistoryIndex,
    accounts: Mapping[str, Account],
    bundle: ModelBundle | None,
    evidence_store: EvidenceStore,
    policy: Policy,
    operating_point: OperatingPoint,
) -> list[AssessmentResult]:
    """Assess many historical requests; each sees only events before its own ordering key."""
    snapshots = [build_features(r, keys[r.request_id], history, accounts.get(r.sender_id)) for r in requests]
    components: list[ModelComponents | None]
    if bundle is not None and snapshots:
        components = list(
            bundle.score_batch(
                np.asarray([s.payment_vector for s in snapshots]),
                np.asarray([s.context_vector for s in snapshots]),
                [s.context_status for s in snapshots],
            )
        )
    else:
        components = [None] * len(snapshots)
    return [
        finalize(r, s, c, evidence_store, policy, operating_point)
        for r, s, c in zip(requests, snapshots, components, strict=True)
    ]


def build_evidence_store(rows: Sequence[dict], policy: Policy) -> EvidenceStore:
    from storage.evidence import evidence_from_row

    return EvidenceStore([evidence_from_row(r) for r in rows], policy.trusted_sources, policy.blocking_types)
