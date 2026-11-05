"""Model bundle: frozen preprocessing, three scikit-learn detectors, and score mappings.

Loading a bundle never fits anything. Feature names, order, and feature version are
checked against the running code so that a stale bundle fails loudly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn

from ml.algorithms.dbscan_context import ContextResult, DBSCANContext
from ml.algorithms.isolation_forest import IsolationForestDetector
from ml.algorithms.local_outlier_factor import LocalOutlierFactorDetector
from ml.algorithms.preprocessing import EmpiricalScoreMapping, FeaturePreprocessor
from ml.features import CONTEXT_FEATURES, FEATURE_VERSION, PAYMENT_FEATURES, FeatureSnapshot
from ml.policy import OperatingPoint

BUNDLE_FILE = "secflow_model.joblib"
METADATA_FILE = "metadata.json"
OPERATING_POINT_FILE = "operating_point.json"


class BundleError(RuntimeError):
    """Raised when a model bundle is missing or incompatible with the running code."""


@dataclass(frozen=True)
class ModelComponents:
    if_raw: float
    if_score: float
    lof_raw: float
    lof_score: float
    context: ContextResult


@dataclass
class ModelBundle:
    preprocessor: FeaturePreprocessor
    isolation_forest: IsolationForestDetector
    lof: LocalOutlierFactorDetector
    dbscan: DBSCANContext
    if_mapping: EmpiricalScoreMapping
    lof_mapping: EmpiricalScoreMapping
    metadata: dict[str, Any]

    @property
    def version(self) -> str:
        return str(self.metadata["model_version"])

    def score_batch(
        self, payment: np.ndarray, context: np.ndarray, context_statuses: tuple[str, ...] | list[str]
    ) -> list[ModelComponents]:
        """Score already-extracted feature rows. Each detector runs exactly once per row."""
        transformed = self.preprocessor.transform(payment)
        if_raw = self.isolation_forest.raw_scores(transformed)
        lof_raw = self.lof.raw_scores(transformed)
        if_score = self.if_mapping.transform(if_raw)
        lof_score = self.lof_mapping.transform(lof_raw)
        contexts = self.dbscan.score(np.asarray(context, dtype=np.float64), context_statuses)
        return [
            ModelComponents(float(if_raw[i]), float(if_score[i]), float(lof_raw[i]), float(lof_score[i]), contexts[i])
            for i in range(len(contexts))
        ]

    def score(self, snapshot: FeatureSnapshot) -> ModelComponents:
        return self.score_batch(
            np.asarray([snapshot.payment_vector]), np.asarray([snapshot.context_vector]), [snapshot.context_status]
        )[0]

    def save(self, directory: Path, operating_point: OperatingPoint, extra: dict[str, Any]) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "preprocessor": self.preprocessor,
                "isolation_forest": self.isolation_forest,
                "lof": self.lof,
                "dbscan": self.dbscan,
                "if_mapping": self.if_mapping,
                "lof_mapping": self.lof_mapping,
                "metadata": self.metadata,
            },
            directory / BUNDLE_FILE,
            compress=3,
        )
        (directory / METADATA_FILE).write_text(json.dumps({**self.metadata, **extra}, indent=2) + "\n")
        (directory / OPERATING_POINT_FILE).write_text(
            json.dumps(
                {
                    "verify_threshold": operating_point.verify,
                    "block_threshold": operating_point.block,
                    "source": operating_point.source,
                    "version": operating_point.version,
                    "model_version": self.version,
                },
                indent=2,
            )
            + "\n"
        )


def load_bundle(directory: Path) -> ModelBundle:
    path = directory / BUNDLE_FILE
    if not path.exists():
        raise BundleError(f"Model bundle not found at {path}. Run `python -m backend.cli train`.")
    payload = joblib.load(path)
    metadata = payload["metadata"]
    if tuple(metadata["payment_features"]) != PAYMENT_FEATURES or tuple(metadata["context_features"]) != CONTEXT_FEATURES:
        raise BundleError("Model bundle feature schema does not match the running feature code")
    if metadata["feature_version"] != FEATURE_VERSION:
        raise BundleError(f"Feature version mismatch: bundle {metadata['feature_version']}, code {FEATURE_VERSION}")
    return ModelBundle(
        preprocessor=payload["preprocessor"],
        isolation_forest=payload["isolation_forest"],
        lof=payload["lof"],
        dbscan=payload["dbscan"],
        if_mapping=payload["if_mapping"],
        lof_mapping=payload["lof_mapping"],
        metadata=metadata,
    )


def load_operating_point(directory: Path, model_version: str | None) -> OperatingPoint:
    path = directory / OPERATING_POINT_FILE
    if not path.exists():
        raise BundleError(f"Operating point not found at {path}")
    raw = json.loads(path.read_text())
    if model_version is not None and raw.get("model_version") != model_version:
        raise BundleError("Operating point was selected for a different model version")
    return OperatingPoint(float(raw["verify_threshold"]), float(raw["block_threshold"]), raw["source"], raw["version"])


def sklearn_version() -> str:
    return sklearn.__version__
