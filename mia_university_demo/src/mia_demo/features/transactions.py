"""Candidate-only features from information observed before scoring time."""

from datetime import datetime, timedelta
from math import log1p
from statistics import median

from mia_demo.schemas import FeatureRow, PaymentRequest
from mia_demo.storage import MemoryHistory


def build_transaction_features(candidate: PaymentRequest, as_of: datetime, history: MemoryHistory, peer_median_bani: int = 10000) -> FeatureRow:
    account_id = candidate.sender_account_id
    if account_id not in history.accounts:
        raise ValueError("Unknown local sender")
    prior = history.prior_events(account_id, as_of)
    outgoing = [e for e in prior if e.sender_psp == "LOCAL" and e.sender_account_id == account_id]
    attempts = [e for e in outgoing if e.event_type == "attempt"]
    completed = [e for e in outgoing if e.event_type == "completed"]
    incoming = [e for e in prior if e.receiver_psp == "LOCAL" and e.receiver_account_id == account_id and e.event_type in {"completed", "incoming"}]
    recent_30d = [e.amount_bani for e in completed if e.observed_at >= as_of - timedelta(days=30)]
    amount_baseline = median(recent_30d) if len(recent_30d) >= 3 else peer_median_bani
    attempts_5m = [e for e in attempts if e.observed_at >= as_of - timedelta(minutes=5)]
    attempts_1h = [e for e in attempts if e.observed_at >= as_of - timedelta(hours=1)]
    outgoing_1h = [e for e in completed if e.observed_at >= as_of - timedelta(hours=1)]
    outgoing_24h = [e for e in completed if e.observed_at >= as_of - timedelta(hours=24)]
    incoming_1h = [e for e in incoming if e.observed_at >= as_of - timedelta(hours=1)]
    incoming_bani = sum(e.amount_bani for e in incoming_1h)
    last_attempt = max((e.observed_at for e in attempts), default=None)
    age_days = max(0, (as_of - history.account_opened_at(account_id)).total_seconds() / 86400)
    return FeatureRow(
        log_amount=log1p(candidate.amount_bani / 100),
        amount_to_sender_median_30d=min(100, candidate.amount_bani / max(amount_baseline, 100)),
        outgoing_attempts_5m=len(attempts_5m),
        outgoing_attempts_1h=len(attempts_1h),
        outgoing_amount_1h=sum(e.amount_bani for e in outgoing_1h) / 100,
        unique_recipients_24h=len({(e.receiver_psp, e.receiver_account_id) for e in outgoing_24h}),
        recipient_is_new=int(not any(e.receiver_account_id == candidate.receiver_account_id and e.receiver_psp == candidate.receiver_psp for e in completed)),
        device_is_new=int(not history.device_seen(account_id, candidate.device_id, as_of, candidate.session_id)),
        account_age_days=age_days,
        seconds_since_last_attempt=min(86400 * 30, (as_of - last_attempt).total_seconds()) if last_attempt else 0,
        last_attempt_missing=int(last_attempt is None),
        incoming_amount_1h=incoming_bani / 100,
        unique_senders_1h=len({(e.sender_psp, e.sender_account_id) for e in incoming_1h}),
        amount_to_recent_inflow=min(100, candidate.amount_bani / max(incoming_bani, 100)),
        no_recent_inflow=int(incoming_bani == 0),
        recent_password_reset=int(history.reset_seen(account_id, as_of)),
        history_count_30d=len(recent_30d),
    )
