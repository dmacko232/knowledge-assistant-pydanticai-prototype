"""FastAPI backend for the Northwind Commerce knowledge assistant.

This module is a thin **presentation layer**.  All business logic lives in
the ``use_cases`` package so it can be tested and reused independently of
any HTTP framework.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AzureOpenAI

from agent import create_agent
from config import get_settings
from models import ChatRequest, ChatResponse
from services.retrieval_service import RetrievalService
from services.sql_service import SQLService
from use_cases import ChatUseCase, EmptyConversationError


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

    agent = create_agent(settings)

    # Wire up the use case with all its dependencies
    app.state.chat = ChatUseCase(
        agent=agent,
        retrieval_service=retrieval,
        sql_service=sql,
    )

    yield

    retrieval.close()
    sql.close()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Northwind Commerce Knowledge Assistant",
    description="Grounded Q&A over internal KB, KPIs, and employee directory.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Simple liveness / readiness check."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the knowledge assistant and receive a grounded answer.

    The request body contains the full conversation history.  The last
    message must be the new user message; earlier messages provide context
    so the agent can rewrite queries as standalone questions.
    """
    try:
        answer = await app.state.chat.execute(request.messages)
    except EmptyConversationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ChatResponse(answer=answer)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
