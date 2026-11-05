"""Leakage-safe chronological features shared by offline training/evaluation and live scoring.

`build_features(request, key, history, account)` only reads events whose ordering key is
strictly lower than `key`. The request being assessed is never part of its own historical
aggregates. The DBSCAN account-context profile is *prospective*: it summarises the sender's
trailing 24 hours of history plus the request under assessment, as a separate block.

Identifiers, names, labels, scenarios and generator parameters are never numeric inputs.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from storage.history import HistoryIndex
from storage.records import KEY_SCALE, Account, PaymentRequest

FEATURE_VERSION = "features-1.0.0"
HOUR = 3_600
DAY = 86_400
WINDOW_30D = 30 * DAY
MAX_GAP_HOURS = 720.0
SUFFICIENT_HISTORY = 5
CONTEXT_MIN_HISTORY = 3

PAYMENT_FEATURES: tuple[str, ...] = (
    "log_amount",
    "amount_zscore_30d",
    "log_amount_to_prior_max_30d",
    "requests_1h",
    "requests_24h",
    "log_sum_24h",
    "velocity_ratio_24h",
    "unique_recipients_24h",
    "new_recipient",
    "recipient_senders_24h",
    "log_recipient_history_days",
    "log_device_age_hours",
    "auth_failures_24h",
    "log_hours_since_last_request",
    "log_account_age_days",
    "log_incoming_24h",
    "foreign_ip",
    "weak_auth",
    "hour_deviation",
    "log_requests_30d",
)

CONTEXT_FEATURES: tuple[str, ...] = (
    "ctx_log_requests_24h",
    "ctx_log_sum_24h",
    "ctx_unique_recipients_24h",
    "ctx_new_recipients_24h",
    "ctx_devices_24h",
    "ctx_auth_failures_24h",
    "ctx_log_incoming_24h",
    "ctx_log_amount_ratio_24h",
)

AUTH_WEAKNESS = {"biometric": 0.0, "password_otp": 0.0, "otp": 0.5, "password": 1.0}


@dataclass(frozen=True)
class FeatureSnapshot:
    payment_vector: tuple[float, ...]
    context_vector: tuple[float, ...]
    history_status: str  # none | limited | sufficient
    context_status: str  # ok | insufficient_history
    facts: Mapping[str, Any]


def _key_at(ts: float) -> int:
    return int(ts) * KEY_SCALE


def _circular_hour_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 24
    return min(diff, 24 - diff)


def build_features(
    request: PaymentRequest, key: int, history: HistoryIndex, account: Account | None
) -> FeatureSnapshot:
    """Compute the feature snapshot for `request` using only history strictly before `key`."""
    t = request.ts
    amount = request.amount
    log_amount = math.log1p(amount)
    sender = history.sender.get(request.sender_id)

    prior_total = 0
    n30 = n24 = n1 = 0
    mean30 = std30 = 0.0
    max30 = 0.0
    sum24 = 0.0
    recipients24: list[str] = []
    gap_hours: float | None = None
    hour_mean: float | None = None
    median30: float | None = None
    if sender is not None:
        hi = HistoryIndex.window(sender.keys, key, key)[1]
        prior_total = hi
        lo30 = HistoryIndex.window(sender.keys, _key_at(t - WINDOW_30D), key)[0]
        lo24 = HistoryIndex.window(sender.keys, _key_at(t - DAY), key)[0]
        lo1 = HistoryIndex.window(sender.keys, _key_at(t - HOUR), key)[0]
        n30, n24, n1 = hi - lo30, hi - lo24, hi - lo1
        if n30 > 0:
            s = sender.cum_log[hi] - sender.cum_log[lo30]
            s2 = sender.cum_log2[hi] - sender.cum_log2[lo30]
            mean30 = s / n30
            std30 = math.sqrt(max(0.0, s2 / n30 - mean30 * mean30))
            window_amounts = sender.amounts[lo30:hi]
            max30 = max(window_amounts)
            median30 = sorted(window_amounts)[len(window_amounts) // 2]
            sin_sum = sender.cum_sin[hi] - sender.cum_sin[lo30]
            cos_sum = sender.cum_cos[hi] - sender.cum_cos[lo30]
            hour_mean = (math.atan2(sin_sum, cos_sum) / (2 * math.pi) * 24) % 24
        sum24 = sender.cum_amount[hi] - sender.cum_amount[lo24]
        recipients24 = sender.recipients[lo24:hi]
        if hi > 0:
            gap_hours = (t - sender.keys[hi - 1] // KEY_SCALE) / HOUR

    account_age_days = max(0.0, (t - account.created_at) / DAY) if account else 0.0
    observed_days = min(30.0, max(1.0, account_age_days))
    usual_daily = n30 / observed_days
    velocity_ratio = (n24 + 1) / (usual_daily + 1)
    history_status = "none" if prior_total == 0 else ("limited" if prior_total < SUFFICIENT_HISTORY else "sufficient")
    zscore = (log_amount - mean30) / (std30 + 0.25) if n30 >= 3 else 0.0
    ratio_to_max = math.log(amount / max30) if max30 > 0 else 0.0

    # A beneficiary counts as new until the sender's first payment to it is at least 24 hours old,
    # so repeated payments inside one burst do not make an unknown beneficiary look established.
    pair_first = history.first_pair_key(request.sender_id, request.recipient_id)
    paid_before = pair_first is not None and pair_first < key
    relationship_hours = (t - pair_first // KEY_SCALE) / HOUR if paid_before else None
    new_recipient = relationship_hours is None or relationship_hours < 24

    rec = history.recipient.get(request.recipient_id)
    recipient_senders = 0
    recipient_days = 0.0
    if rec is not None:
        lo, hi = HistoryIndex.window(rec.keys, _key_at(t - DAY), key)
        recipient_senders = len({s for s in rec.senders[lo:hi] if s != request.sender_id})
        if rec.keys and rec.keys[0] < key:
            recipient_days = (t - rec.keys[0] // KEY_SCALE) / DAY

    device_first = history.first_device_key(request.sender_id, request.device_id)
    device_age_hours = (t - device_first // KEY_SCALE) / HOUR if device_first is not None and device_first < key else None

    auth = history.auth.get(request.sender_id)
    failures24 = 0
    devices24: set[str] = {request.device_id}
    established_before_window = False
    if auth is not None:
        lo, hi = HistoryIndex.window(auth.keys, _key_at(t - DAY), key)
        failures24 = auth.cum_failures[hi] - auth.cum_failures[lo]
        devices24.update(auth.devices[lo:hi])
        established_before_window = lo > 0  # the account signed in before the last 24 hours
    new_device = device_age_hours is None or device_age_hours < 24
    # A device change needs an earlier sign-in history; a brand-new account's first device is not a change.
    device_change = new_device and established_before_window

    incoming = history.incoming.get(request.sender_id)
    incoming24 = 0.0
    if incoming is not None:
        lo, hi = HistoryIndex.window(incoming.keys, _key_at(t - DAY), key)
        incoming24 = incoming.cum_amount[hi] - incoming.cum_amount[lo]

    home = account.home_country if account else request.ip_country
    hour_now = (t % DAY) / HOUR
    hour_dev = _circular_hour_distance(hour_now, hour_mean) if hour_mean is not None and n30 >= 3 else 0.0
    gap = min(gap_hours, MAX_GAP_HOURS) if gap_hours is not None else MAX_GAP_HOURS
    device_age = min(device_age_hours, MAX_GAP_HOURS) if device_age_hours is not None else 0.0
    unique24 = len(set(recipients24))

    payment_vector = (
        log_amount,
        max(-6.0, min(zscore, 12.0)),
        max(-4.0, min(ratio_to_max, 4.0)),
        float(n1),
        float(n24),
        math.log1p(sum24),
        velocity_ratio,
        float(unique24),
        1.0 if new_recipient else 0.0,
        float(recipient_senders),
        math.log1p(recipient_days),
        math.log1p(device_age),
        float(failures24),
        math.log1p(gap),
        math.log1p(account_age_days),
        math.log1p(incoming24),
        1.0 if request.ip_country != home else 0.0,
        AUTH_WEAKNESS.get(request.auth_method, 1.0),
        hour_dev,
        math.log1p(n30),
    )

    new_in_window = sum(
        1
        for r in set(recipients24)
        if (history.first_pair_key(request.sender_id, r) or 0) >= _key_at(t - DAY)
    ) + (1 if new_recipient and request.recipient_id not in recipients24 else 0)
    daily_avg = 0.0
    if sender is not None and n30:
        daily_avg = (sender.cum_amount[prior_total] - sender.cum_amount[prior_total - n30]) / 30
    context_vector = (
        math.log1p(n24 + 1),
        math.log1p(sum24 + amount),
        float(len(set(recipients24) | {request.recipient_id})),
        float(new_in_window),
        float(len(devices24)),
        float(failures24),
        math.log1p(incoming24),
        math.log1p((sum24 + amount) / max(daily_avg, 1.0)),
    )
    context_status = "ok" if prior_total >= CONTEXT_MIN_HISTORY else "insufficient_history"

    facts: dict[str, Any] = {
        "amount": amount,
        "auth_method": request.auth_method,
        "ip_country": request.ip_country,
        "home_country": home,
        "prior_requests_total": prior_total,
        "prior_requests_30d": n30,
        "median_amount_30d": median30,
        "max_amount_30d": max30 if n30 else None,
        "amount_zscore_30d": round(zscore, 3) if n30 >= 3 else None,
        "requests_1h": n1,
        "requests_24h": n24,
        "sum_24h": round(sum24, 2),
        "velocity_ratio_24h": round(velocity_ratio, 3),
        "unique_recipients_24h": unique24,
        "new_recipient": new_recipient,
        "recipient_relationship_hours": round(relationship_hours, 2) if relationship_hours is not None else None,
        "recipient_senders_24h": recipient_senders,
        "recipient_history_days": round(recipient_days, 2) if rec is not None and recipient_days > 0 else None,
        "device_age_hours": round(device_age_hours, 2) if device_age_hours is not None else None,
        "new_device": new_device,
        "device_change": device_change,
        "auth_failures_24h": failures24,
        "hours_since_last_request": round(gap_hours, 2) if gap_hours is not None else None,
        "account_age_days": round(account_age_days, 1),
        "incoming_24h": round(incoming24, 2),
        "foreign_ip": request.ip_country != home,
        "hour_deviation": round(hour_dev, 2),
        "context_devices_24h": len(devices24),
        "context_new_recipients_24h": new_in_window,
    }
    return FeatureSnapshot(payment_vector, context_vector, history_status, context_status, facts)
