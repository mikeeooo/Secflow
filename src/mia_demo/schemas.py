"""Contracts shared by the generator, feature engine, API and UI."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return value.astimezone(timezone.utc)


class PaymentRequest(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=80)
    sender_account_id: str = Field(min_length=1)
    receiver_account_id: str = Field(min_length=1)
    receiver_psp: str = Field(min_length=1)
    amount_bani: int = Field(gt=0)
    currency: Literal["MDL"] = "MDL"
    session_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    initiation_method: Literal["APP", "ALIAS"] = "APP"


class PaymentEvent(BaseModel):
    event_id: str
    transaction_id: str
    occurred_at: datetime
    observed_at: datetime
    event_type: Literal["attempt", "completed", "incoming"]
    sender_account_id: str
    receiver_account_id: str
    sender_psp: str
    receiver_psp: str
    amount_bani: int = Field(gt=0)
    currency: Literal["MDL"] = "MDL"
    session_id: str = ""
    initiation_method: Literal["APP", "ALIAS"] = "APP"

    _occurred_utc = field_validator("occurred_at")(utc)
    _observed_utc = field_validator("observed_at")(utc)


class FeatureRow(BaseModel):
    log_amount: float
    amount_to_sender_median_30d: float
    outgoing_attempts_5m: int
    outgoing_attempts_1h: int
    outgoing_amount_1h: float
    unique_recipients_24h: int
    recipient_is_new: int
    device_is_new: int
    account_age_days: float
    seconds_since_last_attempt: float
    last_attempt_missing: int
    incoming_amount_1h: float
    unique_senders_1h: int
    amount_to_recent_inflow: float
    no_recent_inflow: int
    recent_password_reset: int
    history_count_30d: int


FEATURE_ORDER = tuple(FeatureRow.model_fields)


class RiskResult(BaseModel):
    score: float
    decision: Literal["Permit", "Verify", "Block", "Pending"]
    reasons: list[dict]
    if_percentile: float | None = None
    lof_percentile: float | None = None
    rule_score: float | None = None
    model_version: str | None = None
    policy_version: str = "policy-v1"


class AccountSnapshot(BaseModel):
    account_id: str
    window_end: datetime
    incoming_amount_24h: float
    outgoing_amount_24h: float
    unique_senders_24h: int
    unique_recipients_24h: int
    outgoing_to_incoming: float
    no_incoming: int
    rapid_outflow_share: float
    local_cycle_24h: int = 0
