"""Domain entities and value objects.

These are the core data structures of the knowledge assistant domain,
independent of any infrastructure or framework concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Chat domain entities (persisted in chat history DB)
# ---------------------------------------------------------------------------


@dataclass
class User:
    id: str
    name: str
    email: str | None
    created_at: str


@dataclass
class Chat:
    id: str
    user_id: str
    title: str | None
    title_generated: bool
    created_at: str
    updated_at: str


@dataclass
class Message:
    id: str
    chat_id: str
    role: str
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    model: str | None = None
    latency_ms: int | None = None
    created_at: str = ""


@dataclass
class ChatSummary:
    id: str
    title: str | None
    created_at: str
    updated_at: str
    message_count: int


# ---------------------------------------------------------------------------
# Retrieval domain entity
# ---------------------------------------------------------------------------


@dataclass
class RetrievalResult:
    """A single retrieval result with source metadata."""

    chunk_id: str
    document_name: str
    category: str
    section_header: str | None
    generation_chunk: str
    last_updated: str | None
    score: float
    chunk_metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Shared DTO (used by both use-case and presentation layers)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """A single message in the conversation (used internally by the use case)."""

    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
