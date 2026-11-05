"""Typed public API contracts. Mirrored by `frontend/src/api/types.ts`."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Decision = Literal["Permit", "Verify", "Block"]
DecisionSource = Literal["confirmed_fraud_evidence", "risk_policy", "assessment_safeguard"]
DecisionLabel = Literal["Confirmed fraud evidence", "Preventive risk block", "Needs verification", "Permitted"]
Outcome = Literal["permitted", "pending_verification", "blocked_attempt", "approved_after_review", "rejected_after_review"]
AuthMethod = Literal["biometric", "password", "otp", "password_otp"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class SimulationRequest(StrictModel):
    """A simulated payment request. Unknown fields (for example `is_fraud`) are rejected."""

    request_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{5,63}$")
    sender_id: str = Field(min_length=3, max_length=40)
    recipient_id: str | None = Field(default=None, min_length=3, max_length=40)
    new_recipient_name: str | None = Field(default=None, min_length=2, max_length=80)
    amount: float = Field(gt=0, le=1_000_000)
    currency: Literal["EUR"] = "EUR"
    device_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{3,40}$")
    auth_method: AuthMethod = "biometric"
    failed_login_attempts: int = Field(default=0, ge=0, le=10)
    ip_country: str = Field(default="DE", pattern=r"^[A-Z]{2}$")
    channel: Literal["mobile_app", "web"] = "mobile_app"

    @field_validator("amount")
    @classmethod
    def amount_is_finite_cents(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("amount must be finite")
        return round(value, 2)

    @field_validator("new_recipient_name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value

    @model_validator(mode="after")
    def exactly_one_recipient(self) -> SimulationRequest:
        if bool(self.recipient_id) == bool(self.new_recipient_name):
            raise ValueError("Provide either recipient_id or new_recipient_name, not both")
        return self


class ReviewRequest(StrictModel):
    action: Literal["approve", "reject"]
    reason: str = Field(min_length=8, max_length=500)
    actor: str = Field(default="Local analyst", min_length=2, max_length=60)

    @field_validator("reason", "actor")
    @classmethod
    def strip(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("must not be blank")
        return cleaned


class StreamModeRequest(StrictModel):
    mode: Literal["continuous", "batch_5", "batch_10", "batch_20"]


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class PartyRef(BaseModel):
    id: str
    name: str
    kind: Literal["account", "counterparty"]


class ComponentView(BaseModel):
    key: Literal["isolation_forest", "lof", "dbscan", "rules"]
    label: str
    score: float | None
    weight: float
    contribution: float | None
    raw: float | None
    status: str | None
    detail: str


class ReasonView(BaseModel):
    code: str
    family: str
    description: str
    detail: str
    weight: float
    corroborating: bool


class EvidenceView(BaseModel):
    evidence_id: str
    evidence_type: str
    entity_type: str
    entity_id: str
    source: str
    recorded_at: str
    effective_from: str
    effective_until: str | None
    note: str


class ComponentBrief(BaseModel):
    isolation_forest: float | None
    lof: float | None
    dbscan: float | None
    rules: float | None


class AssessmentSummary(BaseModel):
    cursor: int
    request_id: str
    origin: Literal["baseline", "simulation"]
    producer: str | None
    event_time: str
    sender: PartyRef
    recipient: PartyRef
    amount: float
    currency: str
    risk_score: float | None
    decision: Decision
    decision_source: DecisionSource
    decision_label: DecisionLabel
    assessment_status: str
    outcome: Outcome
    review_status: Literal["not_applicable", "pending", "approved", "rejected"]
    components: ComponentBrief
    evidence_ids: list[str]
    corroborating_signals: list[str]


class Thresholds(BaseModel):
    verify: float
    block: float
    min_corroborating_families: int
    source: str


class AssessmentDetail(AssessmentSummary):
    explanation: str
    status_notes: list[str]
    component_details: list[ComponentView]
    reasons: list[ReasonView]
    evidence: list[EvidenceView]
    thresholds: Thresholds
    model_version: str | None
    policy_version: str
    operating_point_version: str
    assessed_at: str
    device_id: str
    session_id: str
    auth_method: str
    ip_country: str
    channel: str
    facts: dict[str, Any]
    idempotent_replay: bool = False


class TimelineEntry(BaseModel):
    at: str
    kind: str
    title: str
    detail: str | None = None


class ReviewView(BaseModel):
    review_id: str
    action: Literal["approve", "reject"]
    reason: str
    actor: str
    created_at: str
    original_decision: Decision
    original_risk_score: float | None
    resulting_outcome: Outcome


class Investigation(BaseModel):
    assessment: AssessmentDetail
    timeline: list[TimelineEntry]
    reviews: list[ReviewView]
    can_review: bool


class Page(BaseModel):
    total: int
    page: int
    page_size: int


class TransactionPage(Page):
    items: list[AssessmentSummary]


class AccountSummary(BaseModel):
    account_id: str
    display_name: str
    account_type: str
    home_country: str
    created_at: str
    requests: int
    flagged: int
    last_activity: str | None
    last_decision: Decision | None


class AccountPage(Page):
    items: list[AccountSummary]


class StreamStatus(BaseModel):
    running: bool
    mode: str
    interval_seconds: float
    produced: int
    failures: int
    last_error: str | None
    started_at: str | None
    last_tick_at: str | None
    owner: str


class LiveFeed(BaseModel):
    items: list[AssessmentSummary]
    next_cursor: int
    stream: StreamStatus
    simulation_time: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None
