"""SQL service protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ISQLService(Protocol):
    """Interface for read-only SQL query execution.

    Implementations: SQLService (SQLite-backed).
    """

    def execute_query(self, sql: str) -> str:
        """Execute a read-only SQL query and return formatted results."""
        ...

    def connect(self) -> None:
        """Open the database connection."""
        ...

    def close(self) -> None:
        """Close the database connection."""
        ...

    @staticmethod
    def get_schemas() -> str:
        """Return table schemas the LLM can reference."""
        ...
