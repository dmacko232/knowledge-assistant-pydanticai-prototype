"""Embedding service with interface and Azure OpenAI implementation."""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from openai import AzureOpenAI

import config


@runtime_checkable
class IEmbeddingService(Protocol):
    """Interface for embedding service."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of input texts to embed
            batch_size: Maximum batch size for API calls (default: 100)

        Returns:
            List of embedding vectors
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        ...


class OpenAIEmbeddingService:
    """Azure OpenAI implementation of embedding service."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        api_version: str | None = None,
        deployment_name: str | None = None,
        dimensions: int = config.EMBEDDING_DIMENSIONS,
    ):
        """
        Initialize Azure OpenAI embedding service.

        Args:
            api_key: Azure OpenAI API key (uses config if not provided)
            endpoint: Azure OpenAI endpoint (uses config if not provided)
            api_version: API version (uses config if not provided)
            deployment_name: Deployment name (uses config if not provided)
            dimensions: Embedding dimensions
        """
        # Use embedding-specific config (endpoint, version, deployment, key) when not passed in
        azure_endpoint = endpoint or config.AZURE_OPENAI_EMBEDDING_ENDPOINT
        if not azure_endpoint:
            raise ValueError(
                "Azure OpenAI embedding endpoint not set. Set AZURE_OPENAI_EMBEDDING_ENDPOINT or AZURE_OPENAI_ENDPOINT in .env"
            )

        self.client = AzureOpenAI(
            api_key=api_key or config.AZURE_OPENAI_EMBEDDING_API_KEY,
            azure_endpoint=azure_endpoint,
            api_version=api_version or config.AZURE_OPENAI_EMBEDDING_API_VERSION,
        )
        self.deployment_name = deployment_name or config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        self._dimensions = dimensions

    def _to_float_list(self, embedding: list[float]) -> list[float]:
        """Ensure embedding is a plain list of Python floats (for sqlite-vec serialize_float32)."""
        return [float(x) for x in embedding]

    def _create_kwargs(self) -> dict:
        """Build kwargs for embeddings.create."""
        # text-embedding-3-* support dimensions; request our configured size for DB compatibility
        return {"model": self.deployment_name, "dimensions": self._dimensions}

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        kwargs = self._create_kwargs()
        kwargs["input"] = text
        response = self.client.embeddings.create(**kwargs)
        return self._to_float_list(response.data[0].embedding)

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of input texts to embed
            batch_size: Maximum batch size for API calls

        Returns:
            List of embedding vectors (plain list[float] for each)
        """
        all_embeddings = []

        # Process in batches to avoid API limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            kwargs = self._create_kwargs()
            kwargs["input"] = batch
            response = self.client.embeddings.create(**kwargs)
            for item in response.data:
                all_embeddings.append(self._to_float_list(item.embedding))

        return all_embeddings

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimensions


class MockEmbeddingService:
    """Mock embedding service for local dev (no API calls). Uses config.EMBEDDING_DIMENSIONS."""

    def __init__(self, dimension: int | None = None):
        self._dimension = dimension if dimension is not None else config.EMBEDDING_DIMENSIONS

    def embed_text(self, text: str) -> list[float]:
        return [0.1] * self._dimension

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        return [[0.1] * self._dimension for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dimension
