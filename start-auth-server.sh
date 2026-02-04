#!/bin/bash
# Load environment variables from .env and start auth server

cd "$(dirname "$0")"

# Export all variables from .env
set -a
source .env
set +a

# Start the auth server
exec uv run uvicorn auth_server:app --host 0.0.0.0 --port 8083
