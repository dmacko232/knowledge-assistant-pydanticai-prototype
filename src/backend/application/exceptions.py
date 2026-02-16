"""Application-level exceptions.

These are business-logic errors, not HTTP errors. The presentation layer
(e.g. FastAPI routes) translates them into appropriate HTTP responses.
"""


class EmptyConversationError(ValueError):
    """Raised when the caller provides an empty messages list."""
