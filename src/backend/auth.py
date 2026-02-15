"""JWT authentication helpers for the backend.

Provides token creation/verification and a FastAPI dependency that extracts
the current user from the ``Authorization: Bearer <token>`` header.

When ``AUTH_ENABLED=false`` in settings, the dependency returns a mock user
so the API can be used without authentication during development.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, Request
from loguru import logger

from config import get_settings

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

ALGORITHM = "HS256"


@dataclass
class AuthenticatedUser:
    """The user extracted from a valid JWT."""

    user_id: str
    name: str
    email: str

    # Default mock user returned when auth is disabled
    _mock: AuthenticatedUser | None = None


def _mock_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="dev-user",
        name="Dev User",
        email="dev@northwind.com",
    )


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def create_token(user_id: str, name: str, email: str) -> str:
    """Create a signed JWT containing user claims."""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "name": name,
        "email": email,
        "exp": datetime.now(UTC) + timedelta(hours=settings.jwt_expiry_hours),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises on invalid/expired tokens."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_current_user(request: Request) -> AuthenticatedUser:
    """FastAPI dependency: extract user from JWT or return mock when auth disabled."""
    settings = get_settings()

    if not settings.auth_enabled:
        return _mock_user()

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]
    try:
        claims = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT presented")
        raise HTTPException(status_code=401, detail="Invalid token")

    return AuthenticatedUser(
        user_id=claims["sub"],
        name=claims.get("name", ""),
        email=claims.get("email", ""),
    )
