# Design: yazi/nvim Cleanup & Bild-Viewer

## Problem

Die yazi↔nvim Integration hat sich über 15+ Commits zu einem fragilen System aus Tab.layout-Hacks, State-Management-Bugs und undurchsichtigen Plugin-Interaktionen entwickelt. Der preview-force-max Plugin war nach mehreren Fixes immer noch buggy.

## Entscheidung

Komplettes Entfernen aller yazi↔nvim Hacks. Bild-Preview wird durch ein einfaches, isoliert testbares Script ersetzt das WezTerm-native Bildanzeige nutzt.

## Was wird entfernt

| Datei | Grund |
|-------|-------|
| `.config/yazi/plugins/preview-force-max.yazi/` | Tab.layout-Hack, buggy |
| `.config/yazi/plugins/toggle-pane.yazi/` | Nicht mehr benötigt |
| `keymap.toml` ESC-Binding | preview-force-max Referenz |
| `~/tools/ide` | WezTerm yazi+nvim Split — nicht mehr benötigt |
| `~/tools/nvim-ide-open` | yazi→nvim RPC Opener — nicht mehr benötigt |
| `~/.config/nvim/lua/plugins/image-viewer.lua` | ya emit-to basiert — wird ersetzt |
| `yazi.toml` opener: `nvim-ide-open` | Wird zu `$EDITOR` / `nvim` |

## Was bleibt unverändert

- `yafg.yazi` (rg+fzf grep — unabhängig)
- `init.lua` (nur yafg Setup)
- `keymap.toml` (alle anderen Bindings)
- `yazi.toml` (ratio, preview, sorting etc.)

## Neues System

### Architektur

```
nvim (neo-tree/oil) ──Enter auf Bild──► BufReadCmd autocmd
                                              │
                                    wezterm cli split-pane --left --percent 50
                                              │
                                        img-preview FILE
                                              │
                                    wezterm imgcat + read -n1
                                              │
                                        any key → Pane closed

┌─────────────────────┬─────────────────────┐
│  img-preview (50%)  │      nvim (50%)     │
│  wezterm imgcat     │                     │
│  any key to close   │                     │
└─────────────────────┴─────────────────────┘
```

### Komponenten

#### 1. `img-preview` Script (`~/tools/img-preview`)

Standalone-Script, isoliert testbar:
- Input: Dateipfad als Argument
- Bilder: `wezterm imgcat $FILE`
- PDF: `pdftoppm` → tmpfile → `wezterm imgcat` → cleanup
- Wartet auf beliebigen Tastendruck (`read -n1 -s -r`)
- Exit → WezTerm schließt Pane automatisch

#### 2. `image-viewer.lua` (`~/.config/nvim/lua/plugins/image-viewer.lua`)

LazyVim-Plugin (neu geschrieben):
- `BufReadCmd` autocmd für Bild/PDF-Extensions
- Spawnt `wezterm cli split-pane --left --percent 50 -- img-preview FILE`
- Löscht den nvim-Buffer (Binary nicht in nvim öffnen)
- Kein yazi, kein State, kein ya emit-to

#### 3. `yazi.toml` opener

`nvim-ide-open` → `nvim "$@"` (Standard-Editor)

## Vorteile gegenüber alt

- Kein State-Management (st.old, Tab.layout)
- Kein yazi↔nvim Kommunikation (ya emit-to)
- Jede Komponente isoliert testbar
- img-preview funktioniert auch ohne nvim (CLI-Tool)
- Keine Race-Conditions (defer_fn, sleep etc.)

## Dependencies

- `wezterm` CLI (bereits vorhanden)
- `pdftoppm` aus `poppler-utils` (für PDF-Preview)
