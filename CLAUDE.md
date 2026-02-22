# Tools — TUI/Terminal Automation

Dieses Verzeichnis enthält Hilfsmittel zum Steuern und Beobachten von Terminal-Anwendungen (nvim, tmux, yazi, TUIs).

## Setup auf neuem PC

```bash
bash ~/tools/setup.sh
```

Installiert automatisch: tmux2html, mcp-tui-driver, neovim-mcp, tmux2png, img-preview, yazi-Config, Skill und MCP-Config.

**Voraussetzungen:** `uv`, `cargo`, `go`, WezTerm, yazi, neovim.

## Dateien

| Datei | Beschreibung |
|-------|-------------|
| `img-preview` | Bild/PDF im Terminal anzeigen via wezterm imgcat |
| `wez-send-key` | Tastendrücke an WezTerm-Pane senden (nvim-Notation) |
| `wez-screenshot` | XDG Portal Screenshot (GNOME Wayland, echte Pixel) |
| `wez-screenshot-windows.ps1` | Screenshot für Windows |
| `tmux2png` | tmux-Session → lesbares PNG via tmux2html + wkhtmltoimage |
| `setup.sh` | Einrichtungs-Script für neuen PC (alles in einem Schritt) |
| `tui-screenshot-skill.md` | Claude-Skill-Dokumentation für tui-screenshot |
| `mcps.json` | MCP-Server-Konfigurationen (aus `~/.claude.json`) |
| `.config/yazi/` | Yazi-Konfiguration (symlinked nach `~/.config/yazi/`) |
| `yazi-debug-session` | Yazi mit fester Client-ID 1337 + Debug-Logging starten |
| `.config/wezterm/wezterm.lua` | WezTerm-Config: Keybindings + Screenshot-Trigger |

## WezTerm Keybindings

| Shortcut | Aktion |
|----------|--------|
| `Ctrl+Shift+S` | Screenshot via XDG Portal (nur Linux) |

## tmux2png

```bash
tmux2png                        # aktuelle Session → /tmp/tmux-TIMESTAMP.png
tmux2png lazyvim                # Session "lazyvim"
tmux2png lazyvim:0.0            # spezifische Pane
tmux2png lazyvim /tmp/out.png   # mit Ausgabepfad
```

**Intern:** `tmux2html TARGET -o HTML` → `wkhtmltoimage --width 1400 HTML PNG`

**LIMITATION: Erfasst NUR den Text-Layer (ANSI-Zeichen/Farben).**
Sixel/Kitty-Pixel-Grafiken werden vom Terminal-Emulator außerhalb des tmux-Buffers gerendert → NICHT sichtbar in tmux2png.

## MCPs für Terminal-Automation

### tmux-mcp (`npx -y tmux-mcp`)
- Sessions/Panes auflisten, Output capturen, Befehle ausführen
- Tools: `list-sessions`, `list-panes`, `capture-pane`, `execute-command`

### neovim-mcp (`~/.local/bin/neovim-mcp`)
- Neovim direkt über RPC/Socket steuern
- Socket: `/tmp/nvim.sock` (via `NVIM_MCP_LISTEN_ADDRESS`)
- Nvim muss mit `--listen /tmp/nvim.sock` gestartet sein

### tui-driver (`~/.cargo/bin/mcp-tui-driver`)
- TUI-Apps starten, Key-Events senden, Accessibility-Snapshots
- **Achtung:** `tui_screenshot` liefert unlesbaren Pixelbrei → stattdessen `tmux2png`

## Empfohlener Workflow: Screenshot

```
1. tmux ls                          # Session-Namen herausfinden
2. tmux2png SESSION_NAME            # PNG erzeugen
3. Read-Tool → /tmp/tmux-*.png     # PNG in Claude Code anzeigen
```

## Yazi Debugging (Claude-Workflow)

Yazi läuft **NICHT** in headless tmux (Terminal response timeout). User startet yazi im echten Terminal.

```bash
# User startet (einmalig):
yazi-debug-session ~/pfad

# Claude kann dann:
ya emit-to 1337 plugin max-preview       # Plugin triggern
tail -20 ~/.local/state/yazi/yazi.log              # Errors lesen
tmux2png SESSION_NAME                              # Layout-Screenshot
```

**Wichtig:** Plugin-Argumente IMMER mit `--args=` angeben. `ya emit-to 1337 plugin NAME` ohne args tut bei vielen Plugins nichts.

## Skill

Der `tui-screenshot` Skill liegt unter `~/.claude/skills/tui-screenshot/SKILL.md`.
