from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from config.settings import load_settings
from ml.algorithms.dbscan_context import DBSCANContext, EmptyCoreError
from ml.algorithms.isolation_forest import IsolationForestDetector
from ml.algorithms.local_outlier_factor import LocalOutlierFactorDetector
from ml.algorithms.preprocessing import EmpiricalScoreMapping, FeaturePreprocessor
from ml.features import PAYMENT_FEATURES
from ml.model import BundleError, load_bundle, load_operating_point

RNG = np.random.default_rng(7)
NORMAL = RNG.normal(0, 1, size=(2_000, 4))
OUTLIER = np.array([[8.0, 8.0, 8.0, 8.0]])


def test_isolation_forest_scores_higher_for_outliers_and_is_reproducible() -> None:
    a = IsolationForestDetector(100, 256, 42).fit(NORMAL)
    b = IsolationForestDetector(100, 256, 42).fit(NORMAL)
    assert a.raw_scores(OUTLIER)[0] > np.quantile(a.raw_scores(NORMAL[:200]), 0.99)
    assert np.array_equal(a.raw_scores(NORMAL[:50]), b.raw_scores(NORMAL[:50]))


def test_lof_novelty_scores_unseen_rows_and_uses_training_diagnostics_separately() -> None:
    detector = LocalOutlierFactorDetector(n_neighbors=20).fit(NORMAL)
    assert detector.model.novelty is True
    unseen = RNG.normal(0, 1, size=(200, 4))
    assert detector.raw_scores(OUTLIER)[0] > np.quantile(detector.raw_scores(unseen), 0.99)
    diagnostics = detector.training_diagnostics()
    assert diagnostics["fit_rows"] == 2_000
    with pytest.raises(AttributeError):
        detector.model.fit_predict(NORMAL)  # novelty mode forbids scoring the fitting rows this way


def test_score_mapping_is_monotonic_bounded_and_deterministic() -> None:
    mapping = EmpiricalScoreMapping().fit(np.array([1.0, 2.0, 2.0, 3.0]))
    out = mapping.transform(np.array([0.0, 1.0, 2.0, 2.5, 3.0, 99.0]))
    assert out.tolist() == [0.0, 0.25, 0.75, 0.75, 1.0, 1.0]
    assert np.all(np.diff(mapping.transform(np.linspace(-5, 5, 50))) >= 0)
    with pytest.raises(ValueError):
        mapping.transform(np.array([np.nan]))


def test_preprocessor_rejects_non_finite_and_uses_training_quantiles() -> None:
    pre = FeaturePreprocessor().fit(NORMAL)
    clipped = pre.transform(np.array([[1e9, 0, 0, 0]]))
    assert np.isfinite(clipped).all()
    with pytest.raises(ValueError):
        pre.transform(np.array([[np.inf, 0, 0, 0]]))


def test_dbscan_context_near_core_outside_insufficient_and_empty() -> None:
    context = DBSCANContext(eps=0.5, min_samples=5).fit(NORMAL)
    results = context.score(np.vstack([NORMAL[:1], OUTLIER, OUTLIER]), ["ok", "ok", "insufficient_history"])
    assert (results[0].score, results[0].status) == (0.0, "within_context")
    assert (results[1].score, results[1].status) == (1.0, "outside_context")
    assert (results[2].score, results[2].status) == (0.0, "insufficient_history")
    sparse = np.arange(20, dtype=float).reshape(-1, 1) * 100
    with pytest.raises(EmptyCoreError):
        DBSCANContext(eps=0.01, min_samples=5).fit(sparse)


def test_saved_bundle_round_trip_and_schema_metadata() -> None:
    settings = load_settings()
    bundle = load_bundle(settings.models_dir)
    point = load_operating_point(settings.models_dir, bundle.version)
    assert tuple(bundle.metadata["payment_features"]) == PAYMENT_FEATURES
    assert bundle.metadata["fit_rows"]["isolation_forest"] == 60_000
    assert bundle.metadata["fit_rows"]["score_mapping_reference"] == 10_000
    assert bundle.dbscan.core_samples is not None and len(bundle.dbscan.core_samples) > 0
    assert 0 < point.verify < point.block <= 100
    rows = np.zeros((3, len(PAYMENT_FEATURES)))
    out = bundle.score_batch(rows, np.zeros((3, 8)), ["ok", "ok", "insufficient_history"])
    assert all(0 <= c.if_score <= 1 and 0 <= c.lof_score <= 1 for c in out)


def test_bundle_with_mismatched_schema_is_rejected(tmp_path: Path) -> None:
    import joblib

    settings = load_settings()
    payload = joblib.load(settings.models_dir / "secflow_model.joblib")
    payload["metadata"] = {**payload["metadata"], "payment_features": ["something_else"]}
    joblib.dump(payload, tmp_path / "secflow_model.joblib")
    with pytest.raises(BundleError):
        load_bundle(tmp_path)
    with pytest.raises(BundleError):
        load_bundle(tmp_path / "missing")


def test_training_never_fit_on_held_out_partitions() -> None:
    import json

    settings = load_settings()
    report = json.loads((settings.models_dir / "training_report.json").read_text())
    meta = json.loads((settings.models_dir / "metadata.json").read_text())
    assert meta["fit_rows"]["preprocessing"] == 60_000
    assert meta["fit_rows"]["dbscan"] <= 60_000
    assert report["operating_point"]["source"].startswith("validated")
    assert all(r["fit_rows"] == 60_000 for r in report["search"]["lof"])
