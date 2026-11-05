"""Shared fixtures. Generated datasets are written to temporary directories so tests never
modify the committed data or model bundle."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SECFLOW_AUTOSTART_STREAM", "false")

from storage.generator import DEMO_SPEC, TRAINING_SPEC, generate_dataset

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def generated(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    base = tmp_path_factory.mktemp("datasets")
    paths = {}
    for spec in (TRAINING_SPEC, DEMO_SPEC):
        generate_dataset(base / spec.name, spec)
        paths[spec.name] = base / spec.name
    return paths
