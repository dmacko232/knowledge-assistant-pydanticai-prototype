"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation."""

    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""

    messages: list[ChatMessage] = Field(
        description="Conversation history. The last message should be the new user message."
    )


class ChatResponse(BaseModel):
    """Response body from the /chat endpoint."""

    answer: str = Field(description="The assistant's response with inline citations [1], [2], etc.")
