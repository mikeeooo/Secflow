"""Offline training: chronological fitting, bounded parameter search, and operating-point selection.

Data use per partition (labels are only opened where stated):

* train (days 1-60): fit preprocessing, IsolationForest, LOF (novelty) and DBSCAN. No labels.
* calibration (61-70): fit IF/LOF empirical score mappings. No labels.
* validation (71-80): labels used to choose estimator parameters and policy thresholds.
* test (81-100): not touched here. `ml.evaluation` opens it once, after freezing.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from ml.algorithms.dbscan_context import DBSCANContext, EmptyCoreError
from ml.algorithms.isolation_forest import IsolationForestDetector
from ml.algorithms.local_outlier_factor import LocalOutlierFactorDetector
from ml.algorithms.preprocessing import EmpiricalScoreMapping, FeaturePreprocessor
from ml.assess import build_evidence_store
from ml.features import CONTEXT_FEATURES, FEATURE_VERSION, PAYMENT_FEATURES
from ml.model import ModelBundle, sklearn_version
from ml.policy import (
    OperatingPoint,
    Policy,
    assessment_status,
    combine_arrays,
    decide_arrays,
    evaluate_rules,
)
from ml.replay import ReplayResult, replay
from storage.dataset import Dataset, load_dataset, load_labels, load_splits

SEED = 42
IF_GRID = ({"n_estimators": 100, "max_samples": 256}, {"n_estimators": 100, "max_samples": 512},
           {"n_estimators": 200, "max_samples": 256}, {"n_estimators": 200, "max_samples": 512})
LOF_GRID = (20, 35, 50)
DBSCAN_MIN_SAMPLES = (5, 10, 20)
DBSCAN_EPS_QUANTILES = (0.90, 0.95, 0.98)
DBSCAN_FIT_ROWS = 20_000
MODEL_FAMILY = "secflow-sk"


@dataclass(frozen=True)
class PartitionView:
    rows: np.ndarray  # boolean mask over replay rows

    def take(self, matrix: np.ndarray) -> np.ndarray:
        return matrix[self.rows]


def _partition_masks(result: ReplayResult, splits: dict[str, str]) -> dict[str, PartitionView]:
    part = np.array([splits[r] for r in result.request_ids])
    return {name: PartitionView(part == name) for name in ("train", "calibration", "validation", "test")}


def _ap(y: np.ndarray, scores: np.ndarray) -> float | None:
    return float(average_precision_score(y, scores)) if 0 < y.sum() < len(y) else None


def rule_scores_for(result: ReplayResult, mask: np.ndarray, policy: Policy) -> tuple[np.ndarray, np.ndarray]:
    """Rules score and number of distinct corroborating families for the masked rows."""
    ids = np.array(result.request_ids)[mask]
    statuses = np.array(result.history_status)[mask]
    scores = np.empty(len(ids))
    families = np.empty(len(ids), dtype=np.int64)
    for i, (rid, status) in enumerate(zip(ids, statuses, strict=True)):
        outcome = evaluate_rules(result.facts[rid], status, policy)
        scores[i] = outcome.score
        families[i] = len(outcome.corroborating_families)
    return scores, families


def unsafe_mask_for(result: ReplayResult, mask: np.ndarray, policy: Policy) -> np.ndarray:
    ids = np.array(result.request_ids)[mask]
    statuses = np.array(result.history_status)[mask]
    out = np.zeros(len(ids), dtype=bool)
    for i, (rid, status) in enumerate(zip(ids, statuses, strict=True)):
        facts = result.facts[rid]
        state, _ = assessment_status(status, facts["amount"], facts["auth_method"], True, True, policy)
        out[i] = state in {"insufficient_history", "model_unavailable", "invalid_features"}
    return out


def _search_isolation_forest(x_train, x_cal, x_val, y_val) -> tuple[dict, list[dict]]:
    records, best = [], None
    for params in IF_GRID:
        started = time.perf_counter()
        detector = IsolationForestDetector(random_state=SEED, **params).fit(x_train)
        mapping = EmpiricalScoreMapping().fit(detector.raw_scores(x_cal))
        val = mapping.transform(detector.raw_scores(x_val))
        record = {**params, "validation_average_precision": _ap(y_val, val),
                  "fit_seconds": round(time.perf_counter() - started, 3)}
        records.append(record)
        if best is None or (record["validation_average_precision"] or 0) > (best[0]["validation_average_precision"] or 0):
            best = (record, detector, mapping)
    assert best is not None
    return {"record": best[0], "detector": best[1], "mapping": best[2]}, records


def _search_lof(x_train, x_cal, x_val, y_val) -> tuple[dict, list[dict]]:
    records, best = [], None
    for k in LOF_GRID:
        started = time.perf_counter()
        detector = LocalOutlierFactorDetector(n_neighbors=k).fit(x_train)
        # novelty scoring is only applied to unseen calibration/validation rows
        mapping = EmpiricalScoreMapping().fit(detector.raw_scores(x_cal))
        val = mapping.transform(detector.raw_scores(x_val))
        record = {"n_neighbors": k, "validation_average_precision": _ap(y_val, val),
                  **detector.training_diagnostics(), "fit_seconds": round(time.perf_counter() - started, 3)}
        records.append(record)
        if best is None or (record["validation_average_precision"] or 0) > (best[0]["validation_average_precision"] or 0):
            best = (record, detector, mapping)
    assert best is not None
    return {"record": best[0], "detector": best[1], "mapping": best[2]}, records


def _search_dbscan(profiles_train, ctx_val, status_val, y_val) -> tuple[dict, list[dict]]:
    rng = np.random.default_rng(SEED)
    rows = profiles_train
    if len(rows) > DBSCAN_FIT_ROWS:
        rows = rows[np.sort(rng.choice(len(rows), DBSCAN_FIT_ROWS, replace=False))]
    scaled = StandardScaler().fit_transform(rows)
    probe = scaled[rng.choice(len(scaled), min(5_000, len(scaled)), replace=False)]
    records, best = [], None
    for min_samples in DBSCAN_MIN_SAMPLES:
        distances, _ = NearestNeighbors(n_neighbors=min_samples).fit(scaled).kneighbors(probe)
        for quantile in DBSCAN_EPS_QUANTILES:
            eps = float(np.quantile(distances[:, -1], quantile))
            record: dict[str, Any] = {"min_samples": min_samples, "eps_quantile": quantile, "eps": round(eps, 5)}
            try:
                context = DBSCANContext(eps=eps, min_samples=min_samples).fit(rows)
            except EmptyCoreError as error:
                record["error"] = str(error)
                records.append(record)
                continue
            scored = np.array([c.score for c in context.score(ctx_val, status_val)])
            fraud_rate = float(scored[y_val].mean()) if y_val.any() else 0.0
            legit_rate = float(scored[~y_val].mean())
            record.update(context.summary)
            record.update({"validation_fraud_outside_rate": round(fraud_rate, 4),
                           "validation_legitimate_outside_rate": round(legit_rate, 4),
                           "validation_separation": round(fraud_rate - legit_rate, 4)})
            records.append(record)
            if legit_rate <= 0.15 and (best is None or record["validation_separation"] > best[0]["validation_separation"]):
                best = (record, context)
    if best is None:
        raise EmptyCoreError("No DBSCAN candidate produced core samples with an acceptable outside rate")
    return {"record": best[0], "context": best[1]}, records


def select_operating_point(
    risk: np.ndarray,
    families: np.ndarray,
    unsafe: np.ndarray,
    y: np.ndarray,
    policy: Policy,
) -> tuple[OperatingPoint, dict[str, Any]]:
    """Grid-search Verify/Block thresholds on validation (model + rules only, no evidence channel)."""
    goals = policy.goals
    search = policy.threshold_search
    verify_grid = np.arange(search["verify"]["start"], search["verify"]["stop"] + 1e-9, search["verify"]["step"])
    block_grid = np.arange(search["block"]["start"], search["block"]["stop"] + 1e-9, search["block"]["step"])
    no_evidence = np.zeros(len(risk), dtype=bool)
    n_legit = int((~y).sum())
    candidates, frontier = [], {}
    for verify in verify_grid:
        for block in block_grid:
            if block <= verify:
                continue
            decisions = decide_arrays(risk, families, unsafe, no_evidence, verify, block, policy.min_families)
            flagged = decisions > 0
            blocked = decisions == 2
            verify_rate = float((decisions == 1).mean())
            false_blocks = int((blocked & ~y).sum())
            true_blocks = int((blocked & y).sum())
            n_blocks = int(blocked.sum())
            row = {
                "verify_threshold": float(verify),
                "block_threshold": float(block),
                "recall_verify_or_block": float((flagged & y).sum() / max(1, y.sum())),
                "recall_block_only": float(true_blocks / max(1, y.sum())),
                "verify_rate": verify_rate,
                "block_rate": float(blocked.mean()),
                "legitimate_false_block_rate": false_blocks / max(1, n_legit),
                "block_precision": (true_blocks / n_blocks) if n_blocks else None,
                "predicted_blocks": n_blocks,
                "false_blocks": false_blocks,
            }
            feasible = (
                verify_rate <= goals["max_verify_rate"]
                and row["legitimate_false_block_rate"] <= goals["max_legitimate_false_block_rate"]
                and (n_blocks == 0 or row["block_precision"] >= goals["min_block_precision"])
            )
            row["meets_goals"] = feasible
            candidates.append(row)
            key = float(verify)
            if feasible and (key not in frontier or row["recall_block_only"] > frontier[key]["recall_block_only"]):
                frontier[key] = row
    feasible_rows = [c for c in candidates if c["meets_goals"]]
    if feasible_rows:
        chosen = max(
            feasible_rows,
            key=lambda c: (c["recall_verify_or_block"], c["recall_block_only"], -c["verify_rate"], -c["block_threshold"]),
        )
        source = "validated"
    else:  # keep ambiguous cases in Verify instead of pretending certainty
        chosen = min(candidates, key=lambda c: (c["legitimate_false_block_rate"], -c["recall_verify_or_block"]))
        source = "validated_goals_not_met"
    digest = hashlib.sha256(json.dumps(chosen, sort_keys=True).encode()).hexdigest()[:8]
    point = OperatingPoint(chosen["verify_threshold"], chosen["block_threshold"], source, f"op-{digest}")
    return point, {
        "chosen": chosen,
        "candidates_evaluated": len(candidates),
        "feasible_candidates": len(feasible_rows),
        "frontier": sorted(frontier.values(), key=lambda r: r["verify_threshold"]),
        "initial_candidate": next(
            (c for c in candidates if c["verify_threshold"] == policy.initial_verify and c["block_threshold"] == policy.initial_block),
            None,
        ),
    }


def _model_version(dataset: Dataset, selection: dict[str, Any]) -> str:
    material = json.dumps(
        {"files": {k: v["sha256"] for k, v in dataset.manifest["files"].items()}, "selection": selection,
         "features": FEATURE_VERSION, "sklearn": sklearn_version()},
        sort_keys=True,
    )
    return f"{MODEL_FAMILY}-1.0-{hashlib.sha256(material.encode()).hexdigest()[:10]}"


def train_models(training_dir: Path, models_dir: Path, policy: Policy) -> dict[str, Any]:
    started = time.perf_counter()
    dataset = load_dataset(training_dir)
    splits = load_splits(training_dir)
    validation_ids = [rid for rid, part in splits.items() if part == "validation"]
    result = replay(dataset, keep_facts_for=validation_ids)
    masks = _partition_masks(result, splits)
    tr, cal, val = masks["train"], masks["calibration"], masks["validation"]

    preprocessor = FeaturePreprocessor().fit(tr.take(result.payment))
    x_train = preprocessor.transform(tr.take(result.payment))
    x_cal = preprocessor.transform(cal.take(result.payment))
    x_val = preprocessor.transform(val.take(result.payment))

    labels = load_labels(training_dir)  # validation labels only are read below
    val_ids = np.array(result.request_ids)[val.rows]
    y_val = np.array([bool(labels[rid]["is_fraud"]) for rid in val_ids])

    best_if, if_records = _search_isolation_forest(x_train, x_cal, x_val, y_val)
    best_lof, lof_records = _search_lof(x_train, x_cal, x_val, y_val)
    statuses = np.array(result.context_status)
    profiles_train = result.context[tr.rows & (statuses == "ok")]
    best_db, db_records = _search_dbscan(
        profiles_train, val.take(result.context), list(statuses[val.rows]), y_val
    )

    if_val = best_if["mapping"].transform(best_if["detector"].raw_scores(x_val))
    lof_val = best_lof["mapping"].transform(best_lof["detector"].raw_scores(x_val))
    db_val = np.array([c.score for c in best_db["context"].score(val.take(result.context), list(statuses[val.rows]))])
    rules_val, families_val = rule_scores_for(result, val.rows, policy)
    unsafe_val = unsafe_mask_for(result, val.rows, policy)
    risk_val = combine_arrays(if_val, lof_val, db_val, rules_val, policy.weights)
    point, threshold_report = select_operating_point(risk_val, families_val, unsafe_val, y_val, policy)

    selection = {
        "isolation_forest": {k: best_if["record"][k] for k in ("n_estimators", "max_samples")},
        "lof": {"n_neighbors": best_lof["record"]["n_neighbors"]},
        "dbscan": {k: best_db["record"][k] for k in ("min_samples", "eps", "eps_quantile")},
    }
    metadata = {
        "model_version": _model_version(dataset, selection),
        "feature_version": FEATURE_VERSION,
        "payment_features": list(PAYMENT_FEATURES),
        "context_features": list(CONTEXT_FEATURES),
        "sklearn_version": sklearn_version(),
        "random_seed": SEED,
        "training_dataset": {
            "path": "storage/data/training",
            "seed": dataset.manifest["seed"],
            "generator_version": dataset.manifest["generator_version"],
            "file_hashes": {k: v["sha256"] for k, v in dataset.manifest["files"].items()},
        },
        "fit_rows": {
            "preprocessing": int(tr.rows.sum()),
            "isolation_forest": int(tr.rows.sum()),
            "lof": int(tr.rows.sum()),
            "dbscan": int(min(DBSCAN_FIT_ROWS, len(profiles_train))),
            "score_mapping_reference": int(cal.rows.sum()),
        },
        "selected_parameters": selection,
        "dbscan_context": {
            **best_db["context"].summary,
            "eps": best_db["context"].eps,
            "min_samples": best_db["context"].min_samples,
            "metric": best_db["context"].metric,
            "adapter": "frozen-core: within eps of a training core sample -> 0, outside -> 1, insufficient history -> 0",
        },
        "score_mapping": "empirical CDF of inverted raw scores over the unlabelled calibration period",
    }
    bundle = ModelBundle(
        preprocessor=preprocessor,
        isolation_forest=best_if["detector"],
        lof=best_lof["detector"],
        dbscan=best_db["context"],
        if_mapping=best_if["mapping"],
        lof_mapping=best_lof["mapping"],
        metadata=metadata,
    )
    report = {
        "policy_version": policy.version,
        "operating_point": {"verify": point.verify, "block": point.block, "source": point.source, "version": point.version},
        "search": {"isolation_forest": if_records, "lof": lof_records, "dbscan": db_records},
        "threshold_selection": threshold_report,
        "validation_component_average_precision": {
            "isolation_forest": _ap(y_val, if_val),
            "lof": _ap(y_val, lof_val),
            "dbscan": _ap(y_val, db_val),
            "rules": _ap(y_val, rules_val),
            "combined": _ap(y_val, risk_val),
        },
        "training_seconds": round(time.perf_counter() - started, 2),
        "evidence_store_size": len(build_evidence_store(dataset.security_events, policy).records),
    }
    bundle.save(models_dir, point, {"policy_version": policy.version, "operating_point": report["operating_point"]})
    (models_dir / "training_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
