"""Tests for the FastAPI presentation layer (routes, models, settings)."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from application.use_cases.chat import ChatResult
from config import Settings
from domain.infrastructure.chat_history_service import ChatHistoryService


def _test_settings(tmp_path: Path) -> Settings:
    """Create a Settings instance suitable for tests.

    Uses ``_env_file=None`` so the real backend/.env is never loaded.
    Auth is disabled so the mock user is returned instead of requiring JWT.
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
        auth_enabled=False,
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


class TestAuthEndpoint:
    """Test the /auth/login endpoint."""

    @pytest.fixture()
    def client_open(self, tmp_path):
        """Client with open registration enabled."""
        settings = _test_settings(tmp_path)
        settings.open_registration = True
        with (
            patch("config.get_settings", return_value=settings),
            patch("config.Settings.validate_runtime"),
        ):
            from main import app

            with TestClient(app) as c:
                hist = _make_history_service(tmp_path)
                app.state.settings = settings
                app.state.history = hist
                yield c
                hist.close()

    @pytest.fixture()
    def client_closed(self, tmp_path):
        """Client with open registration disabled (default)."""
        settings = _test_settings(tmp_path)
        settings.open_registration = False
        with (
            patch("config.get_settings", return_value=settings),
            patch("config.Settings.validate_runtime"),
        ):
            from main import app

            with TestClient(app) as c:
                hist = _make_history_service(tmp_path)
                # Seed a registered user
                hist.seed_users([{"name": "Alice", "email": "alice@northwind.com"}])
                app.state.settings = settings
                app.state.history = hist
                yield c
                hist.close()

    def test_login_returns_token(self, client_open: TestClient):
        response = client_open.post(
            "/auth/login", json={"name": "Alice", "email": "alice@northwind.com"}
        )
        assert response.status_code == 200
        body = response.json()
        assert "token" in body
        assert body["name"] == "Alice"
        assert body["user_id"]

    def test_login_same_email_returns_same_user(self, client_open: TestClient):
        r1 = client_open.post("/auth/login", json={"name": "Alice", "email": "alice@northwind.com"})
        r2 = client_open.post("/auth/login", json={"name": "Alice", "email": "alice@northwind.com"})
        assert r1.json()["user_id"] == r2.json()["user_id"]

    def test_registered_user_can_login(self, client_closed: TestClient):
        response = client_closed.post(
            "/auth/login", json={"email": "alice@northwind.com"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Alice"
        assert "token" in body

    def test_unregistered_user_rejected(self, client_closed: TestClient):
        response = client_closed.post(
            "/auth/login", json={"email": "unknown@evil.com"}
        )
        assert response.status_code == 401
        assert "No account found" in response.json()["detail"]


class TestChatEndpoint:
    """Test the /chat endpoint — HTTP-level concerns only.

    Business logic is tested in test_chat_use_case.py.
    Auth is disabled so a mock user (dev-user) is injected automatically.
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
                hist = _make_history_service(tmp_path)
                app.state.history = hist
                yield c
                hist.close()

    def test_chat_rejects_missing_body(self, client: TestClient):
        response = client.post("/chat")
        assert response.status_code == 422

    def test_chat_rejects_missing_message(self, client: TestClient):
        response = client.post("/chat", json={})
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
            json={"message": "Hello"},
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
    """Test the /chats and /chats/{chat_id}/messages endpoints.

    Auth is disabled — user_id comes from the mock user (dev-user).
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
                hist = _make_history_service(tmp_path)
                app.state.history = hist
                yield c
                hist.close()

    def test_list_chats_empty(self, client: TestClient):
        response = client.get("/chats")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_chats_returns_chats(self, client: TestClient):
        from main import app

        hist: ChatHistoryService = app.state.history
        # "dev-user" is the mock user_id when auth is disabled
        chat = hist.get_or_create_chat(None, "dev-user")
        hist.save_user_message(chat.id, "Hello")

        response = client.get("/chats")
        assert response.status_code == 200
        chats = response.json()
        assert len(chats) == 1
        assert chats[0]["id"] == chat.id
        assert chats[0]["message_count"] == 1

    def test_get_chat_messages(self, client: TestClient):
        from main import app

        hist: ChatHistoryService = app.state.history
        chat = hist.get_or_create_chat(None, "dev-user")
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


class TestTitleEndpoint:
    """Test the POST /chats/{chat_id}/title endpoint."""

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

    def test_title_returns_404_for_unknown_chat(self, client: TestClient):
        response = client.post("/chats/nonexistent/title")
        assert response.status_code == 404

    def test_title_generates_and_persists(self, client: TestClient):
        """Mock the title agent and verify the endpoint generates + stores a title."""
        from main import app

        hist: ChatHistoryService = app.state.history
        chat = hist.get_or_create_chat(None, "dev-user")
        hist.save_user_message(chat.id, "How do I deploy to production?")
        hist.save_assistant_message(chat.id, "Here are the steps to deploy...")

        mock_agent = AsyncMock()
        mock_result = AsyncMock()
        mock_result.output = "Production Deployment Steps Guide"
        mock_agent.run = AsyncMock(return_value=mock_result)
        app.state.title_agent = mock_agent

        response = client.post(f"/chats/{chat.id}/title")
        assert response.status_code == 200
        body = response.json()
        assert body["chat_id"] == chat.id
        assert body["title"] == "Production Deployment Steps Guide"

        # Verify persisted
        updated_chat = hist.get_chat(chat.id)
        assert updated_chat is not None
        assert updated_chat.title == "Production Deployment Steps Guide"
        assert updated_chat.title_generated is True

    def test_title_returns_existing_when_already_generated(self, client: TestClient):
        """If title was already LLM-generated, return it without calling agent again."""
        from main import app

        hist: ChatHistoryService = app.state.history
        chat = hist.get_or_create_chat(None, "dev-user")
        hist.save_user_message(chat.id, "Test message")
        hist.update_title(chat.id, "Existing LLM Title", generated=True)

        mock_agent = AsyncMock()
        app.state.title_agent = mock_agent

        response = client.post(f"/chats/{chat.id}/title")
        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Existing LLM Title"

        # Agent should NOT have been called
        mock_agent.run.assert_not_awaited()

    def test_title_regenerates_when_only_fallback_exists(self, client: TestClient):
        """If title exists but was not LLM-generated, generate a new one."""
        from main import app

        hist: ChatHistoryService = app.state.history
        chat = hist.get_or_create_chat(None, "dev-user")
        hist.save_user_message(chat.id, "What is the vacation policy?")
        hist.save_assistant_message(chat.id, "The vacation policy states...")

        # Simulate fallback title (title_generated = False)
        hist.update_title(chat.id, "What is the vacation policy?", generated=False)

        mock_agent = AsyncMock()
        mock_result = AsyncMock()
        mock_result.output = "Vacation Policy Overview"
        mock_agent.run = AsyncMock(return_value=mock_result)
        app.state.title_agent = mock_agent

        response = client.post(f"/chats/{chat.id}/title")
        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Vacation Policy Overview"


class TestModels:
    """Test Pydantic model validation."""

    def test_chat_request_valid(self):
        from presentation.schemas import ChatRequest

        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.chat_id is None

    def test_chat_request_with_chat_id(self):
        from presentation.schemas import ChatRequest

        req = ChatRequest(message="Hello", chat_id="chat-1")
        assert req.chat_id == "chat-1"

    def test_chat_response_valid(self):
        from presentation.schemas import ChatResponse

        resp = ChatResponse(
            chat_id="c1",
            message_id="m1",
            answer="Answer [1].\n\nSources:\n[1] doc.md",
        )
        assert "[1]" in resp.answer
        assert resp.tool_calls == []
        assert resp.sources == []

    def test_login_request_valid(self):
        from presentation.schemas import LoginRequest

        req = LoginRequest(name="Alice", email="alice@northwind.com")
        assert req.name == "Alice"
        assert req.email == "alice@northwind.com"

    def test_chat_title_response_valid(self):
        from presentation.schemas import ChatTitleResponse

        resp = ChatTitleResponse(chat_id="c1", title="Production Deployment Guide")
        assert resp.chat_id == "c1"
        assert resp.title == "Production Deployment Guide"


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

    def test_auth_defaults(self):
        s = Settings(
            _env_file=None,
            azure_openai_api_key="k",
            azure_openai_endpoint="https://ep.openai.azure.com/",
        )
        assert s.auth_enabled is True
        assert s.jwt_secret == "dev-secret-change-in-production!!"
        assert s.jwt_expiry_hours == 24
        assert s.open_registration is False

    def test_observability_defaults(self):
        s = Settings(
            _env_file=None,
            azure_openai_api_key="k",
            azure_openai_endpoint="https://ep.openai.azure.com/",
        )
        assert s.observability == "off"
        assert s.otel_service_name == "knowledge-assistant-backend"
        assert s.otel_exporter_otlp_endpoint == "http://localhost:4318"
        assert s.otel_console_exporter is False

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
