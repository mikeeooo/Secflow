"""Paths and validated runtime settings for SecFlow.

All paths are local. Environment variables may override them so that tests can use
temporary directories without touching the committed dataset or model bundle.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).resolve() if value else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return parsed


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    training_dir: Path
    demo_dir: Path
    models_dir: Path
    artifacts_dir: Path
    policy_path: Path
    autostart_stream: bool
    stream_interval_seconds: float
    batch_interval_seconds: float


def load_settings() -> Settings:
    data_dir = _env_path("SECFLOW_DATA_DIR", ROOT / "storage" / "data")
    return Settings(
        data_dir=data_dir,
        training_dir=data_dir / "training",
        demo_dir=data_dir / "demo",
        models_dir=_env_path("SECFLOW_MODELS_DIR", ROOT / "ml" / "models"),
        artifacts_dir=_env_path("SECFLOW_ARTIFACTS_DIR", ROOT / "artifacts"),
        policy_path=_env_path("SECFLOW_POLICY_PATH", ROOT / "config" / "policy.json"),
        autostart_stream=_env_bool("SECFLOW_AUTOSTART_STREAM", True),
        stream_interval_seconds=_env_float("SECFLOW_STREAM_INTERVAL", 2.0),
        batch_interval_seconds=_env_float("SECFLOW_BATCH_INTERVAL", 4.0),
    )
