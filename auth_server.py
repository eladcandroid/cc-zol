"""Auth server entry point.

This is the REMOTE AUTH SERVER that you host. It handles:
- Email verification (/auth/send-code, /auth/verify)
- User database (MongoDB)
- Admin UI (/admin)

Users' cc-zol CLI connects here for login only.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.auth_routes import router as auth_router
from api.admin_routes import router as admin_router
from config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    logger.info("Starting Auth Server...")

    # Initialize MongoDB
    user_db = None
    email_service = None
    try:
        from auth.database import UserDatabase
        from auth.email_service import EmailService

        user_db = UserDatabase(settings.mongodb_uri)
        await user_db.connect()
        logger.info("MongoDB connected")

        email_service = EmailService(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
            smtp_from_email=settings.smtp_from_email,
        )
        if email_service.is_configured:
            logger.info("Email service configured with SMTP")
        else:
            logger.info("Email service using console fallback")

    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        raise

    # Store in app state
    app.state.user_db = user_db
    app.state.email_service = email_service
    app.state.settings = settings

    yield

    # Cleanup
    if user_db:
        await user_db.close()
    logger.info("Auth server shutting down...")


def create_auth_app() -> FastAPI:
    """Create the auth server application."""
    app = FastAPI(
        title="cc-zol Auth Server",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Register routes
    app.include_router(auth_router)
    app.include_router(admin_router)

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/")
    async def root():
        return {"service": "cc-zol-auth", "status": "ok"}

    return app


app = create_auth_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)
