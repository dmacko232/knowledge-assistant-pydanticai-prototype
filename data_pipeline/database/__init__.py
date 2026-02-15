"""Database layer: vector store (sqlite-vec + FTS5) and relational store."""

from database.interfaces import RelationalStoreInterface, VectorStoreInterface
from database.models import (
    ChunkEmbedding,
    DocumentChunk,
    Employee,
    KPICatalog,
    SearchResult,
)
from database.relational_store import RelationalStore
from database.vector_store import VectorStore

__all__ = [
    "ChunkEmbedding",
    "DocumentChunk",
    "Employee",
    "KPICatalog",
    "RelationalStore",
    "RelationalStoreInterface",
    "SearchResult",
    "VectorStore",
    "VectorStoreInterface",
]
