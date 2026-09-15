#!/bin/bash
# setup.sh — TUI/Terminal Automation Tools einrichten (Linux, GNOME Wayland)
# Führe aus: bash ~/projects/tools/setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"

echo "=== TUI Tools Setup ==="
mkdir -p "$BIN_DIR"

# --- System-Pakete ---
echo ""
echo "--- System-Pakete ---"
PKGS="tmux wkhtmltopdf timg ydotool ImageMagick"
if command -v dnf &>/dev/null; then
    sudo dnf install -y $PKGS
elif command -v apt &>/dev/null; then
    sudo apt install -y tmux wkhtmltopdf timg ydotool imagemagick
else
    echo "Unbekannter Paketmanager — bitte manuell installieren: $PKGS"
fi

# --- tmux2html (liefert das HTML für tmux2png) ---
echo ""
echo "--- tmux2html ---"
if command -v uv &>/dev/null; then
    uv tool install tmux2html
    echo "tmux2html installiert"
else
    echo "uv nicht gefunden — bitte uv installieren: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
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

# --- Scripts ---
echo ""
echo "--- Scripts ---"
install_script() {
    local src="$1" name="$2"
    cp "$SCRIPT_DIR/$src" "$BIN_DIR/$name"
    chmod +x "$BIN_DIR/$name"
    echo "$src -> $BIN_DIR/$name"
}

install_script tmux2png       tmux2png
install_script gui-screenshot.sh gui-screenshot
install_script img-proto-test img-proto-test

# mailbox als Verknüpfung, damit Änderungen im Repo sofort gelten; Konten-Vorlage nur anlegen, wenn keine existiert
ln -sfn "$SCRIPT_DIR/mailbox.py" "$BIN_DIR/mailbox"
echo "mailbox.py -> $BIN_DIR/mailbox (Verknüpfung)"
mkdir -p "$HOME/.config/mail" && chmod 700 "$HOME/.config/mail"
if [ ! -f "$HOME/.config/mail/accounts.toml" ]; then
    cp "$SCRIPT_DIR/mailbox-accounts.example.toml" "$HOME/.config/mail/accounts.toml"
    chmod 600 "$HOME/.config/mail/accounts.toml"
    echo "Vorlage nach ~/.config/mail/accounts.toml kopiert, Konten und Passwortdateien eintragen"
fi

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
import json
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
echo "  3. Test: tmux2png"
