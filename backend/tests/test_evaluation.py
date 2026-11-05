from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest import mock

import numpy as np
import pytest

from config.settings import load_settings
from ml.algorithms.isolation_forest import IsolationForestDetector
from ml.algorithms.local_outlier_factor import LocalOutlierFactorDetector
from ml.evaluation import binary_metrics, policy_metrics, run_evaluation, wilson_interval
from ml.model import load_bundle


def test_undefined_metrics_are_null_not_invented() -> None:
    y = np.array([True, False, False])
    result = binary_metrics(np.zeros(3, dtype=bool), y)
    assert result["precision"] is None and result["f1"] is None
    assert result["recall"] == 0.0
    assert "undefined" in result["note"]
    assert wilson_interval(0, 0) is None
    empty = policy_metrics(np.zeros(3, dtype=int), np.zeros(3, dtype=bool))
    assert empty["verify_or_block"]["recall"] is None


def test_wilson_interval_widens_for_small_samples() -> None:
    small = wilson_interval(5, 5)
    large = wilson_interval(500, 500)
    assert small is not None and large is not None
    assert small[0] < large[0] < 1.0


@pytest.fixture(scope="module")
def evaluations(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict, dict, dict[str, int]]:
    settings = load_settings()
    rows = {"isolation_forest": 0, "lof": 0}
    original_if, original_lof = IsolationForestDetector.raw_scores, LocalOutlierFactorDetector.raw_scores

    def count_if(self, matrix):  # type: ignore[no-untyped-def]
        rows["isolation_forest"] += len(matrix)
        return original_if(self, matrix)

    def count_lof(self, matrix):  # type: ignore[no-untyped-def]
        rows["lof"] += len(matrix)
        return original_lof(self, matrix)

    forbid = mock.Mock(side_effect=AssertionError("evaluation must not fit an estimator"))
    with mock.patch.object(IsolationForestDetector, "raw_scores", count_if), mock.patch.object(
        LocalOutlierFactorDetector, "raw_scores", count_lof
    ), mock.patch("sklearn.ensemble.IsolationForest.fit", forbid), mock.patch(
        "sklearn.neighbors.LocalOutlierFactor.fit", forbid
    ), mock.patch("sklearn.cluster.DBSCAN.fit", forbid):
        first = run_evaluation(replace(settings, artifacts_dir=tmp_path_factory.mktemp("eval-a")))
        counted = dict(rows)
    second = run_evaluation(replace(settings, artifacts_dir=tmp_path_factory.mktemp("eval-b")))
    return first, second, counted


def _without_timing(summary: dict) -> dict:
    data = {k: v for k, v in summary.items() if k not in {"generated_at", "latency_ms"}}
    data["headline"] = {k: v for k, v in summary["headline"].items() if k != "latency_p95_ms"}
    return data


def test_repeated_evaluation_is_identical_apart_from_timing(evaluations) -> None:
    first, second, _ = evaluations
    assert _without_timing(first) == _without_timing(second)


def test_each_component_scores_each_row_once(evaluations) -> None:
    first, _, counted = evaluations
    expected = 10_000 + first["test_requests"] + first["latency_ms"]["requests_timed"]  # validation + test + timing
    assert counted == {"isolation_forest": expected, "lof": expected}


def test_evaluation_uses_only_the_chronological_test_period(evaluations) -> None:
    first, _, _ = evaluations
    assert first["test_requests"] == 20_000 and first["test_fraud"] == 200
    assert first["splits"]["test"] == {"requests": 20_000, "fraud": 200, "fraud_share": 0.01}
    assert first["cold_start_accounts"]["accounts"] == 40
    assert first["unusual_legitimate"]["requests"] == 1_000


def test_reports_both_positive_views_and_separate_evidence_channel(evaluations) -> None:
    first, _, _ = evaluations
    for view in (first["combined_policy"], first["combined_policy_without_evidence"]):
        assert {"verify_or_block", "block_only"} <= set(view)
    channel = first["evidence_channel"]
    assert channel["fraud_with_active_evidence"] + channel["fraud_without_evidence"] == 200
    assert set(first["components"]) == {"isolation_forest", "lof", "dbscan", "rules", "combined_risk_score"}


def test_exported_metadata_matches_loaded_artifact() -> None:
    import json

    settings = load_settings()
    exported = json.loads((settings.artifacts_dir / "evaluation.json").read_text())
    assert exported["model_version"] == load_bundle(settings.models_dir).version
    assert Path(settings.artifacts_dir / "evaluation.md").read_text().startswith("# SecFlow evaluation report")
