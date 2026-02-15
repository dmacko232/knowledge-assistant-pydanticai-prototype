"""SQLModel type definitions for database tables."""

from datetime import UTC, datetime

from sqlmodel import JSON, Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class KPICatalog(SQLModel, table=True):
    """KPI catalog table model."""

    __tablename__ = "kpi_catalog"

    id: int | None = Field(default=None, primary_key=True)
    kpi_name: str = Field(index=True, unique=True)
    definition: str
    owner_team: str = Field(index=True)
    primary_source: str
    last_updated: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class Employee(SQLModel, table=True):
    """Employee directory table model."""

    __tablename__ = "directory"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    team: str = Field(index=True)
    role: str
    timezone: str
    created_at: datetime = Field(default_factory=_utcnow)


class DocumentChunk(SQLModel, table=True):
    """Document chunk table model."""

    __tablename__ = "document_chunks"

    id: int | None = Field(default=None, primary_key=True)
    chunk_id: str = Field(unique=True, index=True)
    document_name: str = Field(index=True)
    category: str = Field(index=True)
    section_header: str | None = None
    retrieval_chunk: str
    generation_chunk: str
    last_updated: str | None = None
    word_count: int = Field(default=0)
    chunk_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utcnow)


class SearchResult(SQLModel):
    """Document chunk with search scores (not a table, used for search results)."""

    id: int | None = None
    chunk_id: str
    document_name: str
    category: str
    section_header: str | None = None
    retrieval_chunk: str
    generation_chunk: str
    last_updated: str | None = None
    word_count: int = 0
    chunk_metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    # Search scores
    distance: float | None = None
    score: float | None = None
    bm25_score: float | None = None


class ChunkEmbedding(SQLModel):
    """Embedding data for a chunk (not a table, used for vector operations)."""

    chunk_id: str
    embedding: list[float]


class ChunkFTS(SQLModel):
    """FTS5 data for a chunk (not a table, used for full-text search)."""

    chunk_id: str
    document_name: str
    category: str
    section_header: str | None
    content: str
