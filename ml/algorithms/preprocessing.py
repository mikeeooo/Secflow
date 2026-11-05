"""Fitted feature transforms and monotonic score mappings.

Both are fitted on explicitly provided rows only: the preprocessor on the chronological
training period, the score mappings on the unlabelled calibration period.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.preprocessing import StandardScaler

CLIP_QUANTILES = (0.005, 0.995)


@dataclass
class FeaturePreprocessor:
    """Winsorise each feature at training quantiles, then standardise with scikit-learn."""

    lower: np.ndarray | None = None
    upper: np.ndarray | None = None
    scaler: StandardScaler | None = None

    def fit(self, matrix: np.ndarray) -> FeaturePreprocessor:
        self.lower = np.quantile(matrix, CLIP_QUANTILES[0], axis=0)
        self.upper = np.quantile(matrix, CLIP_QUANTILES[1], axis=0)
        self.scaler = StandardScaler().fit(np.clip(matrix, self.lower, self.upper))
        return self

    def transform(self, matrix: np.ndarray) -> np.ndarray:
        if self.scaler is None or self.lower is None or self.upper is None:
            raise RuntimeError("FeaturePreprocessor is not fitted")
        matrix = np.asarray(matrix, dtype=np.float64)
        if not np.isfinite(matrix).all():
            raise ValueError("Feature matrix contains non-finite values")
        return self.scaler.transform(np.clip(matrix, self.lower, self.upper))


@dataclass
class EmpiricalScoreMapping:
    """Map a raw anomaly score (higher = more anomalous) to its empirical CDF in [0, 1].

    The mapped value is the share of reference scores less than or equal to the input
    (`searchsorted(..., side="right") / n`). Inputs below the reference minimum map to 0,
    inputs at or above the maximum map to 1, and ties resolve deterministically.
    """

    reference: np.ndarray | None = None

    def fit(self, raw_scores: np.ndarray) -> EmpiricalScoreMapping:
        values = np.asarray(raw_scores, dtype=np.float64)
        if values.size == 0 or not np.isfinite(values).all():
            raise ValueError("Reference scores must be non-empty and finite")
        self.reference = np.sort(values)
        return self

    def transform(self, raw_scores: np.ndarray) -> np.ndarray:
        if self.reference is None:
            raise RuntimeError("EmpiricalScoreMapping is not fitted")
        values = np.asarray(raw_scores, dtype=np.float64)
        if not np.isfinite(values).all():
            raise ValueError("Raw scores must be finite")
        mapped = np.searchsorted(self.reference, values, side="right") / self.reference.size
        return np.clip(mapped, 0.0, 1.0)
