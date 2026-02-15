"""Protocol interfaces for vector and relational stores."""

from typing import Protocol

from database.models import ChunkEmbedding, DocumentChunk, Employee, KPICatalog, SearchResult


class VectorStoreInterface(Protocol):
    """Interface for vector storage and search (chunks, embeddings, FTS)."""

    def connect(self) -> None:
        """Connect to database and load extensions."""
        ...

    def close(self) -> None:
        """Close database connection."""
        ...

    def create_tables(self) -> None:
        """Create tables for document chunks with vector and FTS5 support."""
        ...

    def insert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[ChunkEmbedding],
        fts_contents: list[str],
    ) -> None:
        """Insert document chunks with embeddings and FTS content."""
        ...

    def search_by_vector(
        self,
        query_embedding: list[float],
        limit: int = 10,
        category_filter: str | None = None,
    ) -> list[SearchResult]:
        """Search chunks by vector similarity."""
        ...

    def search_by_bm25(
        self,
        query: str,
        limit: int = 10,
        category_filter: str | None = None,
    ) -> list[SearchResult]:
        """Search chunks using BM25 (FTS5 full-text search)."""
        ...

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        ...

    def reset(self) -> None:
        """Drop all vector-store tables (use with caution)."""
        ...


class RelationalStoreInterface(Protocol):
    """Interface for relational storage (KPI catalog, employee directory)."""

    def connect(self) -> None:
        """Connect to database."""
        ...

    def close(self) -> None:
        """Close database connection."""
        ...

    def create_tables(self) -> None:
        """Create KPI and directory tables."""
        ...

    def insert_kpis(self, kpis: list[KPICatalog]) -> None:
        """Insert or update KPIs (upsert by kpi_name)."""
        ...

    def insert_employees(self, employees: list[Employee]) -> None:
        """Insert or update employees (upsert by email)."""
        ...

    def query_kpi_by_name(self, name: str) -> KPICatalog | None:
        """Get KPI by name."""
        ...

    def query_employee_by_email(self, email: str) -> Employee | None:
        """Get employee by email."""
        ...

    def query_kpis_by_owner(self, owner_team: str) -> list[KPICatalog]:
        """Get all KPIs for an owner team."""
        ...

    def query_employees_by_team(self, team: str) -> list[Employee]:
        """Get all employees in a team."""
        ...

    def get_all_teams(self) -> list[str]:
        """Get distinct team names from directory."""
        ...

    def get_stats(self) -> dict:
        """Get counts and breakdowns."""
        ...

    def reset(self) -> None:
        """Drop KPI and directory tables."""
        ...
