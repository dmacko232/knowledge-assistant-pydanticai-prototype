"""Loguru logging configuration for the backend.

Call ``setup_logging()`` once at application startup to:
- configure loguru sinks (coloured stderr + optional file rotation)
- intercept all stdlib ``logging`` records (uvicorn, openai, pydantic_ai)
  and route them through loguru.
"""

from __future__ import annotations

import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Redirect stdlib logging records to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(*, level: str = "INFO", json: bool = False) -> None:
    """Configure loguru as the single logging backend.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, …).
        json: If True, emit structured JSON to stderr (useful for log aggregators).
    """
    # Remove the default loguru sink so we can replace it
    logger.remove()

    # Primary sink: stderr with colour and a concise format
    if json:
        logger.add(sys.stderr, level=level, serialize=True)
    else:
        logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
        )

    # Intercept stdlib loggers used by third-party packages
    intercept = InterceptHandler()
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "openai", "httpx"):
        stdlib_logger = logging.getLogger(name)
        stdlib_logger.handlers = [intercept]
        stdlib_logger.propagate = False

    # Also intercept the root logger as a catch-all
    logging.root.handlers = [intercept]
    logging.root.setLevel(logging.DEBUG)
