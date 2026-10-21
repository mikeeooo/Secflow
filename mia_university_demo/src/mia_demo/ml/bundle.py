"""Trusted local artifact containing preprocessing, estimators and calibration."""

from dataclasses import dataclass
from pathlib import Path
import json

import joblib
import numpy as np

from mia_demo.schemas import FEATURE_ORDER, FeatureRow


LOG_COLUMNS = {"amount_to_sender_median_30d", "outgoing_attempts_5m", "outgoing_attempts_1h", "outgoing_amount_1h", "unique_recipients_24h", "account_age_days", "seconds_since_last_attempt", "incoming_amount_1h", "unique_senders_1h", "amount_to_recent_inflow", "history_count_30d"}


def vector(features: FeatureRow | dict, feature_order=FEATURE_ORDER) -> np.ndarray:
    values = features.model_dump() if isinstance(features, FeatureRow) else features
    if set(values) != set(feature_order):
        raise ValueError("Feature schema mismatch")
    return np.asarray([np.log1p(max(0, values[name])) if name in LOG_COLUMNS else values[name] for name in feature_order], dtype=float)


@dataclass
class ModelBundle:
    imputer: object
    scaler: object
    isolation_forest: object
    lof: object
    if_reference: np.ndarray
    lof_reference: np.ndarray
    feature_order: tuple[str, ...]
    peer_median_bani: int
    version: str
    metadata: dict

    def score(self, features: FeatureRow | dict) -> dict[str, float]:
        row = vector(features, self.feature_order).reshape(1, -1)
        transformed = self.scaler.transform(self.imputer.transform(row))
        if_raw = float(-self.isolation_forest.score_samples(transformed)[0])
        lof_raw = float(-self.lof.score_samples(transformed)[0])
        return {
            "if_percentile": float(np.searchsorted(self.if_reference, if_raw, side="right") / len(self.if_reference)),
            "lof_percentile": float(np.searchsorted(self.lof_reference, lof_raw, side="right") / len(self.lof_reference)),
        }


def save_bundle(bundle: ModelBundle, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    path.with_suffix(".json").write_text(json.dumps(bundle.metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def load_bundle(path: str | Path) -> ModelBundle:
    """Load only this project's locally generated trusted artifact."""
    bundle = joblib.load(path)
    if tuple(bundle.feature_order) != FEATURE_ORDER:
        raise ValueError("Feature schema mismatch in model artifact")
    return bundle
