# cc-zol

Use **Claude Code CLI** with any OpenAI-compatible API via email verification.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  User's Machine                                                 │
│                                                                 │
│  cc-zol CLI                                                     │
│      │                                                          │
│      ├──► Login (email/code) ────────► Auth Server ◄── MongoDB  │
│      │                                      │                   │
│      ├──► Fetch config (with token) ────────┘                   │
│      │         │                                                │
│      │         │ Returns: api_key, base_url, model              │
│      │         │ (passed in memory, never saved to disk)        │
│      │         ▼                                                │
│      └──► Local Proxy (with config) ──► Claude Code             │
│                 │                                               │
└─────────────────┼───────────────────────────────────────────────┘
                  │
                  ▼
           Provider API (OpenAI-compatible)
```

**Key security feature:** Users never see the provider API key. It's fetched from your auth server and passed in memory only.

---

## For Users

### Install (one command)

```bash
curl -fsSL https://raw.githubusercontent.com/eladcandroid/cc-zol/main/install.sh | bash
```

This installs `uv` (if needed) and the `cc-zol` CLI.

### Run

```bash
cc-zol
```

On first run:
1. Enter your email
2. Check email for verification code
3. Enter code
4. Claude Code starts automatically

### Commands

```bash
cc-zol              # Login if needed, then start Claude
cc-zol login        # Force re-login with new email
cc-zol logout       # Clear saved credentials
cc-zol model        # Change the model
cc-zol status       # Show current status
cc-zol stop         # Stop the background server
cc-zol update       # Update to the latest version
```

---

## For Admins (Hosting)

### Quick Setup (one command)

```bash
curl -fsSL https://raw.githubusercontent.com/eladcandroid/cc-zol/main/setup-server.sh | bash
```

This clones the repo to `~/cc-zol`, installs dependencies, and shows next steps.

### Manual Setup

#### 1. Prerequisites

**MongoDB** (choose one):
```bash
# Docker (easiest)
docker run -d --name mongodb -p 27017:27017 mongo:latest

# macOS
brew install mongodb-community && brew services start mongodb-community

# Ubuntu/Debian
sudo apt install mongodb && sudo systemctl start mongodb
```

#### 2. Clone & Configure

```bash
git clone https://github.com/eladcandroid/cc-zol.git
cd cc-zol
cp .env.example .env
```

Edit `.env` with your settings:
```dotenv
# Required: Admin password for dashboard
ADMIN_PASSWORD=your-secure-password

# Required: Email verification (Gmail example)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your@gmail.com

# Required: Your OpenAI-compatible provider (users never see this)
PROVIDER_API_KEY=your-api-key
PROVIDER_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o
```

#### 3. Run the Auth Server

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run server
uv run uvicorn auth_server:app --host 0.0.0.0 --port 8083
```

#### 4. Production (PM2)

```bash
npm install -g pm2
pm2 start "uv run uvicorn auth_server:app --host 0.0.0.0 --port 8083" --name cc-zol-auth
pm2 save
pm2 startup  # Auto-start on reboot
```

#### 5. Update Auth Server URL

In `zol/config.py`, set your hosted URL:
```python
AUTH_SERVER_URL = "https://your-domain.com"
```

Then commit and push. Users installing from your repo will connect to your server.

### Admin Dashboard

Access at `http://your-server:8083/admin` with your `ADMIN_PASSWORD`.

Features:
- View all users and their status
- **Add pre-configured users** with custom tokens (inactive by default)
- Edit user tokens
- Enable/disable users
- Delete users

---

## Security Model

### What Users See

Users only have access to:
```
~/.cc-zol/config.json
{
  "email": "user@example.com",
  "token": "abc123..."    ← Auth token only (not the API key)
}
```

### What Users Never See

- `PROVIDER_API_KEY` - Your OpenAI/NVIDIA/etc API key
- `PROVIDER_BASE_URL` - The actual API endpoint
- Any provider credentials

### How It Works

1. User logs in with email → gets auth token
2. On each `cc-zol` start, CLI fetches provider config from auth server
3. Config is passed to local proxy via environment variables (in memory)
4. **Nothing is written to disk** - config is fetched fresh each session

This means:
- You control the API key centrally
- Revoking a user = they can't fetch config anymore
- No risk of users sharing/leaking your API key

---

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `PROVIDER_API_KEY` | Your API key (users never see this) | required |
| `PROVIDER_BASE_URL` | API endpoint URL | `https://api.openai.com/v1` |
| `MODEL` | Model for all requests | `gpt-4o` |
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
└── install.sh           # User installer
```
