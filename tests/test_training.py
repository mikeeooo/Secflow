from pathlib import Path

import pytest

from mia_demo.features.replay import export_feature_rows
from mia_demo.ml.bundle import load_bundle, save_bundle
from mia_demo.ml.train import train_models
from mia_demo.schemas import FEATURE_ORDER
from mia_demo.simulation.generator import generate


def test_models_use_allowlisted_features_and_persist_exact_scores(tmp_path: Path):
    rows = export_feature_rows(generate(seed=12, accounts=40, attempts=600))
    train = [r for r in rows if r["split"] == "train"]
    calibration = [r for r in rows if r["split"] == "calibration"]
    bundle = train_models(train, calibration, peer_median_bani=12000)
    assert bundle.feature_order == FEATURE_ORDER
    candidate = rows[-1]["features"]
    original = bundle.score(candidate)
    assert all(0 <= value <= 1 for value in original.values())
    save_bundle(bundle, tmp_path / "model.joblib")
    assert load_bundle(tmp_path / "model.joblib").score(candidate) == original
    with pytest.raises(ValueError, match="schema"):
        bundle.score({key: value for key, value in candidate.items() if key != "log_amount"})


def test_evaluation_labels_cannot_affect_unsupervised_fit():
    rows = export_feature_rows(generate(seed=8, accounts=30, attempts=500))
    train = [r for r in rows if r["split"] == "train"]
    calibration = [r for r in rows if r["split"] == "calibration"]
    first = train_models(train, calibration)
    altered = [dict(row, evaluation_label=1) for row in train]
    second = train_models(altered, calibration)
    assert first.score(rows[-1]["features"]) == second.score(rows[-1]["features"])
