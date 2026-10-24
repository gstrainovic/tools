#!/bin/bash
# link.sh — Verknüpfungen aus diesem Repo anlegen, idempotent, ohne sudo:
#   Scripts nach ~/.local/bin, Claude-Skills (skills/<name>/ und ~/projects/skills-privat/skills/<name>/)
#   nach ~/.claude/skills/<name>, die globale ~/.claude/CLAUDE.md aus ~/projects/skills-privat/claude/.
# Wird von setup.sh aufgerufen und kann allein laufen: bash ~/projects/tools/link.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
SKILL_DIR="$HOME/.claude/skills"
mkdir -p "$BIN_DIR" "$SKILL_DIR"

# Verknüpfung setzen; eine Datei am Ziel (frühere Kopie aus setup.sh) wird ersetzt,
# ein echter Ordner bleibt unangetastet
link() {
    local src="$1" dst="$2"
    if [[ -d "$dst" && ! -L "$dst" ]]; then
        echo "übersprungen: $dst ist ein Ordner, keine Verknüpfung, bitte von Hand prüfen" >&2
        return 0
    fi
    ln -sfn "$src" "$dst"
    echo "$dst -> $src"
}

# Scripts als Verknüpfung, damit Änderungen im Repo sofort gelten
link "$SCRIPT_DIR"/tmux2png          "$BIN_DIR/tmux2png"
link "$SCRIPT_DIR"/gui-screenshot.sh "$BIN_DIR/gui-screenshot"
link "$SCRIPT_DIR"/img-proto-test    "$BIN_DIR/img-proto-test"
link "$SCRIPT_DIR"/mailbox.py        "$BIN_DIR/mailbox"
link "$SCRIPT_DIR"/geheimnisse.py    "$BIN_DIR/geheimnisse"
link "$SCRIPT_DIR"/thunderbird_konten.py "$BIN_DIR/thunderbird-konten"
link "$SCRIPT_DIR"/fr_po_pruefen.py  "$BIN_DIR/fr-po-pruefen"
link "$SCRIPT_DIR"/chrome_sitzung.py "$BIN_DIR/chrome-sitzung"
link "$SCRIPT_DIR"/chrome_anhaengen.py "$BIN_DIR/chrome-anhaengen"
link "$SCRIPT_DIR"/mithoeren.py      "$BIN_DIR/mithoeren"

# Claude-Skills, dazu die aus dem privaten Repo skills-privat, falls es geklont ist
for dir in "$SCRIPT_DIR"/skills/*/ "$HOME"/projects/skills-privat/skills/*/; do
    [[ -f "$dir/SKILL.md" ]] || continue
    name="$(basename "$dir")"
    link "${dir%/}" "$SKILL_DIR/$name"
done

# Globale Dateien aus dem privaten Repo (Quelle in skills-privat/claude/ → Ziel unter HOME);
# eine vorhandene echte Datei wird vorher als <ziel>.vor-link-<Zeit> gesichert
GLOBAL_DIR="$HOME/projects/skills-privat/claude"
declare -A GLOBAL_FILES=(
    [CLAUDE.md]=".claude/CLAUDE.md"
    [settings.json]=".claude/settings.json"
    [caveman-statusline.sh]=".claude/caveman-statusline.sh"
    [projects-AGENTS.md]="projects/AGENTS.md"
    [skill-lock.json]=".agents/.skill-lock.json"
)
for src in "${!GLOBAL_FILES[@]}"; do
    [[ -f "$GLOBAL_DIR/$src" ]] || continue
    dst="$HOME/${GLOBAL_FILES[$src]}"
    mkdir -p "$(dirname "$dst")"
    if [[ -f "$dst" && ! -L "$dst" ]]; then
        mv "$dst" "$dst.vor-link-$(date +%Y%m%d%H%M%S)"
    fi
    link "$GLOBAL_DIR/$src" "$dst"
done

# Kopie aus früheren setup.sh-Läufen, Inhalt steht jetzt im Skill screenshots
if [[ -d "$SKILL_DIR/tui-screenshot" && ! -L "$SKILL_DIR/tui-screenshot" ]]; then
    echo "Hinweis: $SKILL_DIR/tui-screenshot ist veraltet (ersetzt durch screenshots), bitte entfernen" >&2
fi
