"""Daily, independent DBSCAN account behavior findings."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json

import joblib
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import RobustScaler

from mia_demo.features.accounts import build_account_snapshot
from mia_demo.schemas import AccountSnapshot
from mia_demo.simulation.generator import START
from mia_demo.storage import MemoryHistory


def _vector(row: AccountSnapshot) -> list[float]:
    return [np.log1p(row.incoming_amount_24h), np.log1p(row.outgoing_amount_24h), np.log1p(row.unique_senders_24h), np.log1p(row.unique_recipients_24h), min(20, row.outgoing_to_incoming), row.no_incoming, row.rapid_outflow_share]


@dataclass
class ClusterReference:
    scaler: RobustScaler
    eps: float
    min_samples: int
    version: str
    metadata: dict


def fit_cluster_reference(training: list[AccountSnapshot], validation: list[AccountSnapshot], min_samples: int = 10) -> ClusterReference:
    if not training or not validation:
        raise ValueError("Need training and validation account snapshots")
    scaler = RobustScaler().fit(np.asarray([_vector(row) for row in training]))
    validation_matrix = scaler.transform(np.asarray([_vector(row) for row in validation]))
    neighbors = min(min_samples, len(validation_matrix))
    if neighbors < 2:
        eps = 0.5
    else:
        distances = NearestNeighbors(n_neighbors=neighbors).fit(validation_matrix).kneighbors(validation_matrix)[0][:, -1]
        eps = max(0.5, float(np.quantile(distances, 0.9)))
    metadata = dict(min_samples=min_samples, eps=eps, training_rows=len(training), validation_rows=len(validation), eps_method="90th percentile of validation k-distances; floor 0.5", feature_order=["log_incoming", "log_outgoing", "log_unique_senders", "log_unique_recipients", "outgoing_to_incoming_clipped_20", "no_incoming", "rapid_outflow_share"])
    version = "cluster-v1-" + sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()[:12]
    metadata["version"] = version
    return ClusterReference(scaler, eps, min_samples, version, metadata)


def run_clustering(snapshots: list[AccountSnapshot], reference: ClusterReference, max_rows: int = 2000) -> list[dict]:
    if len(snapshots) > max_rows:
        raise ValueError("DBSCAN batch exceeds local memory bound")
    if not snapshots:
        return []
    if len({row.window_end for row in snapshots}) != 1:
        raise ValueError("One daily window per DBSCAN fit")
    if len(snapshots) < reference.min_samples:
        labels = np.full(len(snapshots), -1)
    else:
        matrix = reference.scaler.transform(np.asarray([_vector(row) for row in snapshots]))
        labels = DBSCAN(eps=reference.eps, min_samples=reference.min_samples).fit_predict(matrix)
    findings = []
    for row, label in zip(snapshots, labels):
        flags = []
        if row.unique_senders_24h >= 5:
            flags.append("MANY_SENDERS")
        if row.rapid_outflow_share >= 0.5 and row.outgoing_amount_24h >= 500:
            flags.append("RAPID_FLOW_THROUGH")
        if row.local_cycle_24h:
            flags.append("LOCAL_CYCLE")
        findings.append(dict(run_id=f"{reference.version}-{row.window_end.date()}", local_account_id=row.account_id, window_end=row.window_end, available_at=row.window_end + timedelta(minutes=5), cluster_label=int(label), noise_flag=bool(label == -1), contextual_rule_flags=flags))
    return findings


def daily_snapshots(dataset, days: range | list[int]) -> dict[int, list[AccountSnapshot]]:
    accounts = {account_id: dict(opened_at=datetime.fromisoformat(data["opened_at"]), balance_bani=data["initial_balance_bani"]) for account_id, data in dataset.accounts.items()}
    history = MemoryHistory(accounts)
    for event in dataset.events:
        history.add_event(event)
    result = {}
    for day in days:
        end = START + timedelta(days=day)
        snapshots = [build_account_snapshot(account_id, end, history) for account_id in accounts]
        result[day] = [row for row in snapshots if row.incoming_amount_24h > 0 or row.outgoing_amount_24h > 0]
    return result


def save_reference(reference: ClusterReference, path):
    joblib.dump(reference, path)


def load_reference(path) -> ClusterReference:
    return joblib.load(path)
