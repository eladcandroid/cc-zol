#!/bin/bash
# cc-zol installer - run with: curl -fsSL https://raw.githubusercontent.com/eladcandroid/cc-zol/main/install.sh | bash

set -e

echo "Installing cc-zol..."

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install cc-zol
echo "Installing cc-zol CLI..."
uv tool install git+https://github.com/eladcandroid/cc-zol.git --force

echo ""
echo "✓ cc-zol installed successfully!"
echo ""
echo "Run 'cc-zol' to get started."
echo ""
echo "If 'cc-zol' is not found, restart your terminal or run:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
