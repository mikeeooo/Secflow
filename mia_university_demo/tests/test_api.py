from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from mia_demo.api import create_app
from mia_demo.features.replay import export_feature_rows
from mia_demo.ml.bundle import save_bundle
from mia_demo.ml.train import train_models
from mia_demo.simulation.generator import generate
from mia_demo.storage import Account, Event, Repository, ReviewAction


def _client(tmp_path, with_model=True, verify_threshold=101, block_threshold=102):
    database = tmp_path / "api.sqlite3"
    repo = Repository(database)
    opened = datetime.now(timezone.utc) - timedelta(days=100)
    repo.insert_accounts({"A": {"opened_at": opened, "balance_bani": 100000}, "B": {"opened_at": opened, "balance_bani": 100000}})
    model_path = tmp_path / "model.joblib"
    if with_model:
        rows = export_feature_rows(generate(seed=9, accounts=25, attempts=500))
        save_bundle(train_models([r for r in rows if r["split"] == "train"], [r for r in rows if r["split"] == "calibration"]), model_path)
    return TestClient(create_app(database, model_path, verify_threshold=verify_threshold, block_threshold=block_threshold)), repo


def _request(client, transaction_id="DUP-1"):
    session = client.post("/sessions", json={"local_account_id": "A", "device_id": "demo-device"}).json()
    return dict(transaction_id=transaction_id, sender_account_id="A", receiver_account_id="B", receiver_psp="LOCAL", amount_bani=10000, currency="MDL", session_id=session["session_id"], device_id="demo-device", initiation_method="APP")


def test_duplicate_request_has_one_assessment_and_one_mock_transfer(tmp_path):
    client, repo = _client(tmp_path)
    request = _request(client)
    first = client.post("/assessments", json=request)
    second = client.post("/assessments", json=request)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["result"]["decision"] == "Permit"
    with repo.Session() as db:
        assert db.query(Event).filter_by(transaction_id="DUP-1", event_type="completed").count() == 1
        assert db.get(Account, "A").balance_bani == 90000
        assert db.get(Account, "B").balance_bani == 110000


def test_missing_model_stays_pending_and_invalid_request_is_rejected(tmp_path):
    client, repo = _client(tmp_path, with_model=False)
    request = _request(client, "MISSING-1")
    assert client.post("/assessments", json={**request, "amount_bani": 0}).status_code == 422
    result = client.post("/assessments", json=request)
    assert result.status_code == 200
    assert result.json()["result"]["decision"] == "Pending"
    assert result.json()["mock_submitted"] is False
    with repo.Session() as db:
        assert db.query(Event).filter_by(transaction_id="MISSING-1", event_type="completed").count() == 0


def test_verification_requires_explicit_approval(tmp_path):
    client, repo = _client(tmp_path, verify_threshold=0, block_threshold=101)
    request = _request(client, "VERIFY-1")
    result = client.post("/assessments", json=request)
    assert result.json()["result"]["decision"] == "Verify"
    assert result.json()["mock_submitted"] is False
    assert client.post("/assessments/VERIFY-1/approve").status_code == 200
    assert client.post("/assessments/VERIFY-1/approve").status_code == 200
    with repo.Session() as db:
        assert db.query(Event).filter_by(transaction_id="VERIFY-1", event_type="completed").count() == 1
        assert db.query(ReviewAction).filter_by(transaction_id="VERIFY-1", action="approved").count() == 1


def test_demo_context_is_observed_as_prior_attempts(tmp_path):
    client, _ = _client(tmp_path)
    request = _request(client, "CONTEXT-1")
    created = client.post("/demo/context", json={"local_account_id": "A", "attempt_count": 5})
    assert created.status_code == 200
    result = client.post("/assessments", json=request)
    assert result.json()["feature_snapshot"]["outgoing_attempts_5m"] >= 5


def test_review_reject_is_audited_and_never_submits(tmp_path):
    client, repo = _client(tmp_path, verify_threshold=0, block_threshold=101)
    request = _request(client, "REJECT-1")
    original = client.post("/assessments", json=request).json()
    first = client.post("/assessments/REJECT-1/reviews", json={"action": "reject", "note": "Verificare manuală"})
    second = client.post("/assessments/REJECT-1/reviews", json={"action": "reject", "note": "Verificare manuală"})
    assert first.status_code == second.status_code == 200
    assert first.json()["result"] == original["result"]
    assert first.json()["review_status"] == "rejected"
    assert client.post("/assessments/REJECT-1/reviews", json={"action": "approve"}).status_code == 409
    with repo.Session() as db:
        assert db.query(ReviewAction).filter_by(transaction_id="REJECT-1").count() == 1
        assert db.query(Event).filter_by(transaction_id="REJECT-1", event_type="completed").count() == 0


def test_paginated_filters_and_overview_use_full_selected_set(tmp_path):
    client, _ = _client(tmp_path)
    for index in range(3):
        request = _request(client, f"PAGE-{index}")
        assert client.post("/assessments", json=request).status_code == 200
    page = client.get("/transactions", params={"page": 1, "page_size": 1, "search": "PAGE-", "decision": "Permit"}).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    assert page["items"][0]["payment_status"] == "completed"
    assert page["items"][0]["review_status"] == "none"
    assert client.get("/transactions", params={"search": "absent"}).json()["total"] == 0
    overview = client.get("/overview").json()
    assert overview["assessments"] == 3 and overview["decision_counts"]["Permit"] == 3
    details = client.get("/transactions/PAGE-0").json()
    assert details["assessment"]["transaction_id"] == "PAGE-0"
    assert isinstance(details["timeline"], list)


def test_account_profile_and_activity_are_local_and_paginated(tmp_path):
    client, _ = _client(tmp_path)
    request = _request(client, "ACCOUNT-1")
    client.post("/assessments", json=request)
    accounts = client.get("/accounts", params={"search": "A", "page_size": 1}).json()
    assert accounts["total"] >= 1 and len(accounts["items"]) == 1
    profile = client.get("/accounts/A").json()
    assert profile["account_id"] == "A" and profile["outgoing_bani"] >= 10000
    activity = client.get("/accounts/A/activity", params={"page_size": 1}).json()
    assert activity["total"] >= 1 and len(activity["items"]) == 1
    assert client.get("/accounts/EXTERNAL").status_code == 404
