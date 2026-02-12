"""FastAPI application factory and configuration.

This is the LOCAL PROXY that users run. It only proxies requests to the provider.
Authentication is handled by the remote auth server during login.
"""

import os
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .routes import router
from .dependencies import cleanup_provider
from providers.exceptions import ProviderError
from config.settings import get_settings

# Configure logging (atomic - only on true fresh start)
LOG_FILE = os.path.join(os.path.expanduser("~/.cc-zol"), "server.log")

# Check if logging is already configured (e.g., hot reload)
# If handlers exist, skip setup to avoid clearing logs mid-session
if not logging.root.handlers:
    # Fresh start - clear log file and configure
    open(LOG_FILE, "w", encoding="utf-8").close()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")],
    )

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID for log correlation."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Suppress noisy uvicorn logs
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    logger.info("Starting Claude Code Proxy (local)...")

    # Initialize messaging platform if configured (for Telegram bot)
    messaging_platform = None
    message_handler = None
    cli_manager = None

    # Opt-in to future behavior for python-telegram-bot
    os.environ["PTB_TIMEDELTA"] = "1"

    try:
        if settings.telegram_bot_token:
            from messaging.telegram import TelegramPlatform
            from messaging.handler import ClaudeMessageHandler
            from messaging.session import SessionStore
            from cli.manager import CLISessionManager

            # Setup workspace
            workspace = (
                os.path.abspath(settings.allowed_dir)
                if settings.allowed_dir
                else os.getcwd()
            )
            os.makedirs(workspace, exist_ok=True)

            data_path = os.path.abspath(settings.claude_workspace)
            os.makedirs(data_path, exist_ok=True)

            allowed_dirs = [workspace] if settings.allowed_dir else []
            cli_manager = CLISessionManager(
                workspace_path=workspace,
                api_url="http://localhost:8082/v1",
                allowed_dirs=allowed_dirs,
                max_sessions=settings.max_cli_sessions,
            )

            session_store = SessionStore(
                storage_path=os.path.join(data_path, "sessions.json")
            )

            messaging_platform = TelegramPlatform(
                bot_token=settings.telegram_bot_token,
                allowed_user_id=settings.allowed_telegram_user_id,
            )

            message_handler = ClaudeMessageHandler(
                platform=messaging_platform,
                cli_manager=cli_manager,
                session_store=session_store,
            )

            # Restore tree state if available
            if session_store._trees:
                logger.info(
                    f"Restoring {len(session_store._trees)} conversation trees..."
                )
                from messaging.tree_queue import TreeQueueManager

                message_handler.tree_queue = TreeQueueManager.from_dict(
                    {
                        "trees": session_store._trees,
                        "node_to_tree": session_store._node_to_tree,
                    }
                )
                if message_handler.tree_queue.cleanup_stale_nodes() > 0:
                    session_store._trees = message_handler.tree_queue.to_dict()["trees"]
                    session_store._node_to_tree = message_handler.tree_queue.to_dict()[
                        "node_to_tree"
                    ]
                    session_store._save()

            messaging_platform.on_message(message_handler.handle_message)
            await messaging_platform.start()
            logger.info("Telegram platform started with message handler")

    except ImportError as e:
        logger.warning(f"Messaging module import error: {e}")
    except Exception as e:
        logger.error(f"Failed to start messaging platform: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Store in app state
    app.state.messaging_platform = messaging_platform
    app.state.message_handler = message_handler
    app.state.cli_manager = cli_manager

    yield

    # Cleanup
    if messaging_platform:
        await messaging_platform.stop()
    if cli_manager:
        await cli_manager.stop_all()
    await cleanup_provider()
    logger.info("Server shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Claude Code Proxy",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Add request ID middleware for log correlation
    app.add_middleware(RequestIDMiddleware)

    # Register routes (proxy only, no auth routes)
    app.include_router(router)

    # Exception handlers
    @app.exception_handler(ProviderError)
    async def provider_error_handler(request: Request, exc: ProviderError):
        """Handle provider-specific errors and return Anthropic format."""
        logger.error(f"Provider Error: {exc.error_type} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_anthropic_format(),
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """Handle general errors and return Anthropic format."""
        logger.error(f"General Error: {str(exc)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": "An unexpected error occurred.",
                },
            },
        )

    return app


# Default app instance for uvicorn
app = create_app()
