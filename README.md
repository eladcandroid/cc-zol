# cc-zol

Use **Claude Code CLI** with any OpenAI-compatible API via email verification.

## How It Works

```
┌──────────────────────────────────────────────────────────┐
│  Your Machine                                            │
│                                                          │
│  cc-zol ──► Login (email) ──► Auth Server ──► MongoDB    │
│    │                              │                      │
│    │                         (hosted by admin)           │
│    │                                                     │
│    └──► Local Proxy ──► Claude Code                      │
│              │                                           │
└──────────────┼───────────────────────────────────────────┘
               │
               ▼
        Provider API (OpenAI-compatible)
```

## Quick Start (Users)

### 1. Install
```bash
# Using uv (recommended)
uv tool install git+https://github.com/eladcandroid/cc-zol.git

# Or using pip
pip install git+https://github.com/eladcandroid/cc-zol.git
```

### 2. Run
```bash
cc-zol
```

On first run:
1. Enter your email
2. Check email for verification code
3. Enter code
4. Select a model
5. Claude Code starts automatically

### Commands
```bash
cc-zol              # Login if needed, then start Claude
cc-zol login        # Force re-login with new email
cc-zol logout       # Clear saved credentials
cc-zol model        # Change the model
cc-zol status       # Show current status
cc-zol stop         # Stop the background server
```

---

## Hosting (Admins)

If you want to host your own cc-zol auth server:

### Prerequisites
- [uv](https://github.com/astral-sh/uv)
- MongoDB running locally (or remote)
- SMTP credentials (Gmail app password works)

### 1. Clone & Configure
```bash
git clone https://github.com/eladcandroid/cc-zol.git
cd cc-zol
cp .env.example .env
```

Edit `.env`:
```dotenv
# Auth Server
MONGODB_URI=mongodb://localhost:27017
ADMIN_PASSWORD=your-admin-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your@gmail.com

# Provider (for local proxy)
PROVIDER_API_KEY=your-api-key
PROVIDER_BASE_URL=https://integrate.api.nvidia.com/v1
MODEL=moonshotai/kimi-k2.5
```

### 2. Run Auth Server

**With PM2 (recommended):**
```bash
# Create ecosystem.config.cjs with your settings (see CLAUDE.md)
pm2 start ecosystem.config.cjs
pm2 save
```

**Or directly:**
```bash
uv run uvicorn auth_server:app --host 0.0.0.0 --port 8083
```

### 3. Update Auth Server URL

In `zol/config.py`, set your hosted URL:
```python
AUTH_SERVER_URL = "https://your-domain.com"
```

### 4. Publish
```bash
git add -A
git commit -m "Configure for production"
git push
```

Users can now install your configured version.

---

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `PROVIDER_API_KEY` | Your API key | required |
| `PROVIDER_BASE_URL` | API endpoint URL | `https://api.openai.com/v1` |
| `MODEL` | Model for all requests | `moonshotai/kimi-k2.5` |
| `MONGODB_URI` | MongoDB connection | `mongodb://localhost:27017` |
| `ADMIN_PASSWORD` | Admin UI password | `admin` |
| `SMTP_HOST` | SMTP server | `""` (console fallback) |

See [`.env.example`](.env.example) for all options.

---

## Telegram Bot (Optional)

Control Claude Code remotely via Telegram:

1. Get a bot token from [@BotFather](https://t.me/BotFather)
2. Add to `.env`:
   ```dotenv
   TELEGRAM_BOT_TOKEN=your-bot-token
   ALLOWED_TELEGRAM_USER_ID=your-user-id
   CLAUDE_WORKSPACE=./agent_workspace
   ```
3. Start the server and message your bot

---

## Development

### Run Tests
```bash
uv run pytest
```

### Project Structure
```
cc-zol/
├── zol/                 # CLI module
├── auth/                # Authentication (MongoDB, email)
├── api/                 # FastAPI proxy server
├── providers/           # OpenAI-compatible provider
├── messaging/           # Telegram bot (optional)
├── cli/                 # Claude subprocess manager
├── server.py            # Local proxy entry point
├── auth_server.py       # Auth server entry point
└── ecosystem.config.cjs # PM2 config (gitignored)
```

### Adding a Provider

Extend `BaseProvider` in `providers/base.py`:

```python
from providers.base import BaseProvider, ProviderConfig

class MyProvider(BaseProvider):
    async def complete(self, request):
        # Make API call, return raw JSON
        pass

    async def stream_response(self, request, input_tokens=0):
        # Yield Anthropic SSE format events
        pass

    def convert_response(self, response_json, original_request):
        # Convert to Anthropic response format
        pass
```
