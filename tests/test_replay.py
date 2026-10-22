from datetime import datetime, timedelta, timezone

from mia_demo.features.accounts import build_account_snapshot
from mia_demo.features.replay import export_feature_rows
from mia_demo.schemas import PaymentRequest
from mia_demo.simulation.generator import generate
from mia_demo.storage import MemoryHistory


def test_batch_feature_matches_live_for_same_history():
    dataset = generate(seed=4, accounts=20, attempts=200)
    rows = export_feature_rows(dataset)
    assert len(rows) == 200
    assert [row["transaction_id"] for row in rows] == [r["transaction_id"] for r in dataset.requests]
    assert set(rows[0]) >= {"features", "split", "transaction_id"}


def test_account_snapshot_uses_only_prior_local_observations():
    now = datetime(2026, 1, 5, 12, tzinfo=timezone.utc)
    history = MemoryHistory({"A": {"opened_at": now - timedelta(days=10), "balance_bani": 100000}})
    history.add_payment("in", "EXTERNAL", "A", 20000, now - timedelta(minutes=8), "incoming", sender_psp="PSP-1")
    history.add_payment("out", "A", "EXTERNAL", 16000, now - timedelta(minutes=3), "completed", receiver_psp="PSP-2")
    history.add_payment("future", "A", "OTHER", 99999, now + timedelta(minutes=1), "completed")
    snapshot = build_account_snapshot("A", now, history)
    assert snapshot.incoming_amount_24h == 200
    assert snapshot.outgoing_amount_24h == 160
    assert snapshot.rapid_outflow_share == 1
