"""
Claude Code Proxy - Entry Point

Minimal entry point that imports the app from the api module.
Run with: uv run uvicorn server:app --host 0.0.0.0 --port 8082
"""

from api.app import app, create_app

__all__ = ["app", "create_app"]

if __name__ == "__main__":
    import os
    import uvicorn

    log_level = os.getenv("LOG_LEVEL", "info")
    uvicorn.run(app, host="0.0.0.0", port=8082, log_level=log_level)
