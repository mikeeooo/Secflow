"""scikit-learn IsolationForest adapter (higher raw score = more anomalous)."""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest


class IsolationForestDetector:
    def __init__(self, n_estimators: int, max_samples: int, random_state: int) -> None:
        self.params = {"n_estimators": n_estimators, "max_samples": max_samples, "random_state": random_state}
        self.model = IsolationForest(
            n_estimators=n_estimators, max_samples=max_samples, random_state=random_state, n_jobs=1
        )

    def fit(self, matrix: np.ndarray) -> IsolationForestDetector:
        self.model.fit(matrix)
        return self

    def raw_scores(self, matrix: np.ndarray) -> np.ndarray:
        # score_samples is lower for more abnormal samples; invert so higher means more anomalous.
        return -self.model.score_samples(matrix)
