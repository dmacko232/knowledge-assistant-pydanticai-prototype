"""Tests for ChatHistoryService — CRUD operations on chat history."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.chat_history_service import ChatHistoryService


@pytest.fixture()
def history_service(tmp_path: Path) -> ChatHistoryService:
    """Create a ChatHistoryService connected to a temp database."""
    svc = ChatHistoryService(db_path=tmp_path / "chat_history.sqlite")
    svc.connect()
    yield svc
    svc.close()


class TestUsers:
    def test_create_user(self, history_service: ChatHistoryService):
        user = history_service.create_user("Alice", "alice@example.com")
        assert user.name == "Alice"
        assert user.email == "alice@example.com"
        assert user.id

    def test_get_user(self, history_service: ChatHistoryService):
        user = history_service.create_user("Bob")
        fetched = history_service.get_user(user.id)
        assert fetched is not None
        assert fetched.name == "Bob"

    def test_get_user_not_found(self, history_service: ChatHistoryService):
        assert history_service.get_user("nonexistent") is None

    def test_ensure_user_creates_if_missing(self, history_service: ChatHistoryService):
        user = history_service.ensure_user("brand-new-id")
        assert user.name == "User"
        assert user.id == "brand-new-id"


class TestChats:
    def test_create_new_chat(self, history_service: ChatHistoryService):
        user = history_service.create_user("Alice")
        chat = history_service.get_or_create_chat(None, user.id)
        assert chat.id
        assert chat.user_id == user.id
        assert chat.title is None

    def test_get_existing_chat(self, history_service: ChatHistoryService):
        user = history_service.create_user("Alice")
        chat = history_service.get_or_create_chat(None, user.id)
        same = history_service.get_or_create_chat(chat.id, user.id)
        assert same.id == chat.id

    def test_chat_title_set_from_first_message(self, history_service: ChatHistoryService):
        user = history_service.create_user("Alice")
        chat = history_service.get_or_create_chat(None, user.id)
        history_service.save_user_message(chat.id, "What is the security policy?")

        updated = history_service.get_or_create_chat(chat.id, user.id)
        assert updated.title == "What is the security policy?"


class TestMessages:
    def test_save_and_retrieve_messages(self, history_service: ChatHistoryService):
        user = history_service.create_user("Alice")
        chat = history_service.get_or_create_chat(None, user.id)

        history_service.save_user_message(chat.id, "Hello")
        history_service.save_assistant_message(
            chat.id,
            "Hi there!",
            tool_calls=[{"name": "search", "args": {}, "result": "..."}],
            sources=[{"document": "doc.md", "section": "Intro", "date": "2025-01-01"}],
            model="gpt-4o-mini",
            latency_ms=150,
        )

        msgs = history_service.get_chat_messages(chat.id)
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[0].content == "Hello"
        assert msgs[1].role == "assistant"
        assert msgs[1].content == "Hi there!"
        assert len(msgs[1].tool_calls) == 1
        assert len(msgs[1].sources) == 1
        assert msgs[1].model == "gpt-4o-mini"
        assert msgs[1].latency_ms == 150

    def test_empty_chat_returns_empty_list(self, history_service: ChatHistoryService):
        assert history_service.get_chat_messages("nonexistent") == []


class TestListing:
    def test_list_user_chats(self, history_service: ChatHistoryService):
        user = history_service.create_user("Alice")
        chat1 = history_service.get_or_create_chat(None, user.id)
        chat2 = history_service.get_or_create_chat(None, user.id)

        history_service.save_user_message(chat1.id, "Msg 1")
        history_service.save_user_message(chat2.id, "Msg 2a")
        history_service.save_user_message(chat2.id, "Msg 2b")

        chats = history_service.list_user_chats(user.id)
        assert len(chats) == 2
        counts = {c.id: c.message_count for c in chats}
        assert counts[chat1.id] == 1
        assert counts[chat2.id] == 2

    def test_list_empty(self, history_service: ChatHistoryService):
        assert history_service.list_user_chats("no-such-user") == []
