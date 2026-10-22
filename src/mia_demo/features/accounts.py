"""Trailing 24-hour account behavior for independent DBSCAN batches."""

from datetime import datetime, timedelta

from mia_demo.schemas import AccountSnapshot
from mia_demo.storage import MemoryHistory


def build_account_snapshot(account_id: str, as_of: datetime, history: MemoryHistory) -> AccountSnapshot:
    prior = [e for e in history.prior_events(account_id, as_of) if e.observed_at >= as_of - timedelta(hours=24)]
    incoming = [e for e in prior if e.receiver_psp == "LOCAL" and e.receiver_account_id == account_id and e.event_type in {"completed", "incoming"}]
    outgoing = [e for e in prior if e.sender_psp == "LOCAL" and e.sender_account_id == account_id and e.event_type == "completed"]
    incoming_bani = sum(e.amount_bani for e in incoming)
    outgoing_bani = sum(e.amount_bani for e in outgoing)
    rapid = sum(any(inc.observed_at < out.observed_at and inc.observed_at >= out.observed_at - timedelta(minutes=10) for inc in incoming) for out in outgoing)
    return AccountSnapshot(
        account_id=account_id,
        window_end=as_of,
        incoming_amount_24h=incoming_bani / 100,
        outgoing_amount_24h=outgoing_bani / 100,
        unique_senders_24h=len({(e.sender_psp, e.sender_account_id) for e in incoming}),
        unique_recipients_24h=len({(e.receiver_psp, e.receiver_account_id) for e in outgoing}),
        outgoing_to_incoming=min(20, outgoing_bani / max(incoming_bani, 100)),
        no_incoming=int(incoming_bani == 0),
        rapid_outflow_share=rapid / len(outgoing) if outgoing else 0.0,
        local_cycle_24h=int(account_id in history.local_cycle_accounts(as_of)),
    )
