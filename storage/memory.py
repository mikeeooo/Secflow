"""Temporary process-memory state: assessments, reviews, idempotency, and the history overlay.

Everything here lives in one Python process. Restarting the server discards simulations and
reviews; multiple workers or instances would each hold their own independent copy. All
mutations happen under a single re-entrant lock so duplicate detection, scoring and commit
are atomic within the process.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ml.assess import AssessmentResult
from storage.history import HistoryIndex
from storage.records import AuthEvent, PaymentRequest


class ConflictError(RuntimeError):
    """Same request ID with a different payload, or an invalid state transition."""


class NotFoundError(KeyError):
    """Unknown request, account, or other identifier."""


COMPLETED_OUTCOMES = frozenset({"permitted", "approved_after_review"})
OUTCOME_FOR_DECISION = {"Permit": "permitted", "Verify": "pending_verification", "Block": "blocked_attempt"}


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"


@dataclass(frozen=True)
class ReviewRecord:
    review_id: str
    request_id: str
    action: str  # approve | reject
    reason: str
    actor: str
    created_at: str
    simulated_time: int
    original_decision: str
    original_risk_score: float | None
    resulting_outcome: str


@dataclass
class AssessmentRecord:
    """An immutable assessment plus its mutable payment outcome (changed only by a review)."""

    seq: int
    origin: str  # baseline | simulation
    producer: str | None  # manual | stream | None for baseline
    request: PaymentRequest
    key: int
    result: AssessmentResult
    assessed_at: str
    fingerprint: str | None
    session_events: tuple[AuthEvent, ...]
    outcome: str
    reviews: list[ReviewRecord] = field(default_factory=list)
    latency_ms: float | None = None  # measured single-request assessment time (simulations only)


class MemoryState:
    def __init__(self, history: HistoryIndex) -> None:
        self.lock = threading.RLock()
        self.history = history
        self.records: dict[str, AssessmentRecord] = {}
        self.order: list[str] = []
        self.simulation_order: list[str] = []
        self.overlay_counterparties: dict[str, Any] = {}
        self._fingerprints: dict[str, str] = {}
        self._next_seq = 1
        self.review_count = 0

    def next_seq(self) -> int:
        with self.lock:
            value = self._next_seq
            self._next_seq += 1
            return value

    def add_baseline(self, record: AssessmentRecord) -> None:
        with self.lock:
            self.records[record.request.request_id] = record
            self.order.append(record.request.request_id)

    def submit_once(
        self, request_id: str, fingerprint: str, produce: Callable[[], AssessmentRecord]
    ) -> tuple[AssessmentRecord, bool]:
        """Atomically return an existing identical submission or produce and commit a new one.

        Returns (record, replayed). Raises ConflictError for a reused ID with a different payload.
        """
        with self.lock:
            existing = self._fingerprints.get(request_id)
            if existing is not None:
                if existing != fingerprint:
                    raise ConflictError(f"Request ID {request_id} was already used with a different payload")
                return self.records[request_id], True
            if request_id in self.records:
                raise ConflictError(f"Request ID {request_id} belongs to an existing baseline request")
            record = produce()
            self.records[request_id] = record
            self.order.append(request_id)
            self.simulation_order.append(request_id)
            self._fingerprints[request_id] = fingerprint
            return record, False

    def add_review(self, request_id: str, build: Callable[[AssessmentRecord], ReviewRecord]) -> ReviewRecord:
        with self.lock:
            record = self.records.get(request_id)
            if record is None:
                raise NotFoundError(request_id)
            if record.result.policy.decision != "Verify":
                raise ConflictError("Only requests whose automated decision is Verify can be reviewed")
            if record.reviews:
                raise ConflictError("This request already has a final review outcome")
            review = build(record)
            record.reviews.append(review)
            record.outcome = review.resulting_outcome
            self.review_count += 1
            return review
