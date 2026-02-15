"""Tests for the FastAPI presentation layer (routes, models, settings)."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings


def _test_settings(tmp_path: Path) -> Settings:
    """Create a Settings instance suitable for tests.

    Uses ``_env_file=None`` so the real backend/.env is never loaded.
    """
    return Settings(
        _env_file=None,
        azure_openai_api_key="test-key",
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_version="2024-02-01",
        azure_openai_chat_deployment="gpt-4o-mini",
        azure_openai_embedding_endpoint="https://test.openai.azure.com/",
        azure_openai_embedding_api_version="2024-02-01",
        azure_openai_embedding_deployment="text-embedding-3-small",
        azure_openai_embedding_api_key="test-key",
        embedding_dimensions=1536,
        reranker_enabled=False,
        db_path=tmp_path / "test.sqlite",
    )


class TestHealthEndpoint:
    """Test the /health endpoint."""

    @pytest.fixture()
    def client(self, tmp_path):
        """Create a test client with mocked dependencies."""
        settings = _test_settings(tmp_path)

        with patch("config.get_settings", return_value=settings), \
             patch("config.Settings.validate_runtime"):
            from main import app

            with TestClient(app) as c:
                yield c

    def test_health_returns_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestChatEndpoint:
    """Test the /chat endpoint — HTTP-level concerns only.

    Business logic is tested in test_chat_use_case.py.
    """

    @pytest.fixture()
    def client(self, tmp_path):
        """Create a test client with mocked dependencies."""
        settings = _test_settings(tmp_path)

        with patch("config.get_settings", return_value=settings), \
             patch("config.Settings.validate_runtime"):
            from main import app

            with TestClient(app) as c:
                yield c

    def test_chat_rejects_empty_messages(self, client: TestClient):
        response = client.post("/chat", json={"messages": []})
        assert response.status_code == 422

    def test_chat_rejects_missing_body(self, client: TestClient):
        response = client.post("/chat")
        assert response.status_code == 422

    def test_chat_returns_answer(self, client: TestClient):
        """Verify the route delegates to the use case and wraps the result."""
        mock_uc = AsyncMock()
        mock_uc.execute.return_value = "Grounded answer [1].\n\nSources:\n[1] doc.md"

        from main import app
        app.state.chat = mock_uc

        response = client.post(
            "/chat",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )
        assert response.status_code == 200
        assert response.json()["answer"] == "Grounded answer [1].\n\nSources:\n[1] doc.md"
        mock_uc.execute.assert_awaited_once()


class TestModels:
    """Test Pydantic model validation."""

    def test_chat_request_valid(self):
        from models import ChatRequest

        req = ChatRequest(messages=[{"role": "user", "content": "Hello"}])
        assert len(req.messages) == 1
        assert req.messages[0].role == "user"

    def test_chat_response_valid(self):
        from models import ChatResponse

        resp = ChatResponse(answer="This is the answer [1].\n\nSources:\n[1] doc.md")
        assert "[1]" in resp.answer


class TestSettings:
    """Test the pydantic-settings Settings class."""

    def test_defaults(self):
        s = Settings(
            _env_file=None,
            azure_openai_api_key="k",
            azure_openai_endpoint="https://ep.openai.azure.com/",
        )
        assert s.azure_openai_chat_deployment == "gpt-4o-mini"
        assert s.vector_search_limit == 10
        assert s.rrf_k == 60
        assert s.reranker_enabled is False

    def test_embedding_falls_back_to_chat(self):
        s = Settings(
            _env_file=None,
            azure_openai_api_key="k",
            azure_openai_endpoint="https://ep.openai.azure.com/",
            azure_openai_api_version="2025-01-01",
        )
        assert s.azure_openai_embedding_endpoint == "https://ep.openai.azure.com/"
        assert s.azure_openai_embedding_api_version == "2025-01-01"
        assert s.azure_openai_embedding_api_key == "k"

    def test_embedding_override(self):
        s = Settings(
            _env_file=None,
            azure_openai_api_key="k",
            azure_openai_endpoint="https://ep.openai.azure.com/",
            azure_openai_embedding_endpoint="https://embed.openai.azure.com/",
            azure_openai_embedding_api_key="embed-key",
        )
        assert s.azure_openai_embedding_endpoint == "https://embed.openai.azure.com/"
        assert s.azure_openai_embedding_api_key == "embed-key"

    def test_validate_runtime_missing_key(self, tmp_path):
        s = Settings(
            _env_file=None,
            azure_openai_api_key="",
            azure_openai_endpoint="https://ep.openai.azure.com/",
            db_path=tmp_path / "test.sqlite",
        )
        with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY"):
            s.validate_runtime()

    def test_validate_runtime_missing_db(self, tmp_path):
        s = Settings(
            _env_file=None,
            azure_openai_api_key="k",
            azure_openai_endpoint="https://ep.openai.azure.com/",
            db_path=tmp_path / "nonexistent.sqlite",
        )
        with pytest.raises(FileNotFoundError, match="Run the data pipeline"):
            s.validate_runtime()

    def test_validate_runtime_reranker_enabled_no_key(self, tmp_path):
        db = tmp_path / "test.sqlite"
        db.touch()
        s = Settings(
            _env_file=None,
            azure_openai_api_key="k",
            azure_openai_endpoint="https://ep.openai.azure.com/",
            db_path=db,
            reranker_enabled=True,
            reranker_api_key=None,
        )
        with pytest.raises(ValueError, match="RERANKER_API_KEY"):
            s.validate_runtime()

    def test_validate_runtime_ok(self, tmp_path):
        db = tmp_path / "test.sqlite"
        db.touch()
        s = Settings(
            _env_file=None,
            azure_openai_api_key="k",
            azure_openai_endpoint="https://ep.openai.azure.com/",
            db_path=db,
        )
        s.validate_runtime()  # should not raise
