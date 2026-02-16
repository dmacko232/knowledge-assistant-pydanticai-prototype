"""Shared fixtures for backend tests."""

import sys
from pathlib import Path

# Add src/backend to sys.path so imports like `from domain.infrastructure.sql_service import ...` work.
_BACKEND_SRC = str(Path(__file__).resolve().parent.parent.parent / "src" / "backend")
if _BACKEND_SRC not in sys.path:
    sys.path.insert(0, _BACKEND_SRC)

import json
import sqlite3

import pytest

from domain.infrastructure.sql_service import SQLService


def pytest_configure(config):
    """Set pytest-asyncio mode to auto so async test functions work without markers."""
    config.option.asyncio_mode = "auto"


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Create a temporary SQLite database with KPI and directory tables populated."""
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE kpi_catalog (
            id INTEGER PRIMARY KEY,
            kpi_name TEXT UNIQUE,
            definition TEXT,
            owner_team TEXT,
            primary_source TEXT,
            last_updated TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE directory (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            team TEXT,
            role TEXT,
            timezone TEXT,
            created_at TEXT
        )
    """)

    # Seed KPIs
    cursor.executemany(
        "INSERT INTO kpi_catalog (kpi_name, definition, owner_team, primary_source, last_updated) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("MRR", "Monthly Recurring Revenue", "Finance", "billing_db", "2025-06-01"),
            ("Churn Rate", "Percentage of lost subscribers", "Growth", "analytics", "2025-05-15"),
            ("NPS", "Net Promoter Score", "CX", "survey_tool", "2025-04-01"),
        ],
    )

    # Seed employees
    cursor.executemany(
        "INSERT INTO directory (name, email, team, role, timezone) VALUES (?, ?, ?, ?, ?)",
        [
            ("Alice Smith", "alice@northwind.com", "Engineering", "Staff Engineer", "US/Eastern"),
            ("Bob Jones", "bob@northwind.com", "Finance", "Analyst", "US/Central"),
            ("Carol Lee", "carol@northwind.com", "Engineering", "Manager", "US/Pacific"),
        ],
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def tmp_vector_db(tmp_path: Path) -> Path:
    """Create a temp SQLite database with document_chunks (no vec extension needed for unit tests)."""
    db_path = tmp_path / "test_vector.sqlite"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE document_chunks (
            id INTEGER PRIMARY KEY,
            chunk_id TEXT UNIQUE,
            document_name TEXT,
            category TEXT,
            section_header TEXT,
            retrieval_chunk TEXT,
            generation_chunk TEXT,
            last_updated TEXT,
            word_count INTEGER DEFAULT 0,
            chunk_metadata TEXT DEFAULT '{}',
            created_at TEXT
        )
    """)

    # Seed some chunks
    chunks = [
        (
            "chunk_1",
            "security_policy_v2.md",
            "policies",
            "Access Controls",
            "retrieval text 1",
            "Security policy requires MFA for all production access.",
            "2026-01-15",
            20,
            json.dumps({"version": "v2"}),
        ),
        (
            "chunk_2",
            "security_policy_v1.md",
            "policies",
            "Access Controls",
            "retrieval text 2",
            "Production access requires VPN only.",
            "2025-06-01",
            15,
            json.dumps({"version": "v1"}),
        ),
        (
            "chunk_3",
            "kpi_overview.md",
            "domain",
            "KPI Definitions",
            "retrieval text 3",
            "MRR is calculated as total monthly subscriptions.",
            "2025-09-01",
            18,
            json.dumps({}),
        ),
    ]
    cursor.executemany(
        "INSERT INTO document_chunks "
        "(chunk_id, document_name, category, section_header, retrieval_chunk, "
        "generation_chunk, last_updated, word_count, chunk_metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        chunks,
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def sql_service(tmp_db: Path) -> SQLService:
    """A SQLService connected to the temporary database."""
    svc = SQLService(db_path=tmp_db)
    svc.connect()
    yield svc
    svc.close()
