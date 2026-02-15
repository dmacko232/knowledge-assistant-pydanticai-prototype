"""Unit tests for EmbeddingService."""

from unittest.mock import Mock

import pytest

from services.embedding_service import OpenAIEmbeddingService


class TestOpenAIEmbeddingService:
    """Test suite for OpenAIEmbeddingService."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage = Mock(total_tokens=100)
        mock_client.embeddings.create.return_value = mock_response
        return mock_client

    def test_initialization(self):
        """Test service initialization."""
        service = OpenAIEmbeddingService(
            api_key="test_key", endpoint="https://test.openai.azure.com/"
        )
        assert service.deployment_name is not None
        assert service.dimension == 1536

    def test_embed_text(self, mock_openai_client):
        """Test embedding a single text."""
        service = OpenAIEmbeddingService(
            api_key="test_key", endpoint="https://test.openai.azure.com/"
        )
        service.client = mock_openai_client

        result = service.embed_text("test text")

        assert isinstance(result, list)
        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
        mock_openai_client.embeddings.create.assert_called_once()

    def test_embed_batch(self, mock_openai_client):
        """Test embedding multiple texts in batch."""
        # Mock response for batch
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
            Mock(embedding=[0.3] * 1536),
        ]
        mock_response.usage = Mock(total_tokens=300)
        mock_openai_client.embeddings.create.return_value = mock_response

        service = OpenAIEmbeddingService(
            api_key="test_key", endpoint="https://test.openai.azure.com/"
        )
        service.client = mock_openai_client

        texts = ["text 1", "text 2", "text 3"]
        result = service.embed_batch(texts)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(len(emb) == 1536 for emb in result)
        mock_openai_client.embeddings.create.assert_called_once()

    def test_embed_batch_with_batching(self, mock_openai_client):
        """Test that large batches are split into smaller batches."""
        # Mock response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536) for _ in range(50)]
        mock_response.usage = Mock(total_tokens=1000)
        mock_openai_client.embeddings.create.return_value = mock_response

        service = OpenAIEmbeddingService(
            api_key="test_key", endpoint="https://test.openai.azure.com/"
        )
        service.client = mock_openai_client

        # Create 150 texts (should be split into 2 batches of 100 and 50)
        texts = [f"text {i}" for i in range(150)]
        _ = service.embed_batch(texts, batch_size=100)

        # Should make 2 API calls
        assert mock_openai_client.embeddings.create.call_count == 2

    def test_dimension_property(self):
        """Test dimension property."""
        service = OpenAIEmbeddingService(
            dimensions=512, api_key="test_key", endpoint="https://test.openai.azure.com/"
        )
        assert service.dimension == 512

    def test_custom_deployment(self):
        """Test using custom deployment."""
        service = OpenAIEmbeddingService(
            deployment_name="text-embedding-ada-002",
            api_key="test_key",
            endpoint="https://test.openai.azure.com/",
        )
        assert service.deployment_name == "text-embedding-ada-002"

    def test_implements_interface(self):
        """Test that OpenAIEmbeddingService implements IEmbeddingService protocol."""
        service = OpenAIEmbeddingService(
            api_key="test_key", endpoint="https://test.openai.azure.com/"
        )

        # Check that it has required methods
        assert hasattr(service, "embed_text")
        assert hasattr(service, "embed_batch")
        assert hasattr(service, "dimension")
        assert callable(service.embed_text)
        assert callable(service.embed_batch)


class MockEmbeddingService:
    """Mock embedding service for testing."""

    def __init__(self, dimension: int = 128):
        self._dimension = dimension

    def embed_text(self, text: str) -> list[float]:
        """Return mock embedding."""
        return [0.1] * self._dimension

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Return mock embeddings for batch."""
        return [[0.1] * self._dimension for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


class TestMockEmbeddingService:
    """Test that mock service can be used as IEmbeddingService."""

    def test_mock_service_implements_interface(self):
        """Test that mock service implements the interface."""
        service = MockEmbeddingService()

        # Should have all required methods
        assert hasattr(service, "embed_text")
        assert hasattr(service, "embed_batch")
        assert hasattr(service, "dimension")

    def test_mock_service_embed_text(self):
        """Test mock service embed_text."""
        service = MockEmbeddingService(dimension=64)
        result = service.embed_text("test")

        assert len(result) == 64
        assert all(isinstance(x, float) for x in result)

    def test_mock_service_embed_batch(self):
        """Test mock service embed_batch."""
        service = MockEmbeddingService(dimension=64)
        texts = ["text1", "text2", "text3"]
        result = service.embed_batch(texts)

        assert len(result) == 3
        assert all(len(emb) == 64 for emb in result)

    def test_mock_service_dimension(self):
        """Test mock service dimension property."""
        service = MockEmbeddingService(dimension=256)
        assert service.dimension == 256
