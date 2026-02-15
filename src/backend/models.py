"""Pydantic models for API requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Domain model (shared between use-case and presentation layers)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """A single message in the conversation (used internally by the use case)."""

    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    name: str = Field(description="User display name")
    email: str = Field(description="User email")


class LoginResponse(BaseModel):
    """Response from POST /auth/login."""

    token: str
    user_id: str
    name: str


# ---------------------------------------------------------------------------
# Chat request / response (stateful — backend manages history)
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Request body for POST /chat and POST /chat/stream.

    ``user_id`` is extracted from the JWT — not sent in the body.
    """

    chat_id: str | None = Field(
        default=None,
        description="Existing chat ID to continue. None starts a new chat.",
    )
    message: str = Field(description="The new user message")


class ChatResponse(BaseModel):
    """Response body from the POST /chat endpoint."""

    chat_id: str = Field(description="The chat ID (new or existing)")
    message_id: str = Field(description="ID of the persisted assistant message")
    answer: str = Field(description="The assistant's response with inline citations")
    tool_calls: list[dict] = Field(
        default_factory=list,
        description="Tool calls made during this turn: [{name, args, result}]",
    )
    sources: list[dict] = Field(
        default_factory=list,
        description="Sources cited: [{document, section, date}]",
    )


# ---------------------------------------------------------------------------
# Chat history listing
# ---------------------------------------------------------------------------


class ChatSummaryResponse(BaseModel):
    """A single chat in the listing."""

    id: str
    title: str | None
    created_at: str
    updated_at: str
    message_count: int


class MessageResponse(BaseModel):
    """A single persisted message."""

    id: str
    role: str
    content: str
    tool_calls: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    model: str | None = None
    latency_ms: int | None = None
    created_at: str


# ---------------------------------------------------------------------------
# Chat title generation
# ---------------------------------------------------------------------------


class ChatTitleResponse(BaseModel):
    """Response from POST /chats/{chat_id}/title."""

    chat_id: str
    title: str
