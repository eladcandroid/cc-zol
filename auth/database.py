"""MongoDB database operations for authentication."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .models import User


class UserDatabase:
    """Async MongoDB operations for user authentication."""

    VERIFICATION_CODE_EXPIRY_MINUTES = 10
    TOKEN_LENGTH = 64  # 64-char hex token

    def __init__(self, mongodb_uri: str, database_name: str = "cc_zol"):
        """Initialize database connection."""
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._mongodb_uri = mongodb_uri
        self._database_name = database_name

    async def connect(self) -> None:
        """Connect to MongoDB."""
        self._client = AsyncIOMotorClient(self._mongodb_uri)
        self._db = self._client[self._database_name]
        # Create index on email for fast lookups
        await self._db.users.create_index("email", unique=True)
        # Create index on intercept_token for auth lookups
        await self._db.users.create_index("intercept_token", sparse=True)

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    @property
    def users(self):
        """Get users collection."""
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db.users

    def _generate_verification_code(self) -> str:
        """Generate a 6-digit verification code."""
        return f"{secrets.randbelow(1000000):06d}"

    def _generate_token(self) -> str:
        """Generate a secure 64-character hex token."""
        return secrets.token_hex(self.TOKEN_LENGTH // 2)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        doc = await self.users.find_one({"email": email.lower()})
        if doc:
            doc.pop("_id", None)
            return User(**doc)
        return None

    async def get_user_by_token(self, token: str) -> Optional[User]:
        """Get user by intercept token (must be verified and active)."""
        doc = await self.users.find_one({
            "intercept_token": token,
            "verified": True,
            "active": {"$ne": False}  # Active by default if field doesn't exist
        })
        if doc:
            doc.pop("_id", None)
            return User(**doc)
        return None

    async def create_or_update_verification(self, email: str) -> str:
        """Create or update verification code for email. Returns the code."""
        email = email.lower()
        code = self._generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(
            minutes=self.VERIFICATION_CODE_EXPIRY_MINUTES
        )

        await self.users.update_one(
            {"email": email},
            {
                "$set": {
                    "verification_code": code,
                    "verification_code_expires": expires_at,
                },
                "$setOnInsert": {
                    "email": email,
                    "verified": False,
                    "created_at": datetime.utcnow(),
                },
            },
            upsert=True,
        )
        return code

    async def verify_code(self, email: str, code: str) -> Optional[str]:
        """
        Verify the code for an email.
        Returns the intercept token if successful, None if failed.
        For pre-configured users, keeps their existing token.
        """
        email = email.lower()
        user = await self.get_user_by_email(email)

        if not user:
            return None

        # Check if user is active
        if not user.active:
            return None

        if not user.verification_code or not user.verification_code_expires:
            return None

        # Check code matches
        if user.verification_code != code:
            return None

        # Check not expired
        if datetime.utcnow() > user.verification_code_expires:
            return None

        # Use existing token if pre-configured, otherwise generate new one
        token = user.intercept_token if user.intercept_token else self._generate_token()
        await self.users.update_one(
            {"email": email},
            {
                "$set": {
                    "intercept_token": token,
                    "verified": True,
                    "verification_code": None,
                    "verification_code_expires": None,
                    "last_logged_in": datetime.utcnow(),
                }
            },
        )
        return token

    async def invalidate_token(self, email: str) -> bool:
        """Invalidate a user's token. Returns True if user existed."""
        email = email.lower()
        result = await self.users.update_one(
            {"email": email},
            {"$set": {"intercept_token": None, "verified": False}},
        )
        return result.modified_count > 0

    async def is_token_valid(self, token: str) -> bool:
        """Check if a token is valid."""
        user = await self.get_user_by_token(token)
        return user is not None

    async def seed_user(self, email: str, token: str) -> bool:
        """
        Seed a user with a pre-set token.
        Returns True if user was created/updated, False if already exists with same token.
        """
        email = email.lower()
        existing = await self.get_user_by_email(email)

        if existing and existing.intercept_token == token:
            return False  # Already seeded

        await self.users.update_one(
            {"email": email},
            {
                "$set": {
                    "intercept_token": token,
                    "verified": True,
                    "verification_code": None,
                    "verification_code_expires": None,
                },
                "$setOnInsert": {
                    "email": email,
                    "active": True,
                    "created_at": datetime.utcnow(),
                },
            },
            upsert=True,
        )
        return True

    async def seed_users(self, users: list[tuple[str, str]]) -> int:
        """
        Seed multiple users with pre-set tokens.
        Args: users - list of (email, token) tuples
        Returns: number of users seeded
        """
        count = 0
        for email, token in users:
            if await self.seed_user(email, token):
                count += 1
        return count

    # ==================== Admin Methods ====================

    async def list_users(self) -> list[dict]:
        """List all users for admin UI."""
        cursor = self.users.find({})
        users = []
        async for doc in cursor:
            doc.pop("_id", None)
            # Don't expose full token in list, just show if it exists
            if doc.get("intercept_token"):
                doc["has_token"] = True
                doc["intercept_token"] = doc["intercept_token"][:8] + "..."
            else:
                doc["has_token"] = False
            users.append(doc)
        return users

    async def get_user_for_admin(self, email: str) -> Optional[dict]:
        """Get full user details for admin (includes full token)."""
        email = email.lower()
        doc = await self.users.find_one({"email": email})
        if doc:
            doc.pop("_id", None)
            return doc
        return None

    async def toggle_user_active(self, email: str) -> Optional[bool]:
        """Toggle user active status. Returns new status or None if user not found."""
        email = email.lower()
        user = await self.get_user_by_email(email)
        if not user:
            return None

        new_status = not user.active
        await self.users.update_one(
            {"email": email},
            {"$set": {"active": new_status}}
        )
        return new_status

    async def update_user(self, email: str, updates: dict) -> bool:
        """Update user fields. Returns True if updated."""
        email = email.lower()
        # Only allow certain fields to be updated
        allowed_fields = {"active", "verified", "intercept_token"}
        safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        # If setting a new token, also mark as verified
        if "intercept_token" in safe_updates and safe_updates["intercept_token"]:
            safe_updates["verified"] = True

        if not safe_updates:
            return False

        result = await self.users.update_one(
            {"email": email},
            {"$set": safe_updates}
        )
        return result.modified_count > 0

    async def delete_user(self, email: str) -> bool:
        """Delete a user. Returns True if deleted."""
        email = email.lower()
        result = await self.users.delete_one({"email": email})
        return result.deleted_count > 0

    async def get_stats(self) -> dict:
        """Get user statistics for admin dashboard."""
        total = await self.users.count_documents({})
        active = await self.users.count_documents({"active": {"$ne": False}})
        verified = await self.users.count_documents({"verified": True})
        with_token = await self.users.count_documents({"intercept_token": {"$ne": None}})

        # Recent logins (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_logins = await self.users.count_documents({
            "last_logged_in": {"$gte": yesterday}
        })

        # Recent signups (last 7 days)
        last_week = datetime.utcnow() - timedelta(days=7)
        recent_signups = await self.users.count_documents({
            "created_at": {"$gte": last_week}
        })

        return {
            "total_users": total,
            "active_users": active,
            "inactive_users": total - active,
            "verified_users": verified,
            "users_with_token": with_token,
            "logins_last_24h": recent_logins,
            "signups_last_7d": recent_signups,
        }

    async def create_preconfigured_user(
        self, email: str, token: str, active: bool = False
    ) -> dict:
        """
        Create a pre-configured user with a pre-set token.
        User starts as inactive and unverified by default.
        When they verify their email, they keep this token.
        Returns: {"created": bool, "error": str|None}
        """
        email = email.lower()

        # Check if user already exists
        existing = await self.get_user_by_email(email)
        if existing:
            return {"created": False, "error": "User already exists"}

        await self.users.insert_one({
            "email": email,
            "intercept_token": token,
            "verified": False,
            "active": active,
            "created_at": datetime.utcnow(),
        })
        return {"created": True, "error": None}
