"""Authentication middleware for FastAPI routes."""

import logging
from typing import Optional

from fastapi import Request, HTTPException, Depends

from .models import User

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[User]:
    """
    Extract and validate user from Authorization header.
    Returns the user if valid, None if no auth provided.
    """
    auth_header = request.headers.get("Authorization", "")

    # Support both "Bearer <token>" and raw "<token>" formats
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    elif auth_header:
        token = auth_header
    else:
        return None

    # Get user database from app state
    user_db = getattr(request.app.state, "user_db", None)
    if not user_db:
        logger.warning("User database not initialized")
        return None

    user = await user_db.get_user_by_token(token)
    return user


async def require_auth(request: Request) -> User:
    """
    Dependency that requires valid authentication.
    Raises 401 if not authenticated.
    """
    user = await get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "type": "error",
                "error": {
                    "type": "authentication_error",
                    "message": "Invalid or missing authentication token",
                },
            },
        )

    return user
