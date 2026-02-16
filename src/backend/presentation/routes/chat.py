"""Chat routes — chat, streaming, history, and title generation endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from application.exceptions import EmptyConversationError
from application.use_cases.chat import ChatResult, ChatUseCase, generate_chat_title
from domain.infrastructure.chat_history_service import ChatHistoryService
from domain.models import ChatMessage
from presentation.infrastructure.auth import AuthenticatedUser, get_current_user
from presentation.schemas import (
    ChatRequest,
    ChatResponse,
    ChatSummaryResponse,
    ChatTitleResponse,
    MessageResponse,
)

router = APIRouter(tags=["chat"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _load_history_as_messages(history: ChatHistoryService, chat_id: str) -> list[ChatMessage]:
    """Load all messages from the history DB and convert to ChatMessage list."""
    stored = history.get_chat_messages(chat_id)
    return [ChatMessage(role=m.role, content=m.content) for m in stored]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
async def health():
    """Simple liveness / readiness check."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Chat (non-streaming)
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    raw_request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Send a message and receive a grounded answer (non-streaming)."""
    hist: ChatHistoryService = raw_request.app.state.history
    uc: ChatUseCase = raw_request.app.state.chat_uc

    chat_obj = hist.get_or_create_chat(request.chat_id, current_user.user_id)
    hist.save_user_message(chat_obj.id, request.message)
    messages = _load_history_as_messages(hist, chat_obj.id)

    logger.info(
        "POST /chat | user={} chat={} msg={}",
        current_user.user_id,
        chat_obj.id,
        request.message[:60],
    )

    try:
        result: ChatResult = await uc.execute(messages)
    except EmptyConversationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

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


# ---------------------------------------------------------------------------
# Chat (streaming, Vercel AI Data Stream Protocol)
# ---------------------------------------------------------------------------


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    raw_request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Send a message and receive a streamed answer (Vercel AI Data Stream Protocol)."""
    hist: ChatHistoryService = raw_request.app.state.history
    uc: ChatUseCase = raw_request.app.state.chat_uc

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
                yield f"0:{json.dumps(chunk)}\n"

        if final_result:
            msg_id = hist.save_assistant_message(
                chat_id=chat_obj.id,
                content=final_result.answer,
                tool_calls=final_result.tool_calls,
                sources=final_result.sources,
                model=final_result.model,
                latency_ms=final_result.latency_ms,
            )

            annotation = {
                "chat_id": chat_obj.id,
                "message_id": msg_id,
                "tool_calls": final_result.tool_calls,
                "sources": final_result.sources,
            }
            yield f"2:{json.dumps([annotation])}\n"

        yield f"d:{json.dumps({'finishReason': 'stop'})}\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------


@router.get("/chats", response_model=list[ChatSummaryResponse])
async def list_chats(
    raw_request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all chats for the authenticated user, newest first."""
    hist: ChatHistoryService = raw_request.app.state.history
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


@router.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
async def get_chat_messages(
    chat_id: str,
    raw_request: Request,
    _current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get all messages in a chat, ordered chronologically."""
    hist: ChatHistoryService = raw_request.app.state.history
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
# Chat title generation
# ---------------------------------------------------------------------------


@router.post("/chats/{chat_id}/title", response_model=ChatTitleResponse)
async def generate_title(
    chat_id: str,
    raw_request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Generate (or fetch existing) LLM-based title for a chat."""
    hist: ChatHistoryService = raw_request.app.state.history

    chat_record = hist.get_chat(chat_id)
    if not chat_record:
        raise HTTPException(status_code=404, detail="Chat not found")

    if chat_record.title and chat_record.title_generated:
        return ChatTitleResponse(chat_id=chat_id, title=chat_record.title)

    stored = hist.get_chat_messages(chat_id)
    messages = [ChatMessage(role=m.role, content=m.content) for m in stored]

    title = await generate_chat_title(messages, raw_request.app.state.title_agent)
    hist.update_title(chat_id, title, generated=True)

    logger.info("POST /chats/{}/title | user={} title={}", chat_id, current_user.user_id, title)
    return ChatTitleResponse(chat_id=chat_id, title=title)
