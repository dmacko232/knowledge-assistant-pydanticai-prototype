"""Auth routes — login endpoint."""

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from domain.infrastructure.chat_history_service import ChatHistoryService
from presentation.infrastructure.auth import create_token
from presentation.schemas import LoginRequest, LoginResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, raw_request: Request):
    """Authenticate a user and return a JWT.

    When ``open_registration`` is disabled (default), only pre-registered
    users can log in.  When enabled, unknown emails are auto-registered.
    """
    settings = raw_request.app.state.settings
    hist: ChatHistoryService = raw_request.app.state.history

    if settings.open_registration:
        user = hist.ensure_user_by_email(request.name, request.email)
    else:
        user = hist.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="No account found for this email. Contact an administrator.",
            )

    token = create_token(user_id=user.id, name=user.name, email=user.email or "")
    logger.info("POST /auth/login | user={} name={}", user.id, user.name)
    return LoginResponse(token=token, user_id=user.id, name=user.name)
