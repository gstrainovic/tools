# Tools — TUI/Terminal Automation

Dieses Verzeichnis enthält Hilfsmittel zum Steuern und Beobachten von Terminal-Anwendungen (nvim, tmux, TUIs).

## Setup auf neuem PC

```bash
bash ~/tools/setup.sh
```

Installiert automatisch: tmux2html, mcp-tui-driver, neovim-mcp, tmux2png, Skill und MCP-Config.

**Voraussetzungen:** `uv`, `cargo`, `go` müssen bereits installiert sein.

## Dateien

| Datei | Beschreibung |
|-------|-------------|
| `setup.sh` | Einrichtungs-Script für neuen PC (alles in einem Schritt) |
| `tmux2png` | Bash-Script: tmux-Session → lesbares PNG via tmux2html + wkhtmltoimage |
| `tui-screenshot-skill.md` | Claude-Skill-Dokumentation für tui-screenshot |
| `mcps.json` | MCP-Server-Konfigurationen (aus `~/.claude.json`) |

## tmux2png

Selbst geschriebenes Script unter `~/.local/bin/tmux2png` (dort auch ausführbar).

```bash
tmux2png                        # aktuelle Session → /tmp/tmux-TIMESTAMP.png
tmux2png lazyvim                # Session "lazyvim"
tmux2png lazyvim:0.0            # spezifische Pane
tmux2png lazyvim /tmp/out.png   # mit Ausgabepfad
```

**Intern:** `tmux2html TARGET -o HTML` → `wkhtmltoimage --width 1400 HTML PNG`

## MCPs für Terminal-Automation

### tmux-mcp (`npx -y tmux-mcp`)
- Sessions/Panes auflisten, Output capturen, Befehle ausführen
- Tools: `list-sessions`, `list-panes`, `capture-pane`, `execute-command`
- Gut für: tmux beobachten, Shell-Befehle senden

### neovim-mcp (`~/.local/bin/neovim-mcp`)
- Neovim direkt über RPC/Socket steuern
- Socket: `/tmp/nvim.sock` (via `NVIM_MCP_LISTEN_ADDRESS`)
- Gut für: Neovim fernsteuern (Buffer lesen, Commands ausführen)
- Nvim muss mit `--listen /tmp/nvim.sock` gestartet sein

### tui-driver (`~/.cargo/bin/mcp-tui-driver`)
- TUI-Apps starten, Key-Events senden, Accessibility-Snapshots
- Tools: `tui_launch`, `tui_press_key`, `tui_send_text`, `tui_snapshot`
- **Achtung:** `tui_screenshot` liefert unlesbaren Pixelbrei → stattdessen `tmux2png`

## Empfohlener Workflow: Screenshot

```
1. tmux ls                          # Session-Namen herausfinden
2. tmux2png SESSION_NAME            # PNG erzeugen
3. Read-Tool → /tmp/tmux-*.png     # PNG in Claude Code anzeigen
```

## Empfohlener Workflow: Nvim fernsteuern

```
1. Nvim starten mit: nvim --listen /tmp/nvim.sock
   (oder in tmux "lazyvim" Session — dort läuft es schon)
2. neovim-mcp Tools verwenden
3. Für visuellen Check: tmux2png lazyvim
```

## Skill

Der `tui-screenshot` Skill liegt unter `~/.claude/skills/tui-screenshot/SKILL.md`.
Er wird automatisch von Claude Code geladen wenn Screenshots von TUIs gebraucht werden.
