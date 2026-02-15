"""Configuration for the backend using pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent.parent  # src/backend/ → project root


class Settings(BaseSettings):
    """All backend settings, loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Azure OpenAI — Chat model
    # ------------------------------------------------------------------
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2025-01-01-preview"
    azure_openai_chat_deployment: str = "gpt-4o-mini"

    # ------------------------------------------------------------------
    # Azure OpenAI — Embedding model
    # Falls back to the chat-model values when not set explicitly.
    # ------------------------------------------------------------------
    azure_openai_embedding_endpoint: str | None = None
    azure_openai_embedding_api_version: str | None = None
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_openai_embedding_api_key: str | None = None
    embedding_dimensions: int = 1536

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    vector_search_limit: int = 10
    bm25_search_limit: int = 10
    final_results_limit: int = 5
    rrf_k: int = 60

    # ------------------------------------------------------------------
    # Reranker (optional — disabled by default)
    # Set reranker_enabled=true and provide an API key to activate.
    # ------------------------------------------------------------------
    reranker_enabled: bool = False
    reranker_api_key: str | None = None
    reranker_model: str = "rerank-v3.5"
    reranker_top_n: int = 5

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    db_path: Path = _PROJECT_ROOT / "database" / "knowledge_assistant.sqlite"
    chat_db_path: Path = _PROJECT_ROOT / "database" / "chat_history.sqlite"

    # ------------------------------------------------------------------
    # Auth (JWT) — set AUTH_ENABLED=false to disable for development
    # ------------------------------------------------------------------
    auth_enabled: bool = True
    jwt_secret: str = "dev-secret-change-in-production!!"
    jwt_expiry_hours: int = 24

    # ------------------------------------------------------------------
    # OpenTelemetry — set OTEL_ENABLED=true to emit traces/metrics
    # ------------------------------------------------------------------
    otel_enabled: bool = False
    otel_service_name: str = "knowledge-assistant-backend"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_console_exporter: bool = False

    # ------------------------------------------------------------------
    # Computed defaults (embedding falls back to chat values)
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _apply_embedding_fallbacks(self) -> "Settings":
        if not self.azure_openai_embedding_endpoint:
            self.azure_openai_embedding_endpoint = self.azure_openai_endpoint
        if not self.azure_openai_embedding_api_version:
            self.azure_openai_embedding_api_version = self.azure_openai_api_version
        if not self.azure_openai_embedding_api_key:
            self.azure_openai_embedding_api_key = self.azure_openai_api_key
        return self

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_runtime(self) -> None:
        """Check that all required values are present and the DB exists.

        Call this at application startup (not at import time) so that
        tests can override settings before validation runs.
        """
        if not self.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not set. Add it to backend/.env")
        if not self.azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT not set. Add it to backend/.env")
        if not self.azure_openai_embedding_endpoint:
            raise ValueError(
                "No embedding endpoint. Set AZURE_OPENAI_EMBEDDING_ENDPOINT or AZURE_OPENAI_ENDPOINT."
            )
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {self.db_path}. Run the data pipeline first (make run-pipeline)."
            )
        if self.reranker_enabled and not self.reranker_api_key:
            raise ValueError("RERANKER_ENABLED is true but RERANKER_API_KEY is not set.")


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()
