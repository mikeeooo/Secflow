from fastapi.testclient import TestClient

from mia_demo.api import create_app
from mia_demo.cli import run_pipeline


def test_full_demo_pipeline_writes_readable_api_artifacts(tmp_path):
    result = run_pipeline(tmp_path, seed=14, accounts=30, attempts=500, robustness=True)
    assert result["dataset"]["requests"] == 500
    assert result["evaluation"]["test_rows"] > 0
    assert result["evaluation"]["api_benchmark"]["p95_ms"] > 0
    assert result["evaluation"]["validation"]["rows"] > 0
    assert len(result["evaluation"]["robustness"]["seeds"]) == 3
    assert result["evaluation"]["robustness"]["unseen_accounts"]["test_rows"] > 0
    client = TestClient(create_app(tmp_path / "data" / "demo.sqlite3", tmp_path / "artifacts" / "model.joblib", tmp_path / "reports" / "evaluation.json"))
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/accounts").json()
    assert client.get("/experiments").json()["test_range"] == "days 81-100"
    findings = client.get("/batch-findings").json()
    assert findings["total"] >= len(findings["items"])
    assert client.get("/transactions").json()["total"] == 500
    assert client.get("/activity").json()
