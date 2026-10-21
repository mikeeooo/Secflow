"""Chronological offline export using the exact live feature function."""

from datetime import datetime
from statistics import median

from mia_demo.schemas import PaymentRequest
from mia_demo.storage import MemoryHistory
from .transactions import build_transaction_features


def training_peer_median(dataset) -> int:
    amounts = [e.amount_bani for e in dataset.events if e.event_type == "completed" and e.sender_psp == "LOCAL" and 11 <= (e.observed_at.date() - datetime.fromisoformat(dataset.config["start"]).date()).days + 1 <= 60]
    return int(median(amounts)) if amounts else 10000


def export_feature_rows(dataset, peer_median_bani: int | None = None) -> list[dict]:
    peer_median_bani = peer_median_bani or training_peer_median(dataset)
    accounts = {account_id: dict(opened_at=datetime.fromisoformat(data["opened_at"]), balance_bani=data["initial_balance_bani"]) for account_id, data in dataset.accounts.items()}
    history = MemoryHistory(accounts)
    for session in dataset.sessions:
        history.add_session(session["session_id"], session["local_account_id"], session["device_id"], datetime.fromisoformat(session["observed_at"]), session["authentication_result"])
    for event in dataset.account_events:
        history.add_account_event(event["local_account_id"], event["event_type"], datetime.fromisoformat(event["observed_at"]))
    rows = []
    event_index = 0
    for request in dataset.requests:
        as_of = datetime.fromisoformat(request["occurred_at"])
        while event_index < len(dataset.events) and dataset.events[event_index].observed_at < as_of:
            history.add_event(dataset.events[event_index])
            event_index += 1
        candidate = PaymentRequest.model_validate({key: value for key, value in request.items() if key in PaymentRequest.model_fields})
        features = build_transaction_features(candidate, as_of, history, peer_median_bani)
        rows.append(dict(transaction_id=request["transaction_id"], occurred_at=request["occurred_at"], split=request["split"], sender_account_id=request["sender_account_id"], features=features.model_dump()))
    return rows
