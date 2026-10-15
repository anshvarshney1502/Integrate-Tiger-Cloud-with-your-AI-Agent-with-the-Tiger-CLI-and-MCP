#!/usr/bin/env bash
# ==============================================================================
# setup_tiger.sh - Automated installer and configuration for Tiger CLI & Tiger MCP
# ==============================================================================

set -euo pipefail

echo "🐅 Starting Tiger Cloud CLI and MCP Setup..."

# 1. Check if tiger CLI exists in PATH or ~/.local/bin
TIGER_BIN=""
if command -v tiger &> /dev/null; then
    TIGER_BIN=$(command -v tiger)
elif [ -x "$HOME/.local/bin/tiger" ]; then
    TIGER_BIN="$HOME/.local/bin/tiger"
    export PATH="$HOME/.local/bin:$PATH"
fi

if [ -z "$TIGER_BIN" ]; then
    echo "📥 Tiger CLI not found. Downloading and installing..."
    curl -fsSL https://cli.tigerdata.com | sh
    export PATH="$HOME/.local/bin:$PATH"
    TIGER_BIN="$HOME/.local/bin/tiger"
fi

echo "✅ Tiger CLI is available at: $TIGER_BIN"
"$TIGER_BIN" version || true

# 2. Check Tiger MCP server configuration
echo "🔧 Configuring Tiger MCP server for AI agents..."
CLIENT="${1:-antigravity}"

case "$CLIENT" in
    antigravity)
        echo "Configuring for Google Antigravity..."
        "$TIGER_BIN" mcp install antigravity || true
        ;;
    claude-code)
        echo "Configuring for Claude Code..."
        "$TIGER_BIN" mcp install claude-code || true
        ;;
    cursor)
        echo "Configuring for Cursor IDE..."
        "$TIGER_BIN" mcp install cursor || true
        ;;
    vscode)
        echo "Configuring for Visual Studio Code..."
        "$TIGER_BIN" mcp install vscode || true
        ;;
    gemini)
        echo "Configuring for Gemini CLI..."
        "$TIGER_BIN" mcp install gemini || true
        ;;
    *)
        echo "Configuring for $CLIENT..."
        "$TIGER_BIN" mcp install "$CLIENT" || true
        ;;
esac

# 3. Verification
echo ""
echo "🚀 Running Tiger MCP verification test..."
python3 scripts/verify_mcp.py

echo ""
echo "🎉 Tiger Cloud CLI & MCP setup complete!"
echo "Next step: Log in to Tiger Cloud with:"
echo "  tiger auth login"
