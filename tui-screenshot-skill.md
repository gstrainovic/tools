---
name: tui-screenshot
description: Use when you need to take a screenshot of a TUI application, terminal session, tmux pane, Neovim window, or any terminal-based UI to show the user visually what is happening
---

# TUI Screenshot

## Overview

Nutze `tmux2png` um Screenshots von tmux Sessions, Panes oder TUI-Anwendungen (Neovim, lazygit, etc.) zu erstellen. Das Tool konvertiert tmux-Output via `tmux2html` zu einem lesbaren PNG mit korrekten Farben und Schrift.

## When to Use

- User fragt nach Screenshot/Bild einer Terminal-Session
- Du willst zeigen was in Neovim / lazygit / irgendeiner TUI gerade angezeigt wird
- Du willst einen Zustand in der TUI visuell dokumentieren
- Preview einer Datei im Terminal sichtbar machen

**Nicht verwenden für:** GUI-Anwendungen — dafür existieren andere Wege.

## Quick Reference

```bash
# Aktuelle tmux Session → auto-benanntes PNG in /tmp/
tmux2png

# Bestimmte Session
tmux2png SESSION_NAME

# Spezifische Pane (Session:Window.Pane)
tmux2png SESSION_NAME:0.0

# Mit Ausgabepfad
tmux2png SESSION_NAME /tmp/output.png
```

Das Script gibt den Pfad zur erzeugten PNG-Datei aus.

## Workflow

1. Herausfinden in welcher tmux Session die TUI läuft:
   ```bash
   tmux ls
   ```
2. Screenshot machen:
   ```bash
   tmux2png SESSION_NAME
   ```
3. PNG mit dem `Read`-Tool anzeigen (Claude Code kann Bilder lesen):
   ```
   Read tool → /tmp/tmux-TIMESTAMP.png
   ```

## Common Mistakes

- **tui-driver verwenden**: tui-driver Screenshots sind oft unbrauchbar (keine Farben, kein Kitty-Support). Immer `tmux2png` bevorzugen.
- **neovim-mcp screenshot**: Liefert Base64-Rohdaten die schwer zu interpretieren sind. `tmux2png` ist klarer.
- **Session-Name vergessen**: `tmux ls` zeigt alle aktiven Sessions.
