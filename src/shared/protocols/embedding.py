"""Embedding service protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IEmbeddingService(Protocol):
    """Interface for text embedding services.

    Implementations: OpenAIEmbeddingService (data_pipeline),
    PydanticAI Embedder wrapper (backend), MockEmbeddingService (tests).
    """

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Generate embeddings for multiple texts in batch."""
        ...

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        ...
