"""Retrieval service protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class RetrievalResult:
    """A single retrieval result with source metadata."""

    chunk_id: str
    document_name: str
    category: str
    section_header: str | None
    generation_chunk: str
    last_updated: str | None
    score: float
    chunk_metadata: dict = field(default_factory=dict)


@runtime_checkable
class IRetrievalService(Protocol):
    """Interface for knowledge base retrieval.

    Implementations: RetrievalService (hybrid vector + BM25 search).
    """

    def search(
        self,
        query: str,
        category: str | None = None,
        vector_limit: int = 10,
        bm25_limit: int = 10,
        final_limit: int = 5,
        rrf_k: int = 60,
    ) -> list[RetrievalResult]:
        """Run a search and return ranked results."""
        ...

    def connect(self) -> None:
        """Open database connection and load extensions."""
        ...

    def close(self) -> None:
        """Close the database connection."""
        ...
