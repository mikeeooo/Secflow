"""Locked chronological evaluation; private labels join only after scoring."""

from collections import defaultdict
from datetime import datetime
import platform
import tracemalloc
from time import perf_counter

import numpy as np
from sklearn.metrics import auc, precision_recall_curve

from mia_demo.risk.engine import assess, rule_evidence
from mia_demo.schemas import FeatureRow


def _metrics(labels: list[int], scores: list[float], threshold: float = 60) -> dict:
    y = np.asarray(labels, dtype=int)
    s = np.asarray(scores, dtype=float)
    predicted = s >= threshold
    tp = int(np.sum(predicted & (y == 1)))
    fp = int(np.sum(predicted & (y == 0)))
    fn = int(np.sum(~predicted & (y == 1)))
    tn = int(np.sum(~predicted & (y == 0)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    pr_auc = None
    if len(set(labels)) == 2:
        curve_precision, curve_recall, _ = precision_recall_curve(y, s)
        pr_auc = float(auc(curve_recall[::-1], curve_precision[::-1]))
    return dict(threshold=threshold, precision=round(precision, 4), recall=round(recall, 4), f1=round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0, false_positive_rate=round(fpr, 4), pr_auc=round(pr_auc, 4) if pr_auc is not None else None, alert_volume=tp + fp, tp=tp, fp=fp, fn=fn, tn=tn)


def _percentiles(samples: list[float], unit: str) -> dict:
    return {f"p{percentile}_{unit}": round(float(np.percentile(samples, percentile)), 3) for percentile in (50, 95, 99)} if samples else {}


def evaluate_replay(dataset, rows: list[dict], bundle, verify_threshold: float = 60, block_threshold: float = 85) -> dict:
    test_rows = [row for row in rows if row["split"] == "test"]
    if not test_rows:
        raise ValueError("No locked final-test rows")
    labels = [int(dataset.labels.get(row["transaction_id"], {}).get("is_simulated_fraud", False)) for row in test_rows]
    scores = defaultdict(list)
    total_latency = []
    model_latency = []
    for row in test_rows:
        feature = FeatureRow.model_validate(row["features"])
        started = perf_counter()
        model_started = perf_counter()
        raw = bundle.score(feature)
        model_latency.append((perf_counter() - model_started) * 1000)
        rules, _ = rule_evidence(feature)
        rank = 0.6 * raw["if_percentile"] + 0.4 * raw["lof_percentile"]
        scores["rules_only"].append(100 * rules)
        scores["isolation_forest"].append(100 * raw["if_percentile"])
        scores["lof"].append(100 * raw["lof_percentile"])
        scores["if_plus_lof"].append(100 * rank)
        scores["combined"].append(100 * (0.7 * rank + 0.3 * rules))
        total_latency.append((perf_counter() - started) * 1000)
    methods = {name: _metrics(labels, values, verify_threshold) for name, values in scores.items()}
    methods["combined"]["block_volume"] = sum(value >= block_threshold for value in scores["combined"])
    per_type = {}
    for scenario_type in sorted(set(label["scenario_type"] for label in dataset.labels.values())):
        indices = [index for index, row in enumerate(test_rows) if dataset.labels.get(row["transaction_id"], {}).get("scenario_type") == scenario_type]
        if indices:
            per_type[scenario_type] = dict(cases=len(indices), detected=sum(scores["combined"][i] >= verify_threshold for i in indices), recall=round(sum(scores["combined"][i] >= verify_threshold for i in indices) / len(indices), 4))
    grouped = defaultdict(list)
    for index, row in enumerate(test_rows):
        label = dataset.labels.get(row["transaction_id"])
        if label:
            grouped[label["scenario_id"]].append((datetime.fromisoformat(row["occurred_at"]), scores["combined"][index]))
    times_to_detection = []
    for events in grouped.values():
        start = min(time for time, _ in events)
        alerted = [time for time, value in events if value >= verify_threshold]
        if alerted:
            times_to_detection.append((min(alerted) - start).total_seconds())
    observed = sum(labels) / len(labels)
    sensitivity = {}
    tpr = methods["combined"]["recall"]
    fpr = methods["combined"]["false_positive_rate"]
    for prevalence in (0.001, 0.03):
        denominator = tpr * prevalence + fpr * (1 - prevalence)
        sensitivity[f"{prevalence:.1%}"] = round(tpr * prevalence / denominator, 4) if denominator else None
    return {
        "simulation": True,
        "test_range": "days 81-100",
        "test_rows": len(test_rows),
        "test_labels": sum(labels),
        "observed_test_prevalence": round(observed, 5),
        "model_version": bundle.version,
        "policy_version": "policy-v1",
        "methods": methods,
        "per_scenario": per_type,
        "scenario_time_to_detection": _percentiles(times_to_detection, "seconds"),
        "offline_assessment_latency": _percentiles(total_latency, "ms"),
        "model_scoring_latency": _percentiles(model_latency, "ms"),
        "hardware": dict(machine=platform.machine(), processor=platform.processor(), python=platform.python_version()),
        "prevalence_sensitivity": sensitivity,
        "evaluation_notes": [
            "All fitting and calibration ignore private scenario labels; labels join only for validation and final metrics.",
            "Thresholds 60/85 were frozen before final testing; no final-test tuning.",
            "The 0.1% and 3% values are precision projections using measured TPR/FPR, not MIA prevalence estimates.",
            "Offline scoring uses fixed synthetic history; it does not model fraud prevented by a Block decision.",
            "Anomaly ranking is not fraud probability; some authorized scams are not behaviorally distinguishable.",
        ],
    }


def evaluate_dbscan(dataset, snapshots_by_day: dict, reference) -> tuple[dict, list[dict]]:
    """Score account-day findings separately from transaction alerts."""
    from mia_demo.ml.cluster import run_clustering

    request_by_id = {row["transaction_id"]: row for row in dataset.requests}
    positive_pairs = set()
    for transaction_id in dataset.labels:
        request = request_by_id[transaction_id]
        if request["split"] == "test":
            day = (datetime.fromisoformat(request["occurred_at"]).date() - datetime.fromisoformat(dataset.config["start"]).date()).days + 1
            positive_pairs.add((day, request["sender_account_id"]))
    tracemalloc.start()
    started = perf_counter()
    all_findings = []
    labels = []
    noise_scores = []
    contextual_scores = []
    for day in range(81, 101):
        for finding in run_clustering(snapshots_by_day[day], reference):
            all_findings.append(finding)
            labels.append(int((day, finding["local_account_id"]) in positive_pairs))
            noise_scores.append(100 if finding["noise_flag"] else 0)
            contextual_scores.append(100 if finding["contextual_rule_flags"] else 0)
    duration = perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    report = dict(account_windows=len(labels), positive_account_windows=sum(labels), noise_only=_metrics(labels, noise_scores), contextual_flags=_metrics(labels, contextual_scores), runtime_seconds=round(duration, 3), python_allocations_peak_mb=round(peak / 1024 / 1024, 2), caveat="Cluster IDs are local to each daily fit; noise and contextual flags are investigation signals, not fraud proof. Memory number is Python traced allocations, not total native RSS.")
    return report, all_findings


def evaluate_validation(dataset, rows: list[dict], bundle, threshold: float = 60) -> dict:
    """Inspect fixed policy on days 71-80 without changing it."""
    selected = [row for row in rows if row["split"] == "validation"]
    labels = [int(dataset.labels.get(row["transaction_id"], {}).get("is_simulated_fraud", False)) for row in selected]
    scores = [assess(FeatureRow.model_validate(row["features"]), bundle).score for row in selected]
    return dict(rows=len(selected), labels=sum(labels), fixed_threshold_metrics=_metrics(labels, scores, threshold), usage="Validation labels assess the predeclared policy; final-test labels never tune it")
