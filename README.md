# ~/projects/tools — Terminal- und TUI-Automation

Kleine Werkzeuge, um Terminal-Anwendungen zu beobachten und zu dokumentieren.
Zielumgebung: Fedora, GNOME Wayland, Ghostty als Terminal, tmux als Multiplexer.

Editor- und Dateimanager-Configs liegen bewusst nicht mehr hier. Das Repo enthält nur
noch eigenständige Terminal-Scripts.

## Scripts

| Script | Beschreibung |
|--------|-------------|
| `tmux2png` | tmux-Session oder Pane als PNG rendern |
| `gui-screenshot.sh` | Vollbild-Screenshot via ydotool Shift+Print |
| `img-proto-test` | Terminal-Bildprotokolle vergleichen (iTerm2, Kitty, Sixel) |
| `setup.sh` | Einrichtung auf einem neuen Rechner |

Dazu `.bashrc` mit den Shell-Aliasen des Repos. Sie wird nicht kopiert, sondern am Ende
von `~/.bashrc` gesourced:

```bash
[ -f "$HOME/projects/tools/.bashrc" ] && source "$HOME/projects/tools/.bashrc"
```

### tmux2png

```bash
tmux2png                        # aktuelle Session → /tmp/tmux-TIMESTAMP.png
tmux2png dev                    # Session "dev"
tmux2png dev:0.0                # spezifische Pane
tmux2png dev /tmp/out.png       # mit Ausgabepfad
```

Intern: `tmux2html` erzeugt HTML, `wkhtmltoimage` rendert es mit Breite 1400 zu PNG.
Erfasst nur den Text-Layer. Bildprotokolle rendert der Terminal-Emulator außerhalb des
tmux-Buffers und tauchen deshalb nicht auf.

### gui-screenshot.sh

```bash
gui-screenshot                  # → ~/Bilder/Bildschirmfotos/...png
gui-screenshot /tmp/out.png     # mit Ausgabepfad
```

Erfasst echte Pixel inklusive Kitty-Grafiken. Braucht `ydotoold`, das bei Bedarf per sudo
gestartet wird.

### img-proto-test

```bash
img-proto-test [BILD]           # ohne Argument: neuester Screenshot
```

Zeigt dasselbe Bild per iTerm2-Protokoll, Kitty Graphics Protocol und Sixel mit
Zeitmessung. Muss außerhalb von tmux laufen.

## Setup

```bash
bash ~/projects/tools/setup.sh
```

Voraussetzungen: `uv`, `cargo`, `python3`. Alles Weitere installiert das Script.

## Tests

```bash
bash tests/test-repo-consistency.sh
```

## Getestete Screenshot-Ansätze (und warum verworfen)

| Option | Status | Problem |
|--------|--------|---------|
| ydotool Shift+Print | **benutzt** | Echte Pixel, kein Fokus-Wechsel |
| tmux2png | **benutzt** | Nur Text-Layer, dafür scharf und sofort lesbar |
| grim, gnome-screenshot | verworfen | GNOME 49 Portal-Bug `Failed to associate portal window` |
| XDG ScreenCast Portal | verworfen | Dialog erscheint bei jedem Aufruf erneut |
| Weston headless + GL | verworfen | NVIDIA spiegelt den Screenshot horizontal |
| tui-driver `tui_screenshot` | verworfen | Unlesbarer Pixelbrei |
