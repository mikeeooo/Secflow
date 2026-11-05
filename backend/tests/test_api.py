from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from config.settings import load_settings


@pytest.fixture(scope="module")
def client() -> TestClient:
    settings = replace(load_settings(), autostart_stream=False, stream_interval_seconds=0.05,
                       batch_interval_seconds=0.05)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def payload(request_id: str, **overrides: Any) -> dict[str, Any]:
    base = {"request_id": request_id, "sender_id": "ACC-0001", "recipient_id": "CP-00001", "amount": 25.0}
    if "new_recipient_name" in overrides and "recipient_id" not in overrides:
        base.pop("recipient_id")
    return {**base, **overrides}


def known_device(client: TestClient, sender: str = "ACC-0001") -> str:
    return client.get("/api/simulator/options", params={"sender_id": sender}).json()["sender"]["known_devices"][0]


def test_health_reports_local_files_and_process_memory(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["data"]["source"] == "local_files" and body["data"]["requests"] == 10_000
    assert body["state"]["kind"] == "process_memory"
    assert body["state"]["persisted"] is False and body["state"]["shared_across_workers"] is False
    assert body["model"]["loaded"] and body["policy"]["operating_point"]["source"].startswith("validated")


def test_baseline_assessments_use_real_components_and_event_time_snapshots(client: TestClient) -> None:
    page = client.get("/api/transactions", params={"origin": "baseline", "sort": "time_asc", "page_size": 5}).json()
    assert page["total"] == 10_000
    first = client.get(f"/api/investigations/{page['items'][0]['request_id']}").json()["assessment"]
    assert first["facts"]["prior_requests_total"] == 0  # the very first request sees no history
    assert {c["key"] for c in first["component_details"]} == {"isolation_forest", "lof", "dbscan", "rules"}
    assert first["risk_score"] == pytest.approx(sum(c["contribution"] for c in first["component_details"]), abs=0.02)


def test_filters_pagination_and_named_search(client: TestClient) -> None:
    verify = client.get("/api/transactions", params={"decision": "Verify", "page_size": 10, "page": 2}).json()
    assert verify["page"] == 2 and len(verify["items"]) == 10
    assert all(i["decision"] == "Verify" for i in verify["items"])
    high = client.get("/api/transactions", params={"min_score": 80, "sort": "risk_desc"}).json()
    scores = [i["risk_score"] for i in high["items"]]
    assert scores == sorted(scores, reverse=True) and all(s >= 80 for s in scores)
    name = client.get("/api/accounts/ACC-0001").json()["account"]["display_name"]
    found = client.get("/api/accounts", params={"q": name.split()[0].lower()}).json()
    assert any(a["account_id"] == "ACC-0001" for a in found["items"])
    by_name = client.get("/api/transactions", params={"q": name}).json()
    assert by_name["total"] > 0
    assert client.get("/api/transactions", params={"decision": "Maybe"}).status_code == 422


def test_missing_identifiers_return_404(client: TestClient) -> None:
    assert client.get("/api/investigations/NOPE").status_code == 404
    assert client.get("/api/accounts/ACC-9999").status_code == 404
    response = client.post("/api/simulations", json=payload("missing-sender", sender_id="ACC-9999"))
    assert response.status_code == 404


@pytest.mark.parametrize(
    "bad",
    [
        {"amount": -5},
        {"amount": 0},
        {"is_fraud": True},
        {"confirmed_fraud": True},
        {"currency": "USD"},
        {"request_id": "x"},
        {"new_recipient_name": "Someone", "recipient_id": "CP-00001"},  # both recipient fields
    ],
)
def test_invalid_or_authoritative_client_fields_are_rejected(client: TestClient, bad: dict[str, Any]) -> None:
    response = client.post("/api/simulations", json={**payload("invalid-check"), **bad})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_idempotent_retry_and_conflict(client: TestClient) -> None:
    body = payload("idem-000001", device_id=known_device(client))
    first = client.post("/api/simulations", json=body)
    again = client.post("/api/simulations", json=body)
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json()["idempotent_replay"] is True
    assert again.json()["risk_score"] == first.json()["risk_score"]
    assert again.json()["cursor"] == first.json()["cursor"]
    assert client.post("/api/simulations", json={**body, "amount": 26.0}).status_code == 409
    baseline_id = client.get("/api/transactions", params={"origin": "baseline", "page_size": 1}).json()["items"][0]
    assert client.post("/api/simulations", json=payload(baseline_id["request_id"])).status_code == 409


def test_concurrent_duplicates_commit_exactly_once(client: TestClient) -> None:
    body = payload("concurrent-0001", amount=31.0)
    before = client.get("/api/health").json()["state"]["simulations"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = sorted(pool.map(lambda _: client.post("/api/simulations", json=body).status_code, range(8)))
    assert codes.count(201) == 1 and codes.count(200) == 7
    assert client.get("/api/health").json()["state"]["simulations"] == before + 1
    feed = client.get("/api/live-transfers", params={"after": 0, "limit": 200}).json()
    assert [i["request_id"] for i in feed["items"]].count("concurrent-0001") == 1


def test_confirmed_evidence_blocks_low_score_payment(client: TestClient) -> None:
    flagged = client.get("/api/simulator/options").json()["flagged_beneficiaries"]
    assert flagged, "the demo evidence stream should contain an active flagged beneficiary"
    response = client.post("/api/simulations", json=payload("evidence-0001", sender_id="ACC-0003",
                                                             recipient_id=flagged[0]["id"], amount=12.0,
                                                             device_id=known_device(client, "ACC-0003")))
    body = response.json()
    assert (body["decision"], body["decision_source"], body["decision_label"]) == (
        "Block", "confirmed_fraud_evidence", "Confirmed fraud evidence")
    assert body["evidence_ids"] and body["risk_score"] is not None
    assert body["outcome"] == "blocked_attempt"


def test_simulation_sees_earlier_simulations(client: TestClient) -> None:
    device = known_device(client, "ACC-0005")
    results = [
        client.post("/api/simulations", json=payload(f"burst-{i:06d}", sender_id="ACC-0005",
                                                     new_recipient_name="Burst Target", amount=50.0,
                                                     device_id=device)).json()
        for i in range(1)
    ]
    recipient = results[0]["recipient"]["id"]
    later = client.post("/api/simulations", json=payload("burst-000009", sender_id="ACC-0005", recipient_id=recipient,
                                                         amount=50.0, device_id=device)).json()
    assert later["facts"]["requests_1h"] >= 1
    assert later["facts"]["new_recipient"] is True  # first paid moments ago: still no established history


def review_target(client: TestClient, request_id: str, sender: str) -> str:
    """A large first payment to a new beneficiary from a known device: one corroborating family, so never a block."""
    body = client.post("/api/simulations", json=payload(request_id, sender_id=sender, new_recipient_name="Review Target",
                                                         amount=6_000, device_id=known_device(client, sender),
                                                         auth_method="biometric")).json()
    assert body["decision"] == "Verify", body["explanation"]
    assert len(body["corroborating_signals"]) < 2
    return request_id


def test_review_requires_reason_preserves_original_and_rejects_second_review(client: TestClient) -> None:
    rid = review_target(client, "review-000001", "ACC-0011")
    assert client.post(f"/api/investigations/{rid}/reviews", json={"action": "approve", "reason": "ok"}).status_code == 422
    done = client.post(f"/api/investigations/{rid}/reviews",
                       json={"action": "approve", "reason": "Customer confirmed by phone call"})
    assert done.status_code == 201
    body = done.json()
    assert body["assessment"]["decision"] == "Verify"  # original automated decision is immutable
    assert body["assessment"]["outcome"] == "approved_after_review"
    assert body["reviews"][0]["original_decision"] == "Verify"
    assert body["reviews"][0]["original_risk_score"] == pytest.approx(body["assessment"]["risk_score"], abs=0.01)
    assert body["can_review"] is False
    assert any(e["kind"] == "review" for e in body["timeline"])
    second = client.post(f"/api/investigations/{rid}/reviews", json={"action": "reject", "reason": "Changed my mind"})
    assert second.status_code == 409


def test_concurrent_reviews_are_serialised(client: TestClient) -> None:
    rid = review_target(client, "review-000002", "ACC-0012")
    body = {"action": "reject", "reason": "Beneficiary could not be verified"}
    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = sorted(pool.map(lambda _: client.post(f"/api/investigations/{rid}/reviews", json=body).status_code, range(6)))
    assert codes.count(201) == 1 and codes.count(409) == 5


def test_only_verify_can_be_reviewed(client: TestClient) -> None:
    permitted = client.get("/api/transactions", params={"decision": "Permit", "page_size": 1}).json()["items"][0]
    response = client.post(f"/api/investigations/{permitted['request_id']}/reviews",
                           json={"action": "approve", "reason": "Looks fine to me"})
    assert response.status_code == 409


def test_blocked_and_pending_attempts_are_excluded_from_completed_volume(client: TestClient) -> None:
    before = client.get("/api/overview").json()["volumes"]
    review_target(client, "volume-000001", "ACC-0013")  # pending verification
    flagged = client.get("/api/simulator/options").json()["flagged_beneficiaries"][0]["id"]
    client.post("/api/simulations", json=payload("volume-000002", recipient_id=flagged, amount=900.0))
    after = client.get("/api/overview").json()["volumes"]
    assert after["completed"] == pytest.approx(before["completed"])
    assert after["pending_verification"] == pytest.approx(before["pending_verification"] + 6_000)
    assert after["blocked_attempts"] == pytest.approx(before["blocked_attempts"] + 900)


def test_stream_lifecycle_is_backend_owned(client: TestClient) -> None:
    assert client.get("/api/simulation-stream").json()["running"] is False
    for _ in range(3):  # several tabs pressing start must not create several producers
        assert client.post("/api/simulation-stream/start").json()["running"] is True
    deadline = time.time() + 10
    while client.get("/api/simulation-stream").json()["produced"] < 3 and time.time() < deadline:
        time.sleep(0.05)
    stopped = client.post("/api/simulation-stream/stop").json()
    assert stopped["running"] is False
    produced = stopped["produced"]
    assert produced >= 3
    time.sleep(0.4)
    assert client.get("/api/simulation-stream").json()["produced"] <= produced + 1
    tasks = [t for t in client.app.state.stream.__dict__.values() if t.__class__.__name__ == "Task"]
    assert len(tasks) == 1
    feed = client.get("/api/live-transfers", params={"after": 0}).json()
    assert any(i["producer"] == "stream" for i in feed["items"])
    cursor = feed["next_cursor"]
    assert client.get("/api/live-transfers", params={"after": cursor}).json()["items"] == []
    mode = client.post("/api/simulation-stream/mode", json={"mode": "batch_5"}).json()
    assert mode["mode"] == "batch_5"
    client.post("/api/simulation-stream/mode", json={"mode": "continuous"})


def test_algorithms_and_evaluation_endpoints(client: TestClient) -> None:
    algorithms = client.get("/api/algorithms").json()
    assert algorithms["policy"]["weights"] == {"isolation_forest": 0.35, "lof": 0.25, "dbscan": 0.10, "rules": 0.30}
    assert algorithms["model"]["selected_parameters"]["lof"]["n_neighbors"] in (20, 35, 50)
    assert set(algorithms["distributions"]) == {"isolation_forest", "lof", "rules", "risk_score"}
    evaluation = client.get("/api/evaluation")
    assert evaluation.status_code == 200
    assert evaluation.json()["model_version"] == algorithms["model"]["model_version"]


def test_missing_model_routes_everything_to_verify(tmp_path: Path) -> None:
    settings = replace(load_settings(), models_dir=tmp_path / "no-models", autostart_stream=False)
    with TestClient(create_app(settings)) as degraded:
        assert degraded.get("/api/health").json()["status"] == "degraded"
        body = degraded.post("/api/simulations", json=payload("degraded-0001")).json()
        assert (body["decision"], body["decision_source"], body["assessment_status"]) == (
            "Verify", "assessment_safeguard", "model_unavailable")
        assert body["risk_score"] is None
