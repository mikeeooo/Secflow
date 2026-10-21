from mia_demo.evaluation import evaluate_replay
from mia_demo.features.replay import export_feature_rows
from mia_demo.ml.train import train_models
from mia_demo.simulation.generator import generate


def test_locked_test_report_uses_private_labels_only_for_metrics():
    dataset = generate(seed=5, accounts=30, attempts=500)
    rows = export_feature_rows(dataset)
    bundle = train_models([r for r in rows if r["split"] == "train"], [r for r in rows if r["split"] == "calibration"])
    metadata_before = bundle.metadata.copy()
    report = evaluate_replay(dataset, rows, bundle)
    assert report["test_range"] == "days 81-100"
    assert set(report["methods"]) == {"rules_only", "isolation_forest", "lof", "if_plus_lof", "combined"}
    assert report["test_rows"] > 0
    assert report["test_labels"] == len(dataset.labels)
    assert bundle.metadata == metadata_before
    assert report["methods"]["combined"]["threshold"] == 60
