"""Append-only, time-ordered history index used by offline replay and live scoring.

Every query takes an ordering key and only considers events whose key is strictly lower,
so the same index can hold future events without leaking them into earlier features.
Live simulations append to the same structures with keys greater than all baseline keys.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Iterable
from dataclasses import dataclass, field

from storage.records import EVENT_RANK, AuthEvent, PaymentEvent, PaymentRequest, make_key


@dataclass
class _SenderSeries:
    keys: list[int] = field(default_factory=list)
    amounts: list[float] = field(default_factory=list)
    recipients: list[str] = field(default_factory=list)
    cum_amount: list[float] = field(default_factory=lambda: [0.0])
    cum_log: list[float] = field(default_factory=lambda: [0.0])
    cum_log2: list[float] = field(default_factory=lambda: [0.0])
    cum_sin: list[float] = field(default_factory=lambda: [0.0])
    cum_cos: list[float] = field(default_factory=lambda: [0.0])


@dataclass
class _RecipientSeries:
    keys: list[int] = field(default_factory=list)
    senders: list[str] = field(default_factory=list)


@dataclass
class _AuthSeries:
    keys: list[int] = field(default_factory=list)
    devices: list[str] = field(default_factory=list)
    cum_failures: list[int] = field(default_factory=lambda: [0])


@dataclass
class _IncomingSeries:
    keys: list[int] = field(default_factory=list)
    cum_amount: list[float] = field(default_factory=lambda: [0.0])


class HistoryIndex:
    """Chronological view of attempted requests, authentication, and settled/credited flows."""

    def __init__(self) -> None:
        self.sender: dict[str, _SenderSeries] = {}
        self.recipient: dict[str, _RecipientSeries] = {}
        self.pair_first: dict[tuple[str, str], int] = {}
        self.auth: dict[str, _AuthSeries] = {}
        self.device_first: dict[tuple[str, str], int] = {}
        self.incoming: dict[str, _IncomingSeries] = {}
        self.max_key = 0
        self.max_seq = 0

    # -- appends -----------------------------------------------------------
    def _advance(self, key: int) -> None:
        if key <= self.max_key:
            raise ValueError("History appends must use strictly increasing ordering keys")
        self.max_key = key

    def add_request(self, request: PaymentRequest, key: int) -> None:
        self._advance(key)
        series = self.sender.setdefault(request.sender_id, _SenderSeries())
        series.keys.append(key)
        series.amounts.append(request.amount)
        series.recipients.append(request.recipient_id)
        log_amount = math.log1p(request.amount)
        angle = 2 * math.pi * ((request.ts % 86_400) / 86_400)
        series.cum_amount.append(series.cum_amount[-1] + request.amount)
        series.cum_log.append(series.cum_log[-1] + log_amount)
        series.cum_log2.append(series.cum_log2[-1] + log_amount * log_amount)
        series.cum_sin.append(series.cum_sin[-1] + math.sin(angle))
        series.cum_cos.append(series.cum_cos[-1] + math.cos(angle))
        incoming = self.recipient.setdefault(request.recipient_id, _RecipientSeries())
        incoming.keys.append(key)
        incoming.senders.append(request.sender_id)
        self.pair_first.setdefault((request.sender_id, request.recipient_id), key)
        self.device_first.setdefault((request.sender_id, request.device_id), key)

    def add_auth(self, event: AuthEvent, key: int) -> None:
        self._advance(key)
        series = self.auth.setdefault(event.account_id, _AuthSeries())
        series.keys.append(key)
        series.devices.append(event.device_id)
        series.cum_failures.append(series.cum_failures[-1] + (1 if event.event_type == "login_failure" else 0))
        self.device_first.setdefault((event.account_id, event.device_id), key)

    def add_payment(self, event: PaymentEvent, key: int) -> None:
        self._advance(key)
        series = self.incoming.setdefault(event.to_id, _IncomingSeries())
        series.keys.append(key)
        series.cum_amount.append(series.cum_amount[-1] + event.amount)

    # -- bulk construction ------------------------------------------------
    @classmethod
    def from_events(
        cls,
        requests: Iterable[PaymentRequest],
        auth_events: Iterable[AuthEvent],
        payment_events: Iterable[PaymentEvent],
    ) -> tuple[HistoryIndex, dict[str, int]]:
        """Build an index and return the ordering key assigned to each request."""
        merged: list[tuple[int, int, str, object]] = []
        merged += [(e.ts, EVENT_RANK["auth"], e.event_id, e) for e in auth_events]
        merged += [(e.ts, EVENT_RANK["payment"], e.event_id, e) for e in payment_events]
        merged += [(r.ts, EVENT_RANK["request"], r.request_id, r) for r in requests]
        merged.sort(key=lambda item: (item[0], item[1], item[2]))
        index = cls()
        request_keys: dict[str, int] = {}
        for seq, (ts, rank, _, event) in enumerate(merged, start=1):
            key = make_key(ts, seq)
            if rank == EVENT_RANK["auth"]:
                index.add_auth(event, key)  # type: ignore[arg-type]
            elif rank == EVENT_RANK["payment"]:
                index.add_payment(event, key)  # type: ignore[arg-type]
            else:
                index.add_request(event, key)  # type: ignore[arg-type]
                request_keys[event.request_id] = key  # type: ignore[attr-defined]
        index.max_seq = len(merged)
        return index, request_keys

    # -- queries (all strictly before `key`) ------------------------------
    @staticmethod
    def window(keys: list[int], start_key: int, end_key: int) -> tuple[int, int]:
        return bisect_left(keys, start_key), bisect_left(keys, end_key)

    def first_pair_key(self, sender: str, recipient: str) -> int | None:
        return self.pair_first.get((sender, recipient))

    def first_device_key(self, account: str, device: str) -> int | None:
        return self.device_first.get((account, device))
