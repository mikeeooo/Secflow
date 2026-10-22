"""Reproducible local commands for the six-stage university demonstration."""

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

from mia_demo.evaluation import evaluate_dbscan, evaluate_replay, evaluate_validation
from mia_demo.features.replay import export_feature_rows, training_peer_median
from mia_demo.ml.bundle import load_bundle, save_bundle
from mia_demo.ml.cluster import daily_snapshots, fit_cluster_reference, load_reference, run_clustering, save_reference
from mia_demo.ml.train import train_models
from mia_demo.simulation.generator import generate, load_dataset
from mia_demo.storage import Repository


def benchmark_api(model_path: Path, samples: int = 30) -> dict:
    """In-process HTTP/SQLite request timing, isolated from the demonstration DB."""
    from fastapi.testclient import TestClient
    import numpy as np
    from mia_demo.api import create_app

    with TemporaryDirectory(prefix="secflow-benchmark-") as directory:
        db_path = Path(directory) / "bench.sqlite3"
        repo = Repository(db_path)
        opened = datetime.now(timezone.utc) - timedelta(days=100)
        repo.insert_accounts({"BENCH-A": {"opened_at": opened, "balance_bani": 10000000}, "BENCH-B": {"opened_at": opened, "balance_bani": 10000000}})
        client = TestClient(create_app(db_path, model_path))
        session = client.post("/sessions", json={"local_account_id": "BENCH-A", "device_id": "BENCH-DEVICE"}).json()["session_id"]
        durations = []
        for index in range(samples):
            payload = dict(transaction_id=f"BENCH-{index}-{uuid4().hex[:6]}", sender_account_id="BENCH-A", receiver_account_id="BENCH-B", receiver_psp="LOCAL", amount_bani=100, currency="MDL", session_id=session, device_id="BENCH-DEVICE", initiation_method="APP")
            started = perf_counter()
            response = client.post("/assessments", json=payload)
            durations.append((perf_counter() - started) * 1000)
            if response.status_code != 200:
                raise RuntimeError(f"API benchmark request failed: {response.status_code}")
    return dict(samples=samples, p50_ms=round(float(np.percentile(durations, 50)), 3), p95_ms=round(float(np.percentile(durations, 95)), 3), p99_ms=round(float(np.percentile(durations, 99)), 3), measurement="FastAPI TestClient in-process with SQLite and model scoring; no network transport")


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _read_jsonl(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def generate_command(root: Path, seed: int, accounts: int, attempts: int):
    dataset = generate(seed=seed, accounts=accounts, attempts=attempts)
    manifest = dataset.save(root / "data")
    return dataset, manifest


def train_command(root: Path, dataset):
    rows = export_feature_rows(dataset)
    _write_jsonl(root / "data" / "features.jsonl", rows)
    lock_path = root / "uv.lock"
    lock_hash = sha256(lock_path.read_bytes()).hexdigest() if lock_path.exists() else None
    bundle = train_models([row for row in rows if row["split"] == "train"], [row for row in rows if row["split"] == "calibration"], peer_median_bani=training_peer_median(dataset), generator_config=dataset.config, lock_sha256=lock_hash)
    save_bundle(bundle, root / "artifacts" / "model.joblib")
    return rows, bundle


def cluster_command(root: Path, dataset):
    daily = daily_snapshots(dataset, range(11, 101))
    training = [row for day in range(11, 61) for row in daily[day]]
    validation = [row for day in range(71, 81) for row in daily[day]]
    reference = fit_cluster_reference(training, validation)
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    save_reference(reference, root / "artifacts" / "cluster.joblib")
    (root / "artifacts" / "cluster.json").write_text(json.dumps(reference.metadata, indent=2), encoding="utf-8")
    report, findings = evaluate_dbscan(dataset, daily, reference)
    _write_jsonl(root / "reports" / "dbscan_findings.jsonl", findings)
    (root / "reports" / "dbscan.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report, findings


def _save_figure(report, root: Path):
    names = list(report["methods"])
    precision = [report["methods"][name]["precision"] for name in names]
    recall = [report["methods"][name]["recall"] for name in names]
    fig, axis = plt.subplots(figsize=(10, 5), layout="constrained")
    positions = list(range(len(names)))
    axis.bar([x - 0.18 for x in positions], precision, width=0.36, label="Precision", color="#1764B0")
    axis.bar([x + 0.18 for x in positions], recall, width=0.36, label="Recall", color="#C47B14")
    axis.set_xticks(positions, [name.replace("_", "\n") for name in names])
    axis.set_ylim(0, 1)
    axis.set_ylabel("Score pe testul sintetic blocat")
    axis.set_title("Comparația metodelor · zilele 81–100")
    axis.legend()
    axis.spines[["top", "right"]].set_visible(False)
    fig.savefig(root / "reports" / "model_comparison.png", dpi=180)
    plt.close(fig)


def evaluate_command(root: Path, dataset, rows, bundle, dbscan_report=None):
    report = evaluate_replay(dataset, rows, bundle)
    report["validation"] = evaluate_validation(dataset, rows, bundle)
    report["api_benchmark"] = benchmark_api(root / "artifacts" / "model.joblib")
    if dbscan_report is not None:
        report["dbscan"] = dbscan_report
    (root / "reports").mkdir(parents=True, exist_ok=True)
    (root / "reports" / "evaluation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _save_figure(report, root)
    return report


def seed_command(root: Path, dataset, findings):
    repo = Repository(root / "data" / "demo.sqlite3")
    return repo.seed_dataset(dataset, findings)


def robustness_runs(seed: int, accounts: int, attempts: int, baseline_report: dict, baseline_bundle) -> dict:
    seed_reports = [dict(seed=seed, model_version=baseline_bundle.version, test_rows=baseline_report["test_rows"], combined=baseline_report["methods"]["combined"])]
    for additional_seed in (seed + 1, seed + 2):
        dataset = generate(seed=additional_seed, accounts=accounts, attempts=attempts)
        rows = export_feature_rows(dataset)
        bundle = train_models([row for row in rows if row["split"] == "train"], [row for row in rows if row["split"] == "calibration"], peer_median_bani=training_peer_median(dataset), generator_config=dataset.config)
        report = evaluate_replay(dataset, rows, bundle)
        seed_reports.append(dict(seed=additional_seed, model_version=bundle.version, test_rows=report["test_rows"], combined=report["methods"]["combined"]))
    unseen = generate(seed=seed + 3, accounts=accounts, attempts=attempts, account_prefix="U")
    unseen_rows = export_feature_rows(unseen, peer_median_bani=baseline_bundle.peer_median_bani)
    unseen_report = evaluate_replay(unseen, unseen_rows, baseline_bundle)
    return dict(seeds=seed_reports, unseen_accounts=dict(seed=seed + 3, account_prefix="U", test_rows=unseen_report["test_rows"], combined=unseen_report["methods"]["combined"]), note="Each seed run retrains on its own days 11-60 and calibrates on days 61-70. The unseen-account run uses the baseline model and a disjoint account-ID population with the same generator design; this is not external validation.")


def run_pipeline(root: str | Path, seed: int = 42, accounts: int = 400, attempts: int = 10000, robustness: bool = False) -> dict:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    dataset, manifest = generate_command(root, seed, accounts, attempts)
    rows, bundle = train_command(root, dataset)
    dbscan_report, findings = cluster_command(root, dataset)
    report = evaluate_command(root, dataset, rows, bundle, dbscan_report)
    if robustness:
        report["robustness"] = robustness_runs(seed, accounts, attempts, report, bundle)
        (root / "reports" / "evaluation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    seeded = seed_command(root, dataset, findings)
    return {"dataset": manifest, "evaluation": report, "demo_seeded": seeded}


def main():
    parser = argparse.ArgumentParser(description="SecFlow MIA simulated university demo")
    parser.add_argument("command", choices=["all", "generate", "train", "cluster", "evaluate", "seed"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--accounts", type=int, default=400)
    parser.add_argument("--attempts", type=int, default=10000)
    parser.add_argument("--robustness", action="store_true", help="Repeat with three seeds and an unseen account-ID population")
    args = parser.parse_args()
    root = args.root
    if args.command == "all":
        result = run_pipeline(root, args.seed, args.accounts, args.attempts, args.robustness)
        print(json.dumps({"requests": result["dataset"]["requests"], "labels": result["dataset"]["labels"], "model_version": result["evaluation"]["model_version"], "test_rows": result["evaluation"]["test_rows"], "demo_seeded": result["demo_seeded"]}, indent=2))
        return
    if args.command == "generate":
        _, manifest = generate_command(root, args.seed, args.accounts, args.attempts)
        print(json.dumps(manifest, indent=2))
        return
    dataset = load_dataset(root / "data")
    if args.command == "train":
        _, bundle = train_command(root, dataset)
        print(bundle.version)
        return
    if args.command == "cluster":
        report, _ = cluster_command(root, dataset)
        print(json.dumps(report, indent=2))
        return
    rows = _read_jsonl(root / "data" / "features.jsonl")
    bundle = load_bundle(root / "artifacts" / "model.joblib")
    if args.command == "evaluate":
        dbscan_path = root / "reports" / "dbscan.json"
        dbscan_report = json.loads(dbscan_path.read_text(encoding="utf-8")) if dbscan_path.exists() else None
        report = evaluate_command(root, dataset, rows, bundle, dbscan_report)
        print(json.dumps(report["methods"], indent=2))
        return
    findings = _read_jsonl(root / "reports" / "dbscan_findings.jsonl")
    for row in findings:
        row["window_end"] = datetime.fromisoformat(row["window_end"])
        row["available_at"] = datetime.fromisoformat(row["available_at"])
    print("seeded" if seed_command(root, dataset, findings) else "already seeded")


if __name__ == "__main__":
    main()
