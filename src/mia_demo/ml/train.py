"""Fit IF/novelty LOF without labels, then calibrate on unseen dates."""

from hashlib import sha256
import json

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler

from mia_demo.schemas import FEATURE_ORDER
from .bundle import ModelBundle, vector


def _matrix(rows):
    return np.vstack([vector(row["features"]) for row in rows])


def _stratified_sample(rows: list[dict], cap=20000) -> list[int]:
    if len(rows) <= cap:
        return list(range(len(rows)))
    by_day: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        by_day.setdefault(row["occurred_at"][:10], []).append(index)
    chosen = []
    for day in sorted(by_day):
        bucket = by_day[day]
        take = max(1, round(cap * len(bucket) / len(rows)))
        stride = max(1, len(bucket) // take)
        chosen.extend(bucket[::stride][:take])
    return chosen[:cap]


def train_models(train: list[dict], calibration: list[dict], peer_median_bani: int = 10000, generator_config: dict | None = None, lock_sha256: str | None = None) -> ModelBundle:
    if len(train) < 40 or len(calibration) < 10:
        raise ValueError("Need at least 40 training and 10 unseen calibration rows")
    if any(row.get("split") != "train" for row in train) or any(row.get("split") != "calibration" for row in calibration):
        raise ValueError("Chronological train/calibration split mismatch")
    train_dates = [row["occurred_at"] for row in train]
    calibration_dates = [row["occurred_at"] for row in calibration]
    if max(train_dates) >= min(calibration_dates):
        raise ValueError("Training and calibration dates overlap")
    train_raw = _matrix(train)
    calibration_raw = _matrix(calibration)
    imputer = SimpleImputer(strategy="median")
    train_imputed = imputer.fit_transform(train_raw)
    scaler = RobustScaler()
    train_scaled = scaler.fit_transform(train_imputed)
    calibration_scaled = scaler.transform(imputer.transform(calibration_raw))
    isolation_forest = IsolationForest(n_estimators=200, max_samples=min(256, len(train)), contamination="auto", random_state=42, n_jobs=1)
    isolation_forest.fit(train_scaled)
    sampled = _stratified_sample(train)
    lof = LocalOutlierFactor(n_neighbors=min(35, len(sampled) - 1), novelty=True, contamination="auto", n_jobs=1)
    lof.fit(train_scaled[sampled])
    if_reference = np.sort(-isolation_forest.score_samples(calibration_scaled))
    lof_reference = np.sort(-lof.score_samples(calibration_scaled))
    descriptor = dict(feature_order=list(FEATURE_ORDER), train_range=[min(train_dates), max(train_dates)], calibration_range=[min(calibration_dates), max(calibration_dates)], train_rows=len(train), calibration_rows=len(calibration), lof_reference_rows=len(sampled), peer_median_bani=peer_median_bani, generator_config=generator_config or {}, dependency_lock_sha256=lock_sha256, if_params={"n_estimators": 200, "max_samples": min(256, len(train)), "random_state": 42}, lof_params={"n_neighbors": min(35, len(sampled) - 1), "novelty": True}, score_meaning="0-100 anomaly ranking, not fraud probability")
    version = "model-v1-" + sha256(json.dumps(descriptor, sort_keys=True).encode()).hexdigest()[:12]
    descriptor["model_version"] = version
    return ModelBundle(imputer, scaler, isolation_forest, lof, if_reference, lof_reference, FEATURE_ORDER, peer_median_bani, version, descriptor)
