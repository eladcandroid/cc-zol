"""Pydantic models for authentication."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class VerificationCode(BaseModel):
    """Verification code model."""

    code: str
    expires_at: datetime


class User(BaseModel):
    """User model stored in MongoDB."""

    email: EmailStr
    verification_code: Optional[str] = None
    verification_code_expires: Optional[datetime] = None
    intercept_token: Optional[str] = None
    verified: bool = False
    active: bool = True  # Admin can toggle to disable user
    created_at: datetime = datetime.utcnow()
    last_logged_in: Optional[datetime] = None


class AuthToken(BaseModel):
    """Token returned after successful authentication."""

    token: str
    email: str
