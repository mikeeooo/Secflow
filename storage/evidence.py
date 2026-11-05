"""Trusted, time-aware security-evidence lookup.

Evidence comes only from the server-side `security_events.jsonl` stream (or evidence the
server itself records). Client payloads cannot create evidence, and ground-truth labels are
never consulted. At request time `t`, an evidence record is active only if all hold:

* it was recorded at or before `t` (the server knew about it),
* `effective_from <= t` and (`effective_until` is empty or `t < effective_until`),
* its latest status entry at or before `t` is `confirmed` (so later retractions do not
  rewrite the past, and earlier retractions deactivate it),
* its source is one of the configured trusted sources, and its type is a blocking type.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from storage.records import PaymentRequest, parse_ts


@dataclass(frozen=True)
class StatusChange:
    status: str
    at: int
    reason: str | None


@dataclass(frozen=True)
class SecurityEvidence:
    evidence_id: str
    evidence_type: str
    entity_type: str  # session | counterparty | device | account
    entity_id: str
    source: str
    recorded_at: int
    effective_from: int
    effective_until: int | None
    status_history: tuple[StatusChange, ...]
    note: str

    def status_at(self, ts: int) -> str | None:
        current = None
        for change in self.status_history:
            if change.at <= ts:
                current = change.status
        return current


def evidence_from_row(row: dict) -> SecurityEvidence:
    return SecurityEvidence(
        evidence_id=row["evidence_id"],
        evidence_type=row["evidence_type"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        source=row["source"],
        recorded_at=parse_ts(row["recorded_at"]),
        effective_from=parse_ts(row["effective_from"]),
        effective_until=parse_ts(row["effective_until"]) if row.get("effective_until") else None,
        status_history=tuple(
            StatusChange(h["status"], parse_ts(h["at"]), h.get("reason")) for h in row.get("status_history", [])
        ),
        note=row.get("note", ""),
    )


class EvidenceStore:
    def __init__(
        self,
        evidence: Iterable[SecurityEvidence],
        trusted_sources: Sequence[str],
        blocking_types: Sequence[str],
    ) -> None:
        self._trusted = frozenset(trusted_sources)
        self._blocking = frozenset(blocking_types)
        self._all: list[SecurityEvidence] = []
        self._by_entity: dict[tuple[str, str], list[SecurityEvidence]] = {}
        for item in evidence:
            self._add(item)

    def _add(self, item: SecurityEvidence) -> None:
        self._all.append(item)
        self._by_entity.setdefault((item.entity_type, item.entity_id), []).append(item)

    @property
    def records(self) -> tuple[SecurityEvidence, ...]:
        return tuple(self._all)

    def is_active(self, item: SecurityEvidence, ts: int) -> bool:
        if item.source not in self._trusted or item.evidence_type not in self._blocking:
            return False
        if item.recorded_at > ts or item.effective_from > ts:
            return False
        if item.effective_until is not None and ts >= item.effective_until:
            return False
        return item.status_at(ts) == "confirmed"

    def active_for(self, request: PaymentRequest, ts: int | None = None) -> list[SecurityEvidence]:
        """Return active trusted evidence that implicates this request at time `ts`."""
        moment = request.ts if ts is None else ts
        entities = (
            ("session", request.session_id),
            ("device", request.device_id),
            ("account", request.sender_id),
            ("counterparty", request.recipient_id),
            ("account", request.recipient_id),
        )
        found: list[SecurityEvidence] = []
        seen: set[str] = set()
        for entity in entities:
            for item in self._by_entity.get(entity, ()):
                if item.evidence_id not in seen and self.is_active(item, moment):
                    seen.add(item.evidence_id)
                    found.append(item)
        return sorted(found, key=lambda e: e.evidence_id)

    def active_entities(self, entity_type: str, ts: int) -> list[SecurityEvidence]:
        return [
            item for item in self._all if item.entity_type == entity_type and self.is_active(item, ts)
        ]
