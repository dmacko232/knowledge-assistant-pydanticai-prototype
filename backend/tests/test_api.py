"""Tests for the FastAPI presentation layer (routes, models, settings)."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings
from services.chat_history_service import ChatHistoryService
from use_cases.chat import ChatResult


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
        chat_db_path=tmp_path / "chat_history.sqlite",
    )


def _make_history_service(tmp_path: Path) -> ChatHistoryService:
    """Create a real ChatHistoryService backed by a temp DB."""
    svc = ChatHistoryService(db_path=tmp_path / "chat_history.sqlite")
    svc.connect()
    return svc


class TestHealthEndpoint:
    """Test the /health endpoint."""

    @pytest.fixture()
    def client(self, tmp_path):
        settings = _test_settings(tmp_path)
        with (
            patch("config.get_settings", return_value=settings),
            patch("config.Settings.validate_runtime"),
        ):
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
        settings = _test_settings(tmp_path)

        with (
            patch("config.get_settings", return_value=settings),
            patch("config.Settings.validate_runtime"),
        ):
            from main import app

            with TestClient(app) as c:
                # Wire up a real history service for stateful tests
                hist = _make_history_service(tmp_path)
                app.state.history = hist
                yield c
                hist.close()

    def test_chat_rejects_missing_body(self, client: TestClient):
        response = client.post("/chat")
        assert response.status_code == 422

    def test_chat_rejects_missing_user_id(self, client: TestClient):
        response = client.post("/chat", json={"message": "Hello"})
        assert response.status_code == 422

    def test_chat_returns_answer(self, client: TestClient):
        """Verify the route delegates to the use case and wraps the result."""
        mock_uc = AsyncMock()
        mock_uc.execute.return_value = ChatResult(
            answer="Grounded answer [1].\n\nSources:\n[1] doc.md",
            tool_calls=[
                {"name": "search_knowledge_base", "args": {"query": "test"}, "result": "..."}
            ],
            sources=[{"document": "doc.md", "section": "Intro", "date": "2025-01-01"}],
            latency_ms=100,
        )

        from main import app

        app.state.chat_uc = mock_uc

        response = client.post(
            "/chat",
            json={"user_id": "test-user", "message": "Hello"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Grounded answer [1].\n\nSources:\n[1] doc.md"
        assert body["chat_id"]
        assert body["message_id"]
        assert len(body["tool_calls"]) == 1
        assert len(body["sources"]) == 1
        mock_uc.execute.assert_awaited_once()


class TestChatHistoryEndpoints:
    """Test the /chats and /chats/{chat_id}/messages endpoints."""

    @pytest.fixture()
    def client(self, tmp_path):
        settings = _test_settings(tmp_path)

        with (
            patch("config.get_settings", return_value=settings),
            patch("config.Settings.validate_runtime"),
        ):
            from main import app

            with TestClient(app) as c:
                hist = _make_history_service(tmp_path)
                app.state.history = hist
                yield c
                hist.close()

    def test_list_chats_empty(self, client: TestClient):
        response = client.get("/chats?user_id=nobody")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_chats_returns_chats(self, client: TestClient):
        from main import app

        hist: ChatHistoryService = app.state.history
        user = hist.create_user("Test User")
        chat = hist.get_or_create_chat(None, user.id)
        hist.save_user_message(chat.id, "Hello")

        response = client.get(f"/chats?user_id={user.id}")
        assert response.status_code == 200
        chats = response.json()
        assert len(chats) == 1
        assert chats[0]["id"] == chat.id
        assert chats[0]["message_count"] == 1

    def test_get_chat_messages(self, client: TestClient):
        from main import app

        hist: ChatHistoryService = app.state.history
        user = hist.create_user("Test User")
        chat = hist.get_or_create_chat(None, user.id)
        hist.save_user_message(chat.id, "Hi")
        hist.save_assistant_message(chat.id, "Hello!", model="gpt-4o-mini", latency_ms=50)

        response = client.get(f"/chats/{chat.id}/messages")
        assert response.status_code == 200
        msgs = response.json()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["model"] == "gpt-4o-mini"

    def test_get_chat_messages_not_found(self, client: TestClient):
        response = client.get("/chats/nonexistent/messages")
        assert response.status_code == 404


class TestModels:
    """Test Pydantic model validation."""

    def test_chat_request_valid(self):
        from models import ChatRequest

        req = ChatRequest(user_id="user-1", message="Hello")
        assert req.message == "Hello"
        assert req.chat_id is None

    def test_chat_request_with_chat_id(self):
        from models import ChatRequest

        req = ChatRequest(user_id="user-1", message="Hello", chat_id="chat-1")
        assert req.chat_id == "chat-1"

    def test_chat_response_valid(self):
        from models import ChatResponse

        resp = ChatResponse(
            chat_id="c1",
            message_id="m1",
            answer="Answer [1].\n\nSources:\n[1] doc.md",
        )
        assert "[1]" in resp.answer
        assert resp.tool_calls == []
        assert resp.sources == []


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
        s.validate_runtime()
