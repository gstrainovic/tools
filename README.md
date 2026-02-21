# ~/tools — WezTerm Automation Tools

Tools zum automatischen Öffnen von nvim neben dem aktuellen Pane,
Tastatureingaben senden und Screenshots machen — ohne den User-Flow zu unterbrechen.

## Flow: nvim neben Claude öffnen

```
User chattet in Tab 1 (Pane 0)
           │
           ▼
    nvim-split datei.png
           │
           ▼
  WezTerm öffnet nvim als rechten Split (Pane 9)
  User bleibt in Pane 0, nvim ist daneben sichtbar
           │
           ▼
  wez-send-key 9 "<Space><Space>"   ← Taste an nvim senden
           │
           ▼
  python3 wez-screenshot /tmp/out.png   ← XDG Portal Screenshot
  (WezTerm ist aktives Fenster → Screenshot enthält echte Pixel inkl. Kitty/Sixel)
```

## Scripts

### `nvim-split` — nvim als Split öffnen

```bash
nvim-split [file] [--percent N]
```

Öffnet nvim als rechten Split (default: 40% Breite) im aktuellen WezTerm-Tab.
Gibt die Pane-ID zurück, die für `wez-send-key` und `wez-screenshot` gebraucht wird.

```bash
PANE=$(nvim-split /tmp/test.png)       # Öffnet nvim mit test.png
PANE=$(nvim-split --percent 50)        # 50% Breite
echo "Pane ID: $PANE"
```

**Warum Split statt neuer Tab?**
- User bleibt in seinem Pane → kein Flow-Unterbruch
- Nvim ist sofort sichtbar, User kann mitverfolgen/eingreifen
- XDG Portal Screenshot erfasst beide Panes im gleichen Fenster

### `wez-send-key` — Tastendrücke an nvim senden

```bash
wez-send-key PANE_ID "TASTEN"
```

Unterstützt nvim-Style Notation:

| Notation | Beschreibung |
|----------|-------------|
| `<Space>` | Leertaste |
| `<CR>` / `<Enter>` | Enter |
| `<Esc>` | Escape |
| `<Tab>` | Tab |
| `<BS>` | Backspace |
| `<C-c>` | Ctrl+C |
| `<C-u>` | Ctrl+U |
| `<Up>` `<Down>` `<Left>` `<Right>` | Pfeiltasten |

```bash
wez-send-key "$PANE" "<Esc>:w<CR>"           # Speichern
wez-send-key "$PANE" "<Space><Space>"         # Leader Leader
wez-send-key "$PANE" ":set number<CR>"        # Zeilennummern
```

### `wez-screenshot` — Screenshot mit echten Pixeln

```bash
python3 ~/tools/wez-screenshot /tmp/out.png
```

Verwendet XDG Desktop Portal (`org.freedesktop.portal.Screenshot`) mit `interactive=false`.
**Wichtig:** Funktioniert nur wenn WezTerm das aktive Fenster ist (kein Fokus-Wechsel nötig
wenn man bereits in WezTerm ist).

Erfasst echte Pixel inkl. **Sixel** und **Kitty** Grafiken — im Gegensatz zu
`tmux2png` (nur Text-Layer) oder `tui_screenshot` (unlesbarer Pixelbrei).

```bash
python3 ~/tools/wez-screenshot /tmp/screenshot.png
# → Speichert Screenshot, gibt Pfad aus
```

## Komplettes Beispiel

```bash
#!/bin/bash
# Öffne Bild in nvim, mache Screenshot, schließe nvim wieder

FILE="/tmp/mein-bild.png"

# 1. nvim als Split öffnen
PANE=$(~/tools/nvim-split "$FILE")
sleep 1   # nvim startet

# 2. Plugin aktivieren (z.B. Sixelview)
~/tools/wez-send-key "$PANE" "<Space><Space>"
sleep 0.5

# 3. Screenshot
python3 ~/tools/wez-screenshot /tmp/result.png

# 4. nvim schließen (optional)
~/tools/wez-send-key "$PANE" "<Esc>:q!<CR>"

echo "Screenshot: /tmp/result.png"
```

## Getestete Ansätze (und warum verworfen)

| Option | Status | Problem |
|--------|--------|---------|
| XDG Screenshot Portal | ✅ **Benutzt** | Kein Fokus-Wechsel, echte Pixel |
| XDG ScreenCast Portal (persist_mode=2) | ❌ | Dialog erscheint immer wieder |
| Weston headless + GL | ❌ | NVIDIA spiegelt Screenshot horizontal |
| Weston headless + Pixman | ❌ | WezTerm bekommt kein GPU → Kitty blank |
| Xvfb | ❌ | X11-Mode, kein Wayland, Sixel fraglich |
| WezTerm Lua Plugin (user-var-changed) | ❌ | Nicht nötig, zu komplex |
| tmux2png | ❌ | Nur Text-Layer, keine Pixel/Sixel/Kitty |
| tui_screenshot | ❌ | Unlesbarer Pixelbrei |

## Voraussetzungen

- WezTerm mit `wezterm cli` in PATH
- Python 3 mit `dbus-python` und `PyGObject` (für wez-screenshot)
- XDG Desktop Portal (GNOME Wayland: bereits vorhanden)
