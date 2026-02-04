#!/bin/bash
# cc-zol Auth Server Setup
# Run with: curl -fsSL https://raw.githubusercontent.com/eladcandroid/cc-zol/main/setup-server.sh | bash

set -e

INSTALL_DIR="${CC_ZOL_DIR:-$HOME/cc-zol}"

echo "=== cc-zol Auth Server Setup ==="
echo ""

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Clone repo
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning cc-zol to $INSTALL_DIR..."
    git clone https://github.com/eladcandroid/cc-zol.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install dependencies
echo "Installing Python dependencies..."
uv sync

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from template."
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo ""
echo "1. Start MongoDB (choose one):"
echo ""
echo "   # Option A: Docker (recommended)"
echo "   docker run -d --name mongodb -p 27017:27017 mongo:latest"
echo ""
echo "   # Option B: Install locally"
echo "   # macOS: brew install mongodb-community && brew services start mongodb-community"
echo "   # Ubuntu: sudo apt install mongodb && sudo systemctl start mongodb"
echo ""
echo "2. Configure .env:"
echo "   cd $INSTALL_DIR"
echo "   nano .env  # or vim, code, etc."
echo ""
echo "   Required settings:"
echo "   - ADMIN_PASSWORD (for admin dashboard)"
echo "   - SMTP_* settings (for email verification)"
echo "   - PROVIDER_API_KEY (your OpenAI-compatible API key)"
echo "   - PROVIDER_BASE_URL (API endpoint)"
echo ""
echo "3. Start the auth server:"
echo "   cd $INSTALL_DIR"
echo "   uv run uvicorn auth_server:app --host 0.0.0.0 --port 8083"
echo ""
echo "4. (Optional) Use PM2 for production:"
echo "   npm install -g pm2"
echo "   pm2 start \"uv run uvicorn auth_server:app --host 0.0.0.0 --port 8083\" --name cc-zol-auth"
echo "   pm2 save"
echo ""
echo "Admin dashboard will be at: http://your-server:8083/admin"
