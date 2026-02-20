#!/bin/bash
# setup.sh — TUI/Terminal Automation Tools einrichten
# Führe aus: bash ~/tools/setup.sh

set -euo pipefail

echo "=== TUI Tools Setup ==="

# --- System-Pakete ---
echo ""
echo "--- System-Pakete ---"
if command -v dnf &>/dev/null; then
    sudo dnf install -y tmux wkhtmltoimage neovim
elif command -v apt &>/dev/null; then
    sudo apt install -y tmux wkhtmltoimage neovim
else
    echo "⚠ Unbekannter Paketmanager — bitte manuell installieren: tmux, wkhtmltoimage, neovim"
fi

# --- tmux2html (Python via uv) ---
echo ""
echo "--- tmux2html ---"
if command -v uv &>/dev/null; then
    uv tool install tmux2html
    echo "✅ tmux2html installiert"
else
    echo "⚠ uv nicht gefunden — bitte uv installieren: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# --- mcp-tui-driver (Rust via cargo) ---
echo ""
echo "--- mcp-tui-driver ---"
if command -v cargo &>/dev/null; then
    cargo install --git https://github.com/michaellee8/mcp-tui-driver
    echo "✅ mcp-tui-driver installiert"
else
    echo "⚠ cargo nicht gefunden — bitte Rust installieren: https://rustup.rs"
    exit 1
fi

# --- neovim-mcp (Go binary) ---
echo ""
echo "--- neovim-mcp ---"
if command -v go &>/dev/null; then
    TMP=$(mktemp -d)
    git clone https://github.com/cousine/neovim-mcp "$TMP/neovim-mcp"
    cd "$TMP/neovim-mcp"
    go build -o ~/.local/bin/neovim-mcp .
    chmod +x ~/.local/bin/neovim-mcp
    rm -rf "$TMP"
    echo "✅ neovim-mcp installiert nach ~/.local/bin/neovim-mcp"
else
    echo "⚠ go nicht gefunden — bitte Go installieren: https://go.dev/doc/install"
    exit 1
fi

# --- tmux2png Script ---
echo ""
echo "--- tmux2png ---"
mkdir -p ~/.local/bin
cp "$(dirname "$0")/tmux2png" ~/.local/bin/tmux2png
chmod +x ~/.local/bin/tmux2png
echo "✅ tmux2png installiert nach ~/.local/bin/tmux2png"

# --- Claude Code Skill ---
echo ""
echo "--- Claude Code Skill ---"
mkdir -p ~/.claude/skills/tui-screenshot
cp "$(dirname "$0")/tui-screenshot-skill.md" ~/.claude/skills/tui-screenshot/SKILL.md
echo "✅ tui-screenshot Skill installiert"

# --- Claude Code MCP-Konfiguration ---
echo ""
echo "--- MCP-Konfiguration ---"
CLAUDE_JSON="$HOME/.claude.json"
MCP_JSON="$(dirname "$0")/mcps.json"

if [ ! -f "$CLAUDE_JSON" ]; then
    echo '{"mcpServers":{}}' > "$CLAUDE_JSON"
fi

python3 - <<EOF
import json

with open("$CLAUDE_JSON") as f:
    config = json.load(f)

with open("$MCP_JSON") as f:
    new_mcps = json.load(f)

config.setdefault("mcpServers", {}).update(new_mcps)

with open("$CLAUDE_JSON", "w") as f:
    json.dump(config, f, indent=2)

print("✅ MCPs in ~/.claude.json eingetragen:", list(new_mcps.keys()))
EOF

echo ""
echo "=== Setup abgeschlossen ==="
echo ""
echo "Nächste Schritte:"
echo "  1. Neues Terminal öffnen (damit PATH aktualisiert ist)"
echo "  2. Claude Code neu starten (damit MCPs geladen werden)"
echo "  3. Nvim mit Socket starten: nvim --listen /tmp/nvim.sock"
echo "  4. Test: tmux2png"
