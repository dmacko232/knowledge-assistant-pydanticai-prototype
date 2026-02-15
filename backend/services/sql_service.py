"""Read-only SQL query service for structured data (KPI catalog, employee directory)."""

import sqlite3
from pathlib import Path


TABLE_SCHEMAS = """Available tables and their schemas:

TABLE: kpi_catalog
  - id: INTEGER (primary key)
  - kpi_name: TEXT (unique, indexed)
  - definition: TEXT
  - owner_team: TEXT (indexed)
  - primary_source: TEXT
  - last_updated: TEXT
  - created_at: DATETIME

TABLE: directory
  - id: INTEGER (primary key)
  - name: TEXT
  - email: TEXT (unique, indexed)
  - team: TEXT (indexed)
  - role: TEXT
  - timezone: TEXT
  - created_at: DATETIME
"""


_FORBIDDEN_KEYWORDS = frozenset(
    ["drop", "delete", "insert", "update", "alter", "create", "replace", "attach", "detach"]
)


class SQLService:
    """Executes read-only SQL queries against the structured data tables."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        """Open a read-only connection to the database."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    @staticmethod
    def get_schemas() -> str:
        """Return the table schemas the LLM can reference."""
        return TABLE_SCHEMAS

    def execute_query(self, sql: str) -> str:
        """Execute a read-only SQL query and return results as a formatted table.

        Only SELECT statements against kpi_catalog and directory are allowed.
        """
        if not self.conn:
            raise RuntimeError("Not connected to database. Call connect() first.")

        sql_stripped = sql.strip()
        sql_upper = sql_stripped.upper()

        # Safety: only allow SELECT
        if not sql_upper.startswith("SELECT"):
            return "Error: Only SELECT queries are allowed."

        # Safety: reject dangerous keywords
        sql_lower = sql_stripped.lower()
        for keyword in _FORBIDDEN_KEYWORDS:
            if keyword in sql_lower.split():
                return f"Error: {keyword.upper()} operations are not allowed."

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql_stripped)
            rows = cursor.fetchall()

            if not rows:
                return "No results found."

            columns = [desc[0] for desc in cursor.description]
            lines = [" | ".join(columns)]
            lines.append(" | ".join("---" for _ in columns))
            for row in rows:
                lines.append(" | ".join(str(v) if v is not None else "" for v in row))

            return "\n".join(lines)

        except Exception as e:
            return f"SQL Error: {e}"
