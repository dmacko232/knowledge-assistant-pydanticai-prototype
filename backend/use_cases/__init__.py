"""Use-case layer — business logic decoupled from the HTTP transport."""

from use_cases.chat import ChatResult, ChatUseCase
from use_cases.exceptions import EmptyConversationError

__all__ = ["ChatResult", "ChatUseCase", "EmptyConversationError"]
