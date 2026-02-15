"""Chat history persistence service.

Manages users, chats, and messages in a separate SQLite database so the
knowledge-base DB remains read-only and resettable independently.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

# ---------------------------------------------------------------------------
# Data classes returned by the service
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
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    title TEXT,
    title_generated BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES chats(id),
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    tool_calls TEXT DEFAULT '[]',
    sources TEXT DEFAULT '[]',
    model TEXT,
    latency_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


class ChatHistoryService:
    """CRUD operations for chat history stored in a dedicated SQLite file."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        """Open (or create) the database and ensure the schema exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(_SCHEMA_SQL)
        self._migrate()
        self.conn.commit()
        logger.info("Chat history DB ready at {}", self.db_path)

    def _migrate(self) -> None:
        """Apply incremental schema migrations for existing databases."""
        assert self.conn
        # Add title_generated column if it doesn't exist yet
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(chats)").fetchall()}
        if "title_generated" not in columns:
            self.conn.execute("ALTER TABLE chats ADD COLUMN title_generated BOOLEAN DEFAULT 0")
            logger.info("Migrated chats table: added title_generated column")

    def close(self) -> None:
        if self.conn:
            self.conn.close()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def create_user(self, name: str, email: str | None = None) -> User:
        """Create a new user and return it."""
        assert self.conn
        user_id = str(uuid.uuid4())
        now = _utcnow()
        self.conn.execute(
            "INSERT INTO users (id, name, email, created_at) VALUES (?, ?, ?, ?)",
            (user_id, name, email, now),
        )
        self.conn.commit()
        return User(id=user_id, name=name, email=email, created_at=now)

    def get_user(self, user_id: str) -> User | None:
        assert self.conn
        row = self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        return User(
            id=row["id"], name=row["name"], email=row["email"], created_at=row["created_at"]
        )

    def ensure_user(self, user_id: str) -> User:
        """Return existing user or auto-create a placeholder with the given ID."""
        user = self.get_user(user_id)
        if user:
            return user
        assert self.conn
        now = _utcnow()
        self.conn.execute(
            "INSERT INTO users (id, name, email, created_at) VALUES (?, ?, ?, ?)",
            (user_id, "User", None, now),
        )
        self.conn.commit()
        return User(id=user_id, name="User", email=None, created_at=now)

    def ensure_user_by_email(self, name: str, email: str) -> User:
        """Return existing user by email, or create one with a new UUID."""
        assert self.conn
        row = self.conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            return User(
                id=row["id"], name=row["name"], email=row["email"], created_at=row["created_at"]
            )
        user_id = str(uuid.uuid4())
        now = _utcnow()
        self.conn.execute(
            "INSERT INTO users (id, name, email, created_at) VALUES (?, ?, ?, ?)",
            (user_id, name, email, now),
        )
        self.conn.commit()
        logger.info("Created user {} ({})", name, email)
        return User(id=user_id, name=name, email=email, created_at=now)

    # ------------------------------------------------------------------
    # Chats
    # ------------------------------------------------------------------

    def get_chat(self, chat_id: str) -> Chat | None:
        """Return a chat by ID, or None if not found."""
        assert self.conn
        row = self.conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not row:
            return None
        return self._row_to_chat(row)

    def get_or_create_chat(self, chat_id: str | None, user_id: str) -> Chat:
        """Return existing chat or create a new one.

        If *chat_id* is ``None``, a brand-new chat is created.
        """
        assert self.conn

        if chat_id:
            chat = self.get_chat(chat_id)
            if chat:
                return chat

        # Create new chat
        new_id = chat_id or str(uuid.uuid4())
        now = _utcnow()
        self.ensure_user(user_id)
        self.conn.execute(
            "INSERT INTO chats (id, user_id, title, title_generated, created_at, updated_at) "
            "VALUES (?, ?, ?, 0, ?, ?)",
            (new_id, user_id, None, now, now),
        )
        self.conn.commit()
        logger.info("Created new chat {}", new_id)
        return Chat(
            id=new_id,
            user_id=user_id,
            title=None,
            title_generated=False,
            created_at=now,
            updated_at=now,
        )

    def update_title(self, chat_id: str, title: str, generated: bool = True) -> None:
        """Persist an LLM-generated (or manual) title for a chat."""
        assert self.conn
        self.conn.execute(
            "UPDATE chats SET title = ?, title_generated = ?, updated_at = ? WHERE id = ?",
            (title, 1 if generated else 0, _utcnow(), chat_id),
        )
        self.conn.commit()

    def _update_chat_title_if_needed(self, chat_id: str, first_message: str) -> None:
        """Set the chat title from the first user message (truncated)."""
        assert self.conn
        row = self.conn.execute("SELECT title FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if row and not row["title"]:
            title = first_message[:80].strip()
            if len(first_message) > 80:
                title += "..."
            self.conn.execute(
                "UPDATE chats SET title = ?, updated_at = ? WHERE id = ?",
                (title, _utcnow(), chat_id),
            )
            self.conn.commit()

    def _touch_chat(self, chat_id: str) -> None:
        assert self.conn
        self.conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (_utcnow(), chat_id))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def save_user_message(self, chat_id: str, content: str) -> str:
        """Persist a user message and return its ID."""
        assert self.conn
        msg_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
            (msg_id, chat_id, content, _utcnow()),
        )
        self.conn.commit()
        self._update_chat_title_if_needed(chat_id, content)
        self._touch_chat(chat_id)
        return msg_id

    def save_assistant_message(
        self,
        chat_id: str,
        content: str,
        tool_calls: list[dict] | None = None,
        sources: list[dict] | None = None,
        model: str | None = None,
        latency_ms: int | None = None,
    ) -> str:
        """Persist an assistant message (with optional metadata) and return its ID."""
        assert self.conn
        msg_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO messages (id, chat_id, role, content, tool_calls, sources, model, latency_ms, created_at) "
            "VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?, ?)",
            (
                msg_id,
                chat_id,
                content,
                json.dumps(tool_calls or []),
                json.dumps(sources or []),
                model,
                latency_ms,
                _utcnow(),
            ),
        )
        self.conn.commit()
        self._touch_chat(chat_id)
        return msg_id

    def get_chat_messages(self, chat_id: str) -> list[Message]:
        """Return all messages in a chat, ordered chronologically."""
        assert self.conn
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC", (chat_id,)
        ).fetchall()
        return [self._row_to_message(row) for row in rows]

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_user_chats(self, user_id: str) -> list[ChatSummary]:
        """Return all chats for a user, newest first, with message counts."""
        assert self.conn
        rows = self.conn.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) AS message_count
            FROM chats c
            LEFT JOIN messages m ON m.chat_id = c.id
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [
            ChatSummary(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                message_count=row["message_count"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_chat(row: sqlite3.Row) -> Chat:
        return Chat(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            title_generated=bool(row["title_generated"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> Message:
        tool_calls = row["tool_calls"] or "[]"
        sources = row["sources"] or "[]"
        if isinstance(tool_calls, str):
            try:
                tool_calls = json.loads(tool_calls)
            except (json.JSONDecodeError, TypeError):
                tool_calls = []
        if isinstance(sources, str):
            try:
                sources = json.loads(sources)
            except (json.JSONDecodeError, TypeError):
                sources = []
        return Message(
            id=row["id"],
            chat_id=row["chat_id"],
            role=row["role"],
            content=row["content"],
            tool_calls=tool_calls,
            sources=sources,
            model=row["model"],
            latency_ms=row["latency_ms"],
            created_at=row["created_at"],
        )
