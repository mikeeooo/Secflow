"""scikit-learn DBSCAN fit plus a frozen-core account-context adapter.

DBSCAN has no native online prediction. SecFlow fits DBSCAN offline on scaled trailing
24-hour account profiles from the training period, saves the core samples, and scores a
new profile with this application-level heuristic:

* profile has insufficient history               -> 0, status `insufficient_history`
* profile within `eps` of any frozen core sample  -> 0, status `within_context`
* profile beyond every core neighbourhood         -> 1, status `outside_context`

This is a context heuristic, not a fraud verdict. A model without core samples is a
training failure, not a reason to assign maximum risk.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


class EmptyCoreError(RuntimeError):
    """DBSCAN produced no core samples; parameters must be adjusted during validation."""


@dataclass(frozen=True)
class ContextResult:
    score: float
    status: str
    distance: float | None
    cluster: int | None
    nearest_cluster: int | None = None  # closest frozen cluster, also for outside-context profiles


class DBSCANContext:
    def __init__(self, eps: float, min_samples: int, metric: str = "euclidean") -> None:
        self.eps = float(eps)
        self.min_samples = int(min_samples)
        self.metric = metric
        self.scaler = StandardScaler()
        self.core_samples: np.ndarray | None = None
        self.core_labels: np.ndarray | None = None
        self.summary: dict[str, float] = {}
        self._nn: NearestNeighbors | None = None

    def fit(self, profiles: np.ndarray) -> DBSCANContext:
        scaled = self.scaler.fit_transform(profiles)
        model = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric=self.metric).fit(scaled)
        if len(model.core_sample_indices_) == 0:
            raise EmptyCoreError(f"DBSCAN(eps={self.eps:.4f}, min_samples={self.min_samples}) found no core samples")
        self.core_samples = scaled[model.core_sample_indices_]
        self.core_labels = model.labels_[model.core_sample_indices_]
        labels = model.labels_
        self.summary = {
            "fit_profiles": float(len(scaled)),
            "core_samples": float(len(self.core_samples)),
            "clusters": float(len(set(labels.tolist()) - {-1})),
            "noise_fraction": float(np.mean(labels == -1)),
        }
        self._build_index()
        return self

    def _build_index(self) -> None:
        if self.core_samples is None or len(self.core_samples) == 0:
            raise EmptyCoreError("No frozen core samples available")
        self._nn = NearestNeighbors(n_neighbors=1, metric=self.metric).fit(self.core_samples)

    def __getstate__(self) -> dict:
        state = self.__dict__.copy()
        state["_nn"] = None
        return state

    def __setstate__(self, state: dict) -> None:
        self.__dict__.update(state)
        self._build_index()

    def score(self, profiles: np.ndarray, statuses: list[str] | tuple[str, ...]) -> list[ContextResult]:
        if self._nn is None or self.core_labels is None:
            raise EmptyCoreError("DBSCAN context adapter is not fitted")
        scaled = self.scaler.transform(profiles)
        distances, indices = self._nn.kneighbors(scaled)
        results: list[ContextResult] = []
        for row, status in enumerate(statuses):
            distance = float(distances[row, 0])
            cluster = int(self.core_labels[indices[row, 0]])
            if status != "ok":
                results.append(ContextResult(0.0, "insufficient_history", None, None, cluster))
            elif distance <= self.eps:
                results.append(ContextResult(0.0, "within_context", distance, cluster, cluster))
            else:
                results.append(ContextResult(1.0, "outside_context", distance, None, cluster))
        return results
