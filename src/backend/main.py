"""FastAPI backend for the Northwind Commerce knowledge assistant.

This module is a thin **presentation layer**.  All business logic lives in
the ``use_cases`` package so it can be tested and reused independently of
any HTTP framework.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from openai import AzureOpenAI

from agent import create_agent, create_title_agent
from auth import AuthenticatedUser, create_token, get_current_user
from config import get_settings
from logging_config import setup_logging
from models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSummaryResponse,
    ChatTitleResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
)
from services.chat_history_service import ChatHistoryService
from services.retrieval_service import RetrievalService
from services.sql_service import SQLService
from telemetry import is_observability_active, setup_telemetry
from use_cases.chat import ChatResult, ChatUseCase, generate_chat_title
from use_cases.exceptions import EmptyConversationError

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


# ---------------------------------------------------------------------------
# Helper: build ChatMessage list from persisted history
# ---------------------------------------------------------------------------


def _load_history_as_messages(history: ChatHistoryService, chat_id: str) -> list[ChatMessage]:
    """Load all messages from the history DB and convert to ChatMessage list."""
    stored = history.get_chat_messages(chat_id)
    return [ChatMessage(role=m.role, content=m.content) for m in stored]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Simple liveness / readiness check."""
    return {"status": "ok"}


# ---- Auth -----------------------------------------------------------------


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate a user and return a JWT.

    When ``open_registration`` is disabled (default), only pre-registered
    users can log in.  When enabled, unknown emails are auto-registered.
    """
    settings = app.state.settings
    hist: ChatHistoryService = app.state.history

    if settings.open_registration:
        user = hist.ensure_user_by_email(request.name, request.email)
    else:
        user = hist.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="No account found for this email. Contact an administrator.",
            )

    token = create_token(user_id=user.id, name=user.name, email=user.email or "")
    logger.info("POST /auth/login | user={} name={}", user.id, user.name)
    return LoginResponse(token=token, user_id=user.id, name=user.name)


# ---- Chat (non-streaming) ------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Send a message and receive a grounded answer (non-streaming).

    The backend manages conversation history.  Send ``chat_id=null`` to
    start a new conversation, or pass an existing ID to continue one.
    """
    hist: ChatHistoryService = app.state.history
    uc: ChatUseCase = app.state.chat_uc

    # 1) Ensure chat exists
    chat_obj = hist.get_or_create_chat(request.chat_id, current_user.user_id)

    # 2) Persist user message
    hist.save_user_message(chat_obj.id, request.message)

    # 3) Load full history for the agent
    messages = _load_history_as_messages(hist, chat_obj.id)

    logger.info(
        "POST /chat | user={} chat={} msg={}",
        current_user.user_id,
        chat_obj.id,
        request.message[:60],
    )

    # 4) Execute use case
    try:
        result: ChatResult = await uc.execute(messages)
    except EmptyConversationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # 5) Persist assistant message
    msg_id = hist.save_assistant_message(
        chat_id=chat_obj.id,
        content=result.answer,
        tool_calls=result.tool_calls,
        sources=result.sources,
        model=result.model,
        latency_ms=result.latency_ms,
    )

    return ChatResponse(
        chat_id=chat_obj.id,
        message_id=msg_id,
        answer=result.answer,
        tool_calls=result.tool_calls,
        sources=result.sources,
    )


# ---- Chat (streaming, Vercel AI Data Stream Protocol) ---------------------


@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Send a message and receive a streamed answer.

    Uses the **Vercel AI Data Stream Protocol**:
    - ``0:"text chunk"\\n``  — streamed text tokens
    - ``2:[{...}]\\n``       — data annotations (tool_calls, sources)
    - ``d:{"finishReason":"stop"}\\n`` — stream-done signal
    """
    hist: ChatHistoryService = app.state.history
    uc: ChatUseCase = app.state.chat_uc

    chat_obj = hist.get_or_create_chat(request.chat_id, current_user.user_id)
    hist.save_user_message(chat_obj.id, request.message)
    messages = _load_history_as_messages(hist, chat_obj.id)

    logger.info(
        "POST /chat/stream | user={} chat={} msg={}",
        current_user.user_id,
        chat_obj.id,
        request.message[:60],
    )

    async def event_generator():
        final_result: ChatResult | None = None

        async for chunk in uc.execute_stream(messages):
            if isinstance(chunk, ChatResult):
                final_result = chunk
            else:
                # Vercel protocol: text token
                yield f"0:{json.dumps(chunk)}\n"

        if final_result:
            # Persist assistant message
            msg_id = hist.save_assistant_message(
                chat_id=chat_obj.id,
                content=final_result.answer,
                tool_calls=final_result.tool_calls,
                sources=final_result.sources,
                model=final_result.model,
                latency_ms=final_result.latency_ms,
            )

            # Vercel protocol: data annotation with metadata
            annotation = {
                "chat_id": chat_obj.id,
                "message_id": msg_id,
                "tool_calls": final_result.tool_calls,
                "sources": final_result.sources,
            }
            yield f"2:{json.dumps([annotation])}\n"

        # Vercel protocol: finish signal
        yield f"d:{json.dumps({'finishReason': 'stop'})}\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---- Chat history ---------------------------------------------------------


@app.get("/chats", response_model=list[ChatSummaryResponse])
async def list_chats(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all chats for the authenticated user, newest first."""
    hist: ChatHistoryService = app.state.history
    summaries = hist.list_user_chats(current_user.user_id)
    return [
        ChatSummaryResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=s.message_count,
        )
        for s in summaries
    ]


@app.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
async def get_chat_messages(
    chat_id: str,
    _current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get all messages in a chat, ordered chronologically."""
    hist: ChatHistoryService = app.state.history
    messages = hist.get_chat_messages(chat_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Chat not found or has no messages")
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls,
            sources=m.sources,
            model=m.model,
            latency_ms=m.latency_ms,
            created_at=m.created_at,
        )
        for m in messages
    ]


# ---- Chat title generation ------------------------------------------------


@app.post("/chats/{chat_id}/title", response_model=ChatTitleResponse)
async def generate_title(
    chat_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Generate (or fetch existing) LLM-based title for a chat.

    Idempotent: if a title was already generated by the LLM, it is returned
    immediately without another LLM call.
    """
    hist: ChatHistoryService = app.state.history

    chat = hist.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Return existing LLM-generated title
    if chat.title and chat.title_generated:
        return ChatTitleResponse(chat_id=chat_id, title=chat.title)

    # Load messages and generate via LLM
    stored = hist.get_chat_messages(chat_id)
    messages = [ChatMessage(role=m.role, content=m.content) for m in stored]

    title = await generate_chat_title(messages, app.state.title_agent)
    hist.update_title(chat_id, title, generated=True)

    logger.info("POST /chats/{}/title | user={} title={}", chat_id, current_user.user_id, title)
    return ChatTitleResponse(chat_id=chat_id, title=title)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
