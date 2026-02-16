"""FastAPI application bootstrap — composition root.

This module wires together all layers (presentation, application, domain)
and manages the application lifecycle.  No route handlers live here;
they are defined in ``presentation.routes``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from openai import AzureOpenAI

from application.infrastructure.agent import create_agent, create_title_agent
from application.infrastructure.telemetry import is_observability_active, setup_telemetry
from application.use_cases.chat import ChatUseCase
from config import get_settings
from domain.infrastructure.chat_history_service import ChatHistoryService
from domain.infrastructure.retrieval_service import RetrievalService
from domain.infrastructure.sql_service import SQLService
from logging_config import setup_logging
from presentation.routes.auth import router as auth_router
from presentation.routes.chat import router as chat_router

# Configure loguru before anything else
setup_logging()


# ---------------------------------------------------------------------------
# Lifespan: initialise shared resources once at startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Set up and tear down services around the application lifetime."""
    settings = get_settings()
    settings.validate_runtime()

    # Embedding client (sync) — used by the retrieval service
    embedding_client = AzureOpenAI(
        api_key=settings.azure_openai_embedding_api_key,
        azure_endpoint=settings.azure_openai_embedding_endpoint,
        api_version=settings.azure_openai_embedding_api_version,
    )

    retrieval = RetrievalService(
        db_path=settings.db_path,
        embedding_client=embedding_client,
        embedding_deployment=settings.azure_openai_embedding_deployment,
        embedding_dimensions=settings.embedding_dimensions,
        reranker_enabled=settings.reranker_enabled,
        reranker_api_key=settings.reranker_api_key,
        reranker_model=settings.reranker_model,
        reranker_top_n=settings.reranker_top_n,
    )
    retrieval.connect()

    sql = SQLService(db_path=settings.db_path)
    sql.connect()

    # Chat history (separate DB — auto-creates schema)
    history = ChatHistoryService(db_path=settings.chat_db_path)
    history.connect()

    # Seed pre-registered users (used when open_registration is disabled)
    history.seed_users(
        [
            {"name": "Alice Smith", "email": "alice@northwind.com"},
            {"name": "Bob Jones", "email": "bob@northwind.com"},
        ]
    )

    otel_active = is_observability_active(settings)
    agent = create_agent(settings, instrument=otel_active)
    title_agent = create_title_agent(settings, instrument=otel_active)

    # Wire up the use case with all its dependencies
    app.state.settings = settings
    app.state.chat_uc = ChatUseCase(
        agent=agent,
        retrieval_service=retrieval,
        sql_service=sql,
    )
    app.state.history = history
    app.state.title_agent = title_agent

    logger.info("Application startup complete")
    yield

    history.close()
    retrieval.close()
    sql.close()
    logger.info("Application shutdown complete")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Northwind Commerce Knowledge Assistant",
    description="Grounded Q&A over internal KB, KPIs, and employee directory.",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI with observability (no-op when OBSERVABILITY=off)
setup_telemetry(app, get_settings())

# Register route modules
app.include_router(auth_router)
app.include_router(chat_router)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
