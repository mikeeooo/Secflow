"""Chronological replay of a dataset through the shared feature function."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

import numpy as np

from ml.features import CONTEXT_FEATURES, PAYMENT_FEATURES, FeatureSnapshot, build_features
from storage.dataset import Dataset
from storage.history import HistoryIndex


@dataclass(frozen=True)
class ReplayResult:
    request_ids: tuple[str, ...]
    payment: np.ndarray
    context: np.ndarray
    history_status: tuple[str, ...]
    context_status: tuple[str, ...]
    facts: dict[str, dict[str, Any]]
    index: HistoryIndex
    keys: dict[str, int]


def replay(dataset: Dataset, keep_facts_for: Collection[str] | None = None) -> ReplayResult:
    """Compute features for every request using only events ordered before it."""
    index, keys = HistoryIndex.from_events(dataset.requests, dataset.auth_events, dataset.payment_events)
    ordered = sorted(dataset.requests, key=lambda r: keys[r.request_id])
    payment = np.empty((len(ordered), len(PAYMENT_FEATURES)), dtype=np.float64)
    context = np.empty((len(ordered), len(CONTEXT_FEATURES)), dtype=np.float64)
    history_status: list[str] = []
    context_status: list[str] = []
    facts: dict[str, dict[str, Any]] = {}
    wanted = set(keep_facts_for) if keep_facts_for is not None else None
    for row, request in enumerate(ordered):
        snapshot: FeatureSnapshot = build_features(
            request, keys[request.request_id], index, dataset.accounts.get(request.sender_id)
        )
        payment[row] = snapshot.payment_vector
        context[row] = snapshot.context_vector
        history_status.append(snapshot.history_status)
        context_status.append(snapshot.context_status)
        if wanted is None or request.request_id in wanted:
            facts[request.request_id] = dict(snapshot.facts)
    if not (np.isfinite(payment).all() and np.isfinite(context).all()):
        raise ValueError("Non-finite feature values produced during replay")
    return ReplayResult(
        tuple(r.request_id for r in ordered), payment, context, tuple(history_status), tuple(context_status),
        facts, index, keys,
    )
