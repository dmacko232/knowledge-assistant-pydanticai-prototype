"""FastAPI backend for the Northwind Commerce knowledge assistant.

This module is a thin **presentation layer**.  All business logic lives in
the ``use_cases`` package so it can be tested and reused independently of
any HTTP framework.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from openai import AzureOpenAI

from agent import create_agent
from config import get_settings
from logging_config import setup_logging
from models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSummaryResponse,
    MessageResponse,
)
from services.chat_history_service import ChatHistoryService
from services.retrieval_service import RetrievalService
from services.sql_service import SQLService
from use_cases import ChatResult, ChatUseCase, EmptyConversationError

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

    agent = create_agent(settings)

    # Wire up the use case with all its dependencies
    app.state.chat_uc = ChatUseCase(
        agent=agent,
        retrieval_service=retrieval,
        sql_service=sql,
    )
    app.state.history = history

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
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: build ChatMessage list from persisted history
# ---------------------------------------------------------------------------


def _load_history_as_messages(
    history: ChatHistoryService, chat_id: str
) -> list[ChatMessage]:
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


# ---- Chat (non-streaming) ------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message and receive a grounded answer (non-streaming).

    The backend manages conversation history.  Send ``chat_id=null`` to
    start a new conversation, or pass an existing ID to continue one.
    """
    hist: ChatHistoryService = app.state.history
    uc: ChatUseCase = app.state.chat_uc

    # 1) Ensure chat exists
    chat_obj = hist.get_or_create_chat(request.chat_id, request.user_id)

    # 2) Persist user message
    hist.save_user_message(chat_obj.id, request.message)

    # 3) Load full history for the agent
    messages = _load_history_as_messages(hist, chat_obj.id)

    logger.info(
        "POST /chat | user={} chat={} msg={}",
        request.user_id,
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
async def chat_stream(request: ChatRequest):
    """Send a message and receive a streamed answer.

    Uses the **Vercel AI Data Stream Protocol**:
    - ``0:"text chunk"\\n``  — streamed text tokens
    - ``2:[{...}]\\n``       — data annotations (tool_calls, sources)
    - ``d:{"finishReason":"stop"}\\n`` — stream-done signal
    """
    hist: ChatHistoryService = app.state.history
    uc: ChatUseCase = app.state.chat_uc

    chat_obj = hist.get_or_create_chat(request.chat_id, request.user_id)
    hist.save_user_message(chat_obj.id, request.message)
    messages = _load_history_as_messages(hist, chat_obj.id)

    logger.info(
        "POST /chat/stream | user={} chat={} msg={}",
        request.user_id,
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
                yield f'0:{json.dumps(chunk)}\n'

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
            yield f'2:{json.dumps([annotation])}\n'

        # Vercel protocol: finish signal
        yield f'd:{json.dumps({"finishReason": "stop"})}\n'

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
async def list_chats(user_id: str = Query(..., description="User ID to list chats for")):
    """List all chats for a user, newest first."""
    hist: ChatHistoryService = app.state.history
    summaries = hist.list_user_chats(user_id)
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
async def get_chat_messages(chat_id: str):
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


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
