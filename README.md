# ~/tools — WezTerm + Yazi + Nvim Automation

Tools für zwei Workflows:
1. **IDE-Modus:** yazi + nvim als WezTerm-Split-Layout (Dateimanager + Editor)
2. **Claude-Modus:** nvim neben Claude öffnen, Tasten senden, Screenshots machen

## WezTerm Keybindings

| Shortcut | Aktion |
|----------|--------|
| `Ctrl+Shift+Z` | Pane Zoom Toggle — maximiert/minimiert den aktiven Pane (z.B. yazi ausblenden, nvim fullscreen) |
| `Ctrl+Shift+S` | Screenshot via XDG Portal (nur Linux) |

Config: `.config/wezterm/wezterm.lua`

## IDE-Modus: yazi + nvim

```
┌──────────────┬───────────────────────────┐
│  yazi (30%)  │      nvim (70%)           │
│  Datei-      │      --listen             │
│  Browser     │      /tmp/nvim-ide.sock   │
└──────────────┴───────────────────────────┘
```

### `ide` — Layout starten

```bash
ide                  # aktuelles Verzeichnis
ide ~/projekte       # bestimmtes Verzeichnis
```

- Startet nvim als Server (`/tmp/nvim-ide.sock`) im rechten 70%-Split
- Startet yazi im linken 30%-Pane
- Funktioniert auch außerhalb von WezTerm (öffnet neues Fenster)

### `nvim-ide-open` — Dateien aus yazi in nvim öffnen

```bash
nvim-ide-open datei.txt
```

- Wird von yazi als `edit`-Opener aufgerufen (konfiguriert in `yazi.toml`)
- Sendet Datei an laufenden nvim via `--server --remote`
- Fallback: startet normales nvim wenn kein Server läuft

### Yazi-Konfiguration

Die Yazi-Config liegt in `.config/yazi/` und wird via Symlink nach `~/.config/yazi/` verlinkt.

| Datei | Beschreibung |
|-------|-------------|
| `yazi.toml` | Hauptconfig: Layout, Opener (`nvim-ide-open`), Preview |
| `keymap.toml` | Keybindings: Bookmarks, fzf-Search, yafg |
| `init.lua` | Plugin-Init: yafg mit `editor = "nvim"` |
| `theme.toml` | Catppuccin/Dracula Theme |
| `plugins/yafg.yazi/` | Fuzzy-Grep Plugin (rg + fzf) |
| `flavors/dracula.yazi/` | Dracula Flavor |

## Claude-Modus: nvim neben Claude

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
```

### `nvim-split` — nvim als Split öffnen

```bash
nvim-split [file] [--percent N]
```

Öffnet nvim als rechten Split (default: 40%) im aktuellen WezTerm-Tab.
Gibt die Pane-ID zurück.

### `wez-send-key` — Tastendrücke an Pane senden

```bash
wez-send-key PANE_ID "TASTEN"
```

Unterstützt nvim-Style Notation: `<Space>`, `<CR>`, `<Esc>`, `<Tab>`, `<BS>`, `<C-c>`, `<Up>` etc.

### `wez-screenshot` — Screenshot mit echten Pixeln

```bash
python3 ~/tools/wez-screenshot /tmp/out.png
```

XDG Desktop Portal Screenshot (`interactive=false`).
Erfasst echte Pixel inkl. Sixel und Kitty Grafiken.

## Alle Scripts

| Script | Beschreibung |
|--------|-------------|
| `ide` | WezTerm-Layout: yazi (30%) + nvim (70%) |
| `nvim-ide-open` | Datei an laufenden nvim-Server senden (yazi-Opener) |
| `nvim-split` | Nvim als rechten WezTerm-Split öffnen (Claude-Modus) |
| `wez-send-key` | Tastendrücke an WezTerm-Pane senden |
| `wez-screenshot` | XDG Portal Screenshot (GNOME Wayland) |
| `wez-screenshot-windows.ps1` | Screenshot für Windows |
| `tmux2png` | tmux-Session → PNG via tmux2html |
| `setup.sh` | Einrichtungs-Script für neuen PC |

## Plattform-Kompatibilität

| Feature | Linux (Fedora) | Windows (Git Bash) |
|---------|:-:|:-:|
| ide (yazi + nvim) | Ja | Ja |
| nvim-ide-open | Ja | Ja |
| nvim-split | Ja | Ja |
| wez-send-key | Ja | Ja |
| wez-screenshot | Ja (XDG Portal) | PowerShell-Version |
| tmux2png | Ja | Nein (kein tmux) |

Unter Windows nutzt nvim Named Pipes (`\\.\pipe\nvim-ide`) statt Unix-Sockets.

## Setup

```bash
bash ~/tools/setup.sh
```

Erkennt automatisch Linux vs. Windows und installiert entsprechend.

**Voraussetzungen:** `cargo`, `go`, WezTerm, yazi, neovim. Zusätzlich Linux: `uv`, tmux.

## Getestete Ansätze (und warum verworfen)

| Option | Status | Problem |
|--------|--------|---------|
| XDG Screenshot Portal | **Benutzt** | Kein Fokus-Wechsel, echte Pixel |
| XDG ScreenCast Portal (persist_mode=2) | verworfen | Dialog erscheint immer wieder |
| Weston headless + GL | verworfen | NVIDIA spiegelt Screenshot horizontal |
| Weston headless + Pixman | verworfen | WezTerm bekommt kein GPU, Kitty blank |
| tmux2png | nur Text | Nur Text-Layer, keine Pixel/Sixel/Kitty |
| tui_screenshot | verworfen | Unlesbarer Pixelbrei |
