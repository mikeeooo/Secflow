from datetime import datetime, timezone

from mia_demo.ml.cluster import fit_cluster_reference, run_clustering
from mia_demo.features.accounts import build_account_snapshot
from mia_demo.schemas import AccountSnapshot
from mia_demo.storage import MemoryHistory
from datetime import timedelta


def _snapshot(account, incoming, outgoing, senders=1):
    return AccountSnapshot(account_id=account, window_end=datetime(2026, 4, 1, tzinfo=timezone.utc), incoming_amount_24h=incoming, outgoing_amount_24h=outgoing, unique_senders_24h=senders, unique_recipients_24h=1, outgoing_to_incoming=outgoing / max(incoming, 1), no_incoming=int(incoming == 0), rapid_outflow_share=0.5)


def test_singleton_and_constant_columns_are_safe():
    rows = [_snapshot("A", 100, 80)]
    reference = fit_cluster_reference(rows * 12, rows * 12, min_samples=10)
    findings = run_clustering(rows, reference)
    assert len(findings) == 1
    assert findings[0]["cluster_label"] == -1
    assert findings[0]["noise_flag"] is True


def test_batch_findings_have_later_availability_and_context_not_fraud_truth():
    rows = [_snapshot(f"A{i}", 100 + i, 85 + i, senders=5 if i == 0 else 1) for i in range(15)]
    reference = fit_cluster_reference(rows, rows, min_samples=3)
    findings = run_clustering(rows, reference)
    assert len(findings) == 15
    assert all(f["available_at"] > f["window_end"] for f in findings)
    assert all("is_fraud" not in f for f in findings)
    assert "MANY_SENDERS" in findings[0]["contextual_rule_flags"]


def test_local_transfer_cycle_is_a_contextual_graph_signal():
    now = datetime(2026, 4, 1, tzinfo=timezone.utc)
    history = MemoryHistory({key: {"opened_at": now - timedelta(days=90), "balance_bani": 100000} for key in "ABCD"})
    for index, (sender, receiver) in enumerate((('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'))):
        history.add_payment(f"t{index}", sender, receiver, 10000, now - timedelta(minutes=10 - index), "completed")
    rows = [build_account_snapshot(key, now, history) for key in "ABCD"]
    assert all(row.local_cycle_24h == 1 for row in rows)
    reference = fit_cluster_reference(rows * 3, rows * 3, min_samples=3)
    findings = run_clustering(rows, reference)
    assert all("LOCAL_CYCLE" in row["contextual_rule_flags"] for row in findings)


def test_cycle_scan_handles_recipient_without_outgoing_edges():
    now = datetime(2026, 4, 1, tzinfo=timezone.utc)
    history = MemoryHistory({key: {"opened_at": now - timedelta(days=90), "balance_bani": 100000} for key in "AB"})
    history.add_payment("one-way", "A", "B", 10000, now - timedelta(minutes=1), "completed")
    assert build_account_snapshot("A", now, history).local_cycle_24h == 0
