"""Chat use case — orchestrates conversation with the PydanticAI agent.

This module contains all business logic for handling a chat turn:
message validation, history conversion, agent execution, and
content-filter handling.  It has **no dependency on FastAPI** and can be
tested or invoked from any transport layer (HTTP, CLI, WebSocket, …).
"""

from __future__ import annotations

import logging

from pydantic_ai import Agent, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.exceptions import ModelHTTPError

from agent import AgentDeps
from models import ChatMessage
from services.retrieval_service import RetrievalService
from services.sql_service import SQLService
from use_cases.exceptions import EmptyConversationError

logger = logging.getLogger(__name__)

CONTENT_FILTER_REFUSAL = (
    "I'm sorry, but I can't comply with that request. "
    "I'm not able to share my system prompt, API keys, "
    "or any other internal configuration details."
)


class ChatUseCase:
    """Orchestrates a single chat turn with the knowledge assistant agent.

    Parameters
    ----------
    agent:
        A fully-configured PydanticAI ``Agent`` instance.
    retrieval_service:
        The hybrid-search retrieval service connected to the SQLite DB.
    sql_service:
        The read-only SQL service connected to the SQLite DB.
    """

    def __init__(
        self,
        agent: Agent[AgentDeps, str],
        retrieval_service: RetrievalService,
        sql_service: SQLService,
    ) -> None:
        self.agent = agent
        self.retrieval_service = retrieval_service
        self.sql_service = sql_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(self, messages: list[ChatMessage]) -> str:
        """Run a single chat turn and return the assistant's answer.

        Args:
            messages: Full conversation history. The last entry must be the
                      new user message; earlier entries provide context for
                      query rewriting.

        Returns:
            The agent's grounded answer string (with inline citations).

        Raises:
            EmptyConversationError: If *messages* is empty.
        """
        if not messages:
            raise EmptyConversationError("messages list must not be empty")

        deps = AgentDeps(
            retrieval_service=self.retrieval_service,
            sql_service=self.sql_service,
        )

        message_history = self._build_history(messages[:-1])
        user_prompt = messages[-1].content

        try:
            result = await self.agent.run(
                user_prompt,
                deps=deps,
                message_history=message_history if message_history else None,
            )
        except ModelHTTPError as exc:
            if self._is_jailbreak_filter(exc):
                logger.warning("Azure content filter blocked request (jailbreak detection)")
                return CONTENT_FILTER_REFUSAL
            raise

        return result.output

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_history(
        prior_messages: list[ChatMessage],
    ) -> list[ModelRequest | ModelResponse]:
        """Convert prior ChatMessages into PydanticAI message-history objects."""
        history: list[ModelRequest | ModelResponse] = []
        for msg in prior_messages:
            if msg.role == "user":
                history.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
            else:
                history.append(ModelResponse(parts=[TextPart(content=msg.content)]))
        return history

    @staticmethod
    def _is_jailbreak_filter(exc: ModelHTTPError) -> bool:
        """Return True if the error was caused by Azure's jailbreak content filter."""
        body = getattr(exc, "body", None) or {}
        inner = body.get("innererror", {})
        cfr = inner.get("content_filter_result", {})
        return cfr.get("jailbreak", {}).get("filtered", False)
