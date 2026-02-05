# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cc-zol is a CLI that lets anyone use Claude Code with any OpenAI-compatible API. It features:
- **Email verification** for user authentication
- **Local proxy** that translates Anthropic API → OpenAI format
- **Remote auth server** for centralized user management
- **Secure config delivery** - users never see the provider API key
- **Optional Telegram bot** for remote task control

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER'S MACHINE                          │
│                                                                 │
│  cc-zol CLI                                                     │
│      │                                                          │
│      ├─► Login ──────────────────────► Auth Server (remote)     │
│      │         POST /auth/send-code     │                       │
│      │         POST /auth/verify        ▼                       │
│      │                              MongoDB                     │
│      │                                                          │
│      ├─► Fetch config ───────────────► GET /auth/config         │
│      │   (with token)                   │                       │
│      │         │                        │ Returns provider      │
│      │         │ ◄──────────────────────┘ api_key, url, model   │
│      │         │                                                │
│      │         │ (in memory only - never written to disk)       │
│      │         ▼                                                │
│      └─► Start local proxy (with config as env vars)            │
│              │                                                  │
│              ▼                                                  │
│      Claude Code CLI                                            │
│      (ANTHROPIC_BASE_URL=localhost)                             │
│               │                                                 │
└───────────────┼─────────────────────────────────────────────────┘
                │
                ▼ (OpenAI format)
        Provider API (e.g., OpenAI, NVIDIA NIM)
```

## Security Model

### What Users See
```
~/.cc-zol/config.json
{
  "email": "user@example.com",
  "token": "abc123..."    ← Auth token only
}
```

### What Users Never See
- `PROVIDER_API_KEY` - fetched from auth server, passed in memory
- `PROVIDER_BASE_URL` - fetched from auth server, passed in memory
- Provider credentials are **never written to disk** on user's machine

### Config Flow
1. User logs in → gets auth token (stored locally)
2. On each `cc-zol` start → fetch `/auth/config` with token
3. Server returns provider config (api_key, url, model)
4. Config passed to local proxy as environment variables
5. Fresh config fetched each session

## Installation

### For Users (one command)
```bash
curl -fsSL https://raw.githubusercontent.com/eladcandroid/cc-zol/main/install.sh | bash
```

### For Admins (auth server setup)
```bash
curl -fsSL https://raw.githubusercontent.com/eladcandroid/cc-zol/main/setup-server.sh | bash
```

## Commands

### Run cc-zol (Main CLI)
```bash
cc-zol              # Login if needed, then start Claude
cc-zol login        # Force re-login with new email
cc-zol logout       # Clear saved credentials
cc-zol model        # Change the model
cc-zol status       # Show current user and server status
cc-zol stop         # Stop the background server
cc-zol update       # Update to the latest version
```

### Run Auth Server (for hosting)
```bash
# With PM2 (recommended)
pm2 start "uv run uvicorn auth_server:app --host 0.0.0.0 --port 8083" --name cc-zol-auth

# Or directly
uv run uvicorn auth_server:app --host 0.0.0.0 --port 8083
```

### Run Local Proxy Manually
```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8082
```

### Run Tests
```bash
uv run pytest                        # Run all tests
uv run pytest tests/test_api.py      # Run single test file
uv run pytest -k "test_name"         # Run tests matching pattern
uv run pytest -x                     # Stop on first failure
```

## Core Packages

### zol/ - CLI Module
- `main.py` - Click CLI entry point (cc-zol commands)
- `config.py` - Local config (~/.cc-zol/), AUTH_SERVER_URL
- `server_manager.py` - Background uvicorn process management
- `tui.py` - Interactive prompts, model selection

### auth/ - Authentication Module (used by auth server)
- `models.py` - User Pydantic model
- `database.py` - MongoDB operations (motor)
- `email_service.py` - SMTP email + console fallback
- `middleware.py` - FastAPI auth middleware

### api/ - Server Routes
- `app.py` - FastAPI app (local proxy, no auth)
- `routes.py` - `/v1/messages` endpoint (proxies to provider)
- `auth_routes.py` - `/auth/*` endpoints (login, verify, config)
- `admin_routes.py` - `/admin/*` endpoints (user management UI)
- `request_utils.py` - Optimizations (quota mocking, title skip)

### providers/ - API Provider
- `base.py` - Abstract `BaseProvider` class
- `openai_provider.py` - OpenAI-compatible provider
- `openai_mixins.py` - Request/response conversion
- `utils/` - SSE builder, thinking parser, tool extraction

### messaging/ - Telegram Bot (optional)
- `telegram.py` - Telegram bot adapter
- `handler.py` - Message handler
- `tree_*.py` - Conversation threading

### cli/ - Claude Code Subprocess (for Telegram)
- `manager.py` - Session pooling
- `session.py` - CLI session wrapper

## Key Files

| File | Purpose |
|------|---------|
| `server.py` | Local proxy entry point |
| `auth_server.py` | Remote auth server entry point |
| `install.sh` | User installer (curl \| bash) |
| `setup-server.sh` | Admin server setup script |
| `ecosystem.config.cjs` | PM2 config for auth server (gitignored) |
| `.env` | Local secrets (gitignored) |
| `.env.example` | Template for .env |

## Configuration

### Auth Server URL
Set in `zol/config.py`:
```python
AUTH_SERVER_URL = "http://localhost:8083"  # Or your hosted URL
```

### Environment Variables (.env)

**For Auth Server:**
```
MONGODB_URI=mongodb://localhost:27017
ADMIN_PASSWORD=your-admin-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=app-password
SMTP_FROM_EMAIL=your@gmail.com

# Provider config (served to authenticated users via /auth/config)
PROVIDER_API_KEY=your-api-key
PROVIDER_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o
```

## API Endpoints

### Auth Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/send-code` | POST | Send verification code to email |
| `/auth/verify` | POST | Verify code, return auth token |
| `/auth/config` | GET | Get provider config (requires token) |
| `/admin/` | GET | Admin dashboard UI |
| `/admin/api/users` | GET | List all users |
| `/admin/api/users` | POST | Create pre-configured user |
| `/admin/api/users/{email}` | PATCH | Update user (token, active, verified) |
| `/admin/api/users/{email}` | DELETE | Delete user |

## Local Config

User credentials stored in `~/.cc-zol/`:
- `config.json` - Email and auth token (not API key)
- `server.pid` - Background server PID
- `server.port` - Current server port
- `server.log` - Server logs

## MongoDB Schema

Collection: `cc_zol.users`
```json
{
    "email": "user@gmail.com",
    "verification_code": "123456",
    "verification_code_expires": datetime,
    "intercept_token": "abc123...",
    "verified": true,
    "active": true,
    "created_at": datetime,
    "last_logged_in": datetime
}
```
