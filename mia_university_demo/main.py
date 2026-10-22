"""Vercel entrypoint for the integrated FastAPI service."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mia_demo.api import app  # noqa: E402
