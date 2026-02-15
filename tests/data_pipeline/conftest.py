"""Pytest configuration and fixtures for data pipeline tests."""

import sys
import tempfile
from pathlib import Path

import pytest

# Add src/data_pipeline to sys.path so imports like `from database.models import ...` work.
_DP_SRC = str(Path(__file__).resolve().parent.parent.parent / "src" / "data_pipeline")
if _DP_SRC not in sys.path:
    sys.path.insert(0, _DP_SRC)


@pytest.fixture
def temp_db_path():
    """Provide a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def temp_dir():
    """Provide a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
