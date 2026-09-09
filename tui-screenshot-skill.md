---
name: tui-screenshot
description: Use when you need to take a screenshot of a TUI application, terminal session, or tmux pane to show the user visually what is happening
---

# TUI Screenshot

## Overview

Nutze `tmux2png` um Screenshots von tmux Sessions, Panes oder TUI-Anwendungen (lazygit,
htop, Dateimanager, beliebige TUIs) zu erstellen. Das Tool konvertiert
tmux-Output via `tmux2html` zu einem lesbaren PNG mit korrekten Farben und Schrift.

## When to Use

- User fragt nach Screenshot/Bild einer Terminal-Session
- Du willst zeigen, was eine TUI gerade anzeigt
- Du willst einen Zustand in der TUI visuell dokumentieren

**Nicht verwenden für:** GUI-Anwendungen und Bildprotokolle. Kitty-Graphics- und
Sixel-Pixel rendert der Terminal-Emulator außerhalb des tmux-Buffers und tauchen im PNG
nicht auf. Dafür `gui-screenshot` verwenden.

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

1. Herausfinden, in welcher tmux Session die TUI läuft:
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

- **tui-driver verwenden**: dessen Screenshots sind unbrauchbar (keine Farben, kein
  Bildprotokoll-Support). Immer `tmux2png` bevorzugen.
- **Pixel-Grafiken erwarten**: `tmux2png` erfasst nur den Text-Layer. Für echte Pixel
  `gui-screenshot` nehmen.
- **Session-Name vergessen**: `tmux ls` zeigt alle aktiven Sessions.
