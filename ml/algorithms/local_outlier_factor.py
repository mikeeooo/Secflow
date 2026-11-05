"""scikit-learn LocalOutlierFactor adapter in novelty mode.

`raw_scores` must only be called on rows that were not used for fitting (calibration,
validation, test, or live requests). Training-row diagnostics use `negative_outlier_factor_`
through `training_diagnostics`, never the novelty scoring interface.
"""

from __future__ import annotations

import numpy as np
from sklearn.neighbors import LocalOutlierFactor


class LocalOutlierFactorDetector:
    def __init__(self, n_neighbors: int) -> None:
        self.params = {"n_neighbors": n_neighbors, "novelty": True}
        self.model = LocalOutlierFactor(n_neighbors=n_neighbors, novelty=True, n_jobs=1)
        self.n_fit_rows = 0

    def fit(self, matrix: np.ndarray) -> LocalOutlierFactorDetector:
        self.model.fit(matrix)
        self.n_fit_rows = int(matrix.shape[0])
        return self

    def raw_scores(self, matrix: np.ndarray) -> np.ndarray:
        # score_samples returns the negative LOF of unseen rows; invert so higher = more anomalous.
        return -self.model.score_samples(matrix)

    def training_diagnostics(self) -> dict[str, float]:
        lof = -self.model.negative_outlier_factor_
        return {
            "fit_rows": float(self.n_fit_rows),
            "training_lof_median": float(np.median(lof)),
            "training_lof_p99": float(np.quantile(lof, 0.99)),
        }
