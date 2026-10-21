from datetime import datetime, timedelta, timezone

import pytest

from mia_demo.features.transactions import build_transaction_features
from mia_demo.risk.engine import decide
from mia_demo.schemas import PaymentRequest
from mia_demo.storage import MemoryHistory


UTC = timezone.utc


def test_history_excludes_current_and_future_events():
    now = datetime(2026, 1, 12, 12, tzinfo=UTC)
    history = MemoryHistory({"A": {"opened_at": now - timedelta(days=60), "balance_bani": 100000}})
    history.add_payment("old", "A", "B", 30000, now - timedelta(minutes=30), "completed")
    history.add_payment("future", "A", "C", 90000, now + timedelta(minutes=1), "completed")
    history.add_payment("current", "A", "D", 50000, now, "attempt")
    candidate = PaymentRequest(transaction_id="current", sender_account_id="A", receiver_account_id="D", receiver_psp="LOCAL", amount_bani=50000, session_id="S", device_id="device-1")
    row = build_transaction_features(candidate, now, history, peer_median_bani=10000)
    assert row.outgoing_amount_1h == 300
    assert row.outgoing_attempts_5m == 0
    assert row.recipient_is_new == 1


def test_score_policy_boundaries():
    assert decide(59.999) == "Permit"
    assert decide(60) == "Verify"
    assert decide(84.999) == "Verify"
    assert decide(85) == "Block"


def test_request_rejects_non_mdl_and_nonpositive_amounts():
    base = dict(transaction_id="T", sender_account_id="A", receiver_account_id="B", receiver_psp="LOCAL", session_id="S", device_id="D")
    with pytest.raises(ValueError):
        PaymentRequest(**base, amount_bani=0)
    with pytest.raises(ValueError):
        PaymentRequest(**base, amount_bani=100, currency="EUR")


def test_current_session_does_not_make_new_device_old():
    now = datetime(2026, 1, 12, 12, tzinfo=UTC)
    history = MemoryHistory({"A": {"opened_at": now - timedelta(days=60), "balance_bani": 100000}})
    history.add_session("CURRENT", "A", "NEW", now - timedelta(minutes=1))
    candidate = PaymentRequest(transaction_id="T", sender_account_id="A", receiver_account_id="X", receiver_psp="PSP-1", amount_bani=10000, session_id="CURRENT", device_id="NEW")
    assert build_transaction_features(candidate, now, history).device_is_new == 1
    history.add_session("OLD", "A", "NEW", now - timedelta(days=1))
    assert build_transaction_features(candidate, now, history).device_is_new == 0
