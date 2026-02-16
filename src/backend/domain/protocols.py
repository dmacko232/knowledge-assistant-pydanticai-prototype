"""Domain service interfaces (ports).

These protocols define the contracts that infrastructure implementations
must satisfy.  The application layer depends on these abstractions,
not on concrete classes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.models import Chat, ChatSummary, Message, RetrievalResult, User

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


@runtime_checkable
class IRetrievalService(Protocol):
    """Interface for knowledge base retrieval.

    Implementations: RetrievalService (hybrid vector + BM25 search).
    """

    def search(
        self,
        query: str,
        category: str | None = None,
        vector_limit: int = 10,
        bm25_limit: int = 10,
        final_limit: int = 5,
        rrf_k: int = 60,
    ) -> list[RetrievalResult]: ...

    def connect(self) -> None: ...

    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------


@runtime_checkable
class ISQLService(Protocol):
    """Interface for read-only SQL query execution.

    Implementations: SQLService (SQLite-backed).
    """

    def execute_query(self, sql: str) -> str: ...

    def connect(self) -> None: ...

    def close(self) -> None: ...

    @staticmethod
    def get_schemas() -> str: ...


# ---------------------------------------------------------------------------
# Chat History
# ---------------------------------------------------------------------------


@runtime_checkable
class IChatHistoryService(Protocol):
    """Interface for chat history persistence.

    Implementations: ChatHistoryService (SQLite-backed).
    """

    def connect(self) -> None: ...

    def close(self) -> None: ...

    def create_user(self, name: str, email: str | None = None) -> User: ...

    def get_user(self, user_id: str) -> User | None: ...

    def get_user_by_email(self, email: str) -> User | None: ...

    def ensure_user(self, user_id: str) -> User: ...

    def ensure_user_by_email(self, name: str, email: str) -> User: ...

    def seed_users(self, users: list[dict]) -> None: ...

    def get_or_create_chat(self, chat_id: str | None, user_id: str) -> Chat: ...

    def get_chat(self, chat_id: str) -> Chat | None: ...

    def update_title(self, chat_id: str, title: str, generated: bool = True) -> None: ...

    def save_user_message(self, chat_id: str, content: str) -> str: ...

    def save_assistant_message(
        self,
        chat_id: str,
        content: str,
        tool_calls: list[dict] | None = None,
        sources: list[dict] | None = None,
        model: str | None = None,
        latency_ms: int | None = None,
    ) -> str: ...

    def get_chat_messages(self, chat_id: str) -> list[Message]: ...

    def list_user_chats(self, user_id: str) -> list[ChatSummary]: ...
