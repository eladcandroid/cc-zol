"""Authentication routes for cc-zol."""

import logging
from pydantic import BaseModel, EmailStr

from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class SendCodeRequest(BaseModel):
    """Request to send verification code."""

    email: EmailStr


class VerifyRequest(BaseModel):
    """Request to verify code."""

    email: EmailStr
    code: str


class TokenResponse(BaseModel):
    """Response with authentication token."""

    token: str
    email: str


@router.post("/send-code")
async def send_verification_code(request_data: SendCodeRequest, request: Request):
    """Send verification code to email."""
    user_db = getattr(request.app.state, "user_db", None)
    email_service = getattr(request.app.state, "email_service", None)

    if not user_db:
        raise HTTPException(status_code=503, detail="Authentication not configured")

    email = request_data.email.lower()

    try:
        # Generate and store verification code
        code = await user_db.create_or_update_verification(email)

        # Send the code
        if email_service:
            email_service.send_verification_code(email, code)
        else:
            # Fallback to logging
            logger.info(f"Verification code for {email}: {code}")

        return {"status": "ok", "message": "Verification code sent"}

    except Exception as e:
        logger.error(f"Failed to send verification code: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification code")


@router.post("/verify", response_model=TokenResponse)
async def verify_code(request_data: VerifyRequest, request: Request):
    """Verify code and return authentication token."""
    user_db = getattr(request.app.state, "user_db", None)

    if not user_db:
        raise HTTPException(status_code=503, detail="Authentication not configured")

    email = request_data.email.lower()
    code = request_data.code.strip()

    try:
        token = await user_db.verify_code(email, code)

        if not token:
            raise HTTPException(
                status_code=401, detail="Invalid or expired verification code"
            )

        return TokenResponse(token=token, email=email)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify code: {e}")
        raise HTTPException(status_code=500, detail="Verification failed")
