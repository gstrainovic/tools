---
name: screenshots
description: Screenshots unter GNOME Wayland machen (tmux2png für TUIs und tmux-Sessions, gui-screenshot für echte Pixel) und TUIs über tmux-mcp oder tui-driver steuern. Laden, bevor ein Screenshot gemacht oder eine TUI ferngesteuert wird.
---

# Screenshots (GNOME Wayland)

Beide Scripts liegen in `~/projects/tools` und sind von `link.sh` (läuft in `setup.sh`) nach `~/.local/bin` verknüpft. Fehlt ein Befehl: `bash ~/projects/tools/link.sh`.

## TUI oder tmux-Session: `tmux2png`

```bash
tmux2png                        # aktuelle Session → /tmp/tmux-TIMESTAMP.png
tmux2png SESSION                # bestimmte Session
tmux2png SESSION:0.0            # bestimmte Pane (Session:Window.Pane)
tmux2png SESSION /tmp/out.png   # mit Ausgabepfad
```

- Intern: `tmux2html TARGET -o HTML` → `wkhtmltoimage --width 1400 HTML PNG`. Scharfes PNG mit Farben, sofort lesbar. Das Script gibt den Pfad des PNG aus.
- **Erfasst nur den Text-Layer (ANSI-Zeichen und Farben).** Kitty-Graphics- und Sixel-Pixel rendert der Terminal-Emulator ausserhalb des tmux-Buffers, sie fehlen im PNG. Dafür `gui-screenshot`.

Ablauf:

1. `tmux ls`: Session-Namen herausfinden.
2. `tmux2png SESSION`
3. PNG mit dem Read-Tool anzeigen.

## Echte Pixel, ganzer Bildschirm: `gui-screenshot`

```bash
gui-screenshot                  # → ~/Bilder/Bildschirmfotos/...png, gibt den Pfad aus
gui-screenshot /tmp/out.png     # verschiebt den Screenshot dorthin
```

Simuliert Shift+Print per `ydotool` und wartet bis zu 5 Sekunden auf die neue Datei in `~/Bilder/Bildschirmfotos`. Braucht `ydotoold`, das Script startet ihn bei Bedarf per sudo. Erfasst auch Kitty-Grafiken.

## Funktioniert nicht

- `grim`, `gnome-screenshot`: GNOME-49-Portal-Bug (`Failed to associate portal window`).
- XDG-ScreenCast-Portal: Dialog erscheint bei jedem Aufruf.
- tui-driver `tui_screenshot`: unlesbarer Pixelbrei ohne Farben.

## TUIs steuern (MCPs)

- **tmux-mcp** (`npx -y tmux-mcp`): Sessions und Panes auflisten, Output capturen, Befehle ausführen (`list-sessions`, `list-panes`, `capture-pane`, `execute-command`). Nach Aktionen `tmux2png SESSION` aufrufen.
- **tui-driver** (`~/.cargo/bin/mcp-tui-driver`): TUI-Apps starten, Key-Events senden, Accessibility-Snapshots. Seine Sessions laufen nicht in tmux, `tmux2png` greift dort nicht. Für Screenshots die App stattdessen in tmux starten.
- Control-Tasten per `tmux send-keys -t SESSION C-p` senden. rawMode schickt «C-p» als wörtlichen Text.
