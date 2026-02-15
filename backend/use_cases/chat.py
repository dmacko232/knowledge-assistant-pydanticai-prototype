"""Chat use case — orchestrates conversation with the PydanticAI agent.

This module contains all business logic for handling a chat turn:
message validation, history conversion, agent execution, and
content-filter handling.  It has **no dependency on FastAPI** and can be
tested or invoked from any transport layer (HTTP, CLI, WebSocket, ...).
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from loguru import logger
from pydantic_ai import Agent, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ToolCallPart, ToolReturnPart

from agent import AgentDeps
from models import ChatMessage
from services.retrieval_service import RetrievalService
from services.sql_service import SQLService
from use_cases.exceptions import EmptyConversationError

CONTENT_FILTER_REFUSAL = (
    "I'm sorry, but I can't comply with that request. "
    "I'm not able to share my system prompt, API keys, "
    "or any other internal configuration details."
)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class ChatResult:
    """Rich result from a single chat turn, including metadata for persistence."""

    answer: str
    tool_calls: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    model: str | None = None
    latency_ms: int = 0


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------


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
    # Public API — non-streaming
    # ------------------------------------------------------------------

    async def execute(self, messages: list[ChatMessage]) -> ChatResult:
        """Run a single chat turn and return a rich result.

        Args:
            messages: Full conversation history. The last entry must be the
                      new user message; earlier entries provide context for
                      query rewriting.

        Returns:
            A ``ChatResult`` containing the answer plus tool call / source metadata.

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

        t0 = time.perf_counter()

        try:
            result = await self.agent.run(
                user_prompt,
                deps=deps,
                message_history=message_history if message_history else None,
            )
        except ModelHTTPError as exc:
            latency = int((time.perf_counter() - t0) * 1000)
            if self._is_jailbreak_filter(exc):
                logger.warning("Azure content filter blocked request (jailbreak detection)")
                return ChatResult(answer=CONTENT_FILTER_REFUSAL, latency_ms=latency)
            raise

        latency = int((time.perf_counter() - t0) * 1000)
        tool_calls = self._extract_tool_calls(result.all_messages())
        sources = self._extract_sources(result.all_messages())

        logger.info(
            "Chat completed | latency={}ms | tools={} | sources={}",
            latency,
            len(tool_calls),
            len(sources),
        )

        return ChatResult(
            answer=result.output,
            tool_calls=tool_calls,
            sources=sources,
            model=None,
            latency_ms=latency,
        )

    # ------------------------------------------------------------------
    # Public API — streaming
    # ------------------------------------------------------------------

    async def execute_stream(
        self, messages: list[ChatMessage]
    ) -> AsyncIterator[str | ChatResult]:
        """Run a streaming chat turn.

        Yields:
            ``str`` chunks as the agent produces text.
            As the **final** item, yields a ``ChatResult`` with the full answer
            and metadata (tool_calls, sources, latency).

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

        t0 = time.perf_counter()

        try:
            async with self.agent.run_stream(
                user_prompt,
                deps=deps,
                message_history=message_history if message_history else None,
            ) as stream:
                full_text = ""
                async for chunk in stream.stream_text(delta=True):
                    full_text += chunk
                    yield chunk

                latency = int((time.perf_counter() - t0) * 1000)
                tool_calls = self._extract_tool_calls(stream.all_messages())
                sources = self._extract_sources(stream.all_messages())

                logger.info(
                    "Stream completed | latency={}ms | tools={} | sources={}",
                    latency,
                    len(tool_calls),
                    len(sources),
                )

                yield ChatResult(
                    answer=full_text,
                    tool_calls=tool_calls,
                    sources=sources,
                    model=None,
                    latency_ms=latency,
                )

        except ModelHTTPError as exc:
            latency = int((time.perf_counter() - t0) * 1000)
            if self._is_jailbreak_filter(exc):
                logger.warning("Azure content filter blocked request (jailbreak detection)")
                yield CONTENT_FILTER_REFUSAL
                yield ChatResult(answer=CONTENT_FILTER_REFUSAL, latency_ms=latency)
                return
            raise

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

    @staticmethod
    def _extract_tool_calls(
        messages: list[ModelRequest | ModelResponse],
    ) -> list[dict]:
        """Pull tool-call / tool-return pairs from the PydanticAI message list."""
        calls: dict[str, dict] = {}
        for msg in messages:
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    calls[part.tool_call_id] = {
                        "name": part.tool_name,
                        "args": part.args if isinstance(part.args, dict) else {},
                    }
                elif isinstance(part, ToolReturnPart):
                    if part.tool_call_id in calls:
                        content = part.content
                        if not isinstance(content, str):
                            content = str(content)
                        calls[part.tool_call_id]["result"] = content[:500]
        return list(calls.values())

    @staticmethod
    def _extract_sources(
        messages: list[ModelRequest | ModelResponse],
    ) -> list[dict]:
        """Extract source citations from retrieval tool results."""
        sources: list[dict] = []
        for msg in messages:
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name == "search_knowledge_base":
                    content = part.content if isinstance(part.content, str) else str(part.content)
                    for block in content.split("---"):
                        doc = section = date = None
                        for line in block.strip().splitlines():
                            if line.startswith("Document:"):
                                doc = line.split(":", 1)[1].strip()
                            elif line.startswith("Section:"):
                                section = line.split(":", 1)[1].strip()
                            elif line.startswith("Last Updated:"):
                                date = line.split(":", 1)[1].strip()
                        if doc:
                            sources.append({
                                "document": doc,
                                "section": section or "N/A",
                                "date": date or "Unknown",
                            })
        return sources
