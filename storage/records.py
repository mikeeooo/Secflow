"""Typed runtime records shared by the loader, feature pipeline, and service.

None of these records carries a ground-truth label, scenario, or campaign identifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

# Events that share a timestamp are ordered auth -> payment -> request, then by identifier.
EVENT_RANK = {"auth": 0, "payment": 1, "request": 2}
KEY_SCALE = 1_000_000  # ordering key = epoch_seconds * KEY_SCALE + global sequence number


def parse_ts(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp())


def format_ts(ts: float) -> str:
    return datetime.fromtimestamp(int(ts), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_key(ts: int, seq: int) -> int:
    if seq >= KEY_SCALE:
        raise ValueError("sequence number exceeds key capacity")
    return ts * KEY_SCALE + seq


def key_ts(key: int) -> int:
    return key // KEY_SCALE


@dataclass(frozen=True, slots=True)
class PaymentRequest:
    request_id: str
    ts: int
    sender_id: str
    recipient_id: str
    recipient_type: str
    amount: float
    currency: str
    channel: str
    device_id: str
    session_id: str
    auth_method: str
    ip_country: str


@dataclass(frozen=True, slots=True)
class AuthEvent:
    event_id: str
    ts: int
    account_id: str
    session_id: str
    device_id: str
    event_type: str  # login_success | login_failure | session_revoked
    auth_method: str
    ip_country: str
    reason: str | None


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    event_id: str
    ts: int
    event_type: str  # transfer_settled | incoming_credit
    from_id: str
    to_id: str
    amount: float
    currency: str
    request_id: str | None


@dataclass(frozen=True, slots=True)
class Account:
    account_id: str
    display_name: str
    account_type: str
    home_country: str
    created_at: int


@dataclass(frozen=True, slots=True)
class Counterparty:
    counterparty_id: str
    display_name: str
    kind: str
    category: str


def request_from_row(row: dict) -> PaymentRequest:
    return PaymentRequest(
        request_id=row["request_id"],
        ts=parse_ts(row["timestamp"]),
        sender_id=row["sender_id"],
        recipient_id=row["recipient_id"],
        recipient_type=row["recipient_type"],
        amount=float(row["amount"]),
        currency=row["currency"],
        channel=row["channel"],
        device_id=row["device_id"],
        session_id=row["session_id"],
        auth_method=row["auth_method"],
        ip_country=row["ip_country"],
    )


def auth_from_row(row: dict) -> AuthEvent:
    return AuthEvent(
        event_id=row["event_id"],
        ts=parse_ts(row["timestamp"]),
        account_id=row["account_id"],
        session_id=row["session_id"],
        device_id=row["device_id"],
        event_type=row["event_type"],
        auth_method=row["auth_method"],
        ip_country=row["ip_country"],
        reason=row.get("reason"),
    )


def payment_from_row(row: dict) -> PaymentEvent:
    return PaymentEvent(
        event_id=row["event_id"],
        ts=parse_ts(row["timestamp"]),
        event_type=row["event_type"],
        from_id=row["from_id"],
        to_id=row["to_id"],
        amount=float(row["amount"]),
        currency=row["currency"],
        request_id=row.get("request_id"),
    )
