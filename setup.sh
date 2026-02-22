#!/bin/bash
# setup.sh — TUI/Terminal Automation Tools einrichten
# Funktioniert unter Linux (Fedora/Ubuntu) und Windows (Git Bash)
# Führe aus: bash ~/tools/setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IS_WINDOWS=false
[[ "$OS" == "Windows_NT" ]] && IS_WINDOWS=true

echo "=== TUI Tools Setup ==="

# --- Zielverzeichnis für Scripts ---
if $IS_WINDOWS; then
    BIN_DIR="$HOME/bin"
else
    BIN_DIR="$HOME/.local/bin"
fi
mkdir -p "$BIN_DIR"

# --- System-Pakete (nur Linux) ---
if ! $IS_WINDOWS; then
    echo ""
    echo "--- System-Pakete ---"
    if command -v dnf &>/dev/null; then
        sudo dnf install -y tmux wkhtmltoimage neovim
    elif command -v apt &>/dev/null; then
        sudo apt install -y tmux wkhtmltoimage neovim
    else
        echo "Unbekannter Paketmanager — bitte manuell installieren: tmux, wkhtmltoimage, neovim"
    fi
fi

# --- tmux2html (nur Linux, braucht tmux) ---
if ! $IS_WINDOWS; then
    echo ""
    echo "--- tmux2html ---"
    if command -v uv &>/dev/null; then
        uv tool install tmux2html
        echo "tmux2html installiert"
    else
        echo "uv nicht gefunden — bitte uv installieren: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

# --- mcp-tui-driver (Rust via cargo) ---
echo ""
echo "--- mcp-tui-driver ---"
if command -v cargo &>/dev/null; then
    cargo install --git https://github.com/michaellee8/mcp-tui-driver
    echo "mcp-tui-driver installiert"
else
    echo "cargo nicht gefunden — bitte Rust installieren: https://rustup.rs"
    exit 1
fi

# --- neovim-mcp (Go binary) ---
echo ""
echo "--- neovim-mcp ---"
if command -v go &>/dev/null; then
    TMP=$(mktemp -d)
    git clone https://github.com/cousine/neovim-mcp "$TMP/neovim-mcp"
    cd "$TMP/neovim-mcp"
    if $IS_WINDOWS; then
        go build -o "$BIN_DIR/neovim-mcp.exe" .
    else
        go build -o "$BIN_DIR/neovim-mcp" .
        chmod +x "$BIN_DIR/neovim-mcp"
    fi
    rm -rf "$TMP"
    echo "neovim-mcp installiert nach $BIN_DIR"
else
    echo "go nicht gefunden — bitte Go installieren: https://go.dev/doc/install"
    exit 1
fi

# --- Scripts kopieren ---
echo ""
echo "--- Scripts ---"
# Plattformübergreifende Scripts
for script in ide nvim-ide-open nvim-split wez-send-key; do
    cp "$SCRIPT_DIR/$script" "$BIN_DIR/$script"
    chmod +x "$BIN_DIR/$script" 2>/dev/null || true
    echo "$script -> $BIN_DIR/$script"
done

# Nur Linux: tmux2png
if ! $IS_WINDOWS; then
    cp "$SCRIPT_DIR/tmux2png" "$BIN_DIR/tmux2png"
    chmod +x "$BIN_DIR/tmux2png"
    echo "tmux2png -> $BIN_DIR/tmux2png"
fi

# --- Config-Symlinks (nvim, yazi, wezterm) ---
echo ""
echo "--- Config-Symlinks ---"
mkdir -p "$HOME/.config"

link_config() {
    local name="$1" src="$2" dest="$3"
    if [ -e "$dest" ] && [ ! -L "$dest" ]; then
        echo "$name: $dest existiert bereits (kein Symlink) — manuell pruefen"
    else
        rm -f "$dest"
        if $IS_WINDOWS; then
            cp -r "$src" "$dest"
            echo "$name: kopiert nach $dest"
        else
            ln -s "$src" "$dest"
            echo "$name: $dest -> $src"
        fi
    fi
}

link_config "nvim"    "$SCRIPT_DIR/.config/nvim"    "$HOME/.config/nvim"
link_config "yazi"    "$SCRIPT_DIR/.config/yazi"    "$HOME/.config/yazi"
link_config "wezterm" "$SCRIPT_DIR/.config/wezterm" "$HOME/.config/wezterm"

# --- Claude Code Skill ---
echo ""
echo "--- Claude Code Skill ---"
mkdir -p ~/.claude/skills/tui-screenshot
cp "$SCRIPT_DIR/tui-screenshot-skill.md" ~/.claude/skills/tui-screenshot/SKILL.md
echo "tui-screenshot Skill installiert"

# --- Claude Code MCP-Konfiguration ---
echo ""
echo "--- MCP-Konfiguration ---"
CLAUDE_JSON="$HOME/.claude.json"
MCP_JSON="$SCRIPT_DIR/mcps.json"

if [ ! -f "$CLAUDE_JSON" ]; then
    echo '{"mcpServers":{}}' > "$CLAUDE_JSON"
fi

python3 -c "
import json, sys
with open('$CLAUDE_JSON') as f:
    config = json.load(f)
with open('$MCP_JSON') as f:
    new_mcps = json.load(f)
config.setdefault('mcpServers', {}).update(new_mcps)
with open('$CLAUDE_JSON', 'w') as f:
    json.dump(config, f, indent=2)
print('MCPs eingetragen:', list(new_mcps.keys()))
"

echo ""
echo "=== Setup abgeschlossen ==="
echo ""
echo "Naechste Schritte:"
echo "  1. Neues Terminal oeffnen (damit PATH aktualisiert ist)"
echo "  2. Claude Code neu starten (damit MCPs geladen werden)"
echo "  3. Test: ide ~/projekte"
if ! $IS_WINDOWS; then
    echo "  4. Test: tmux2png"
fi
