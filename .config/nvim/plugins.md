# LazyVim Plugins (Vanilla Starter + Optimierungen)

Startup: **~22ms** | 31 Plugins (1 deaktiviert) | 18 beim Start geladen | 13 lazy-loaded

Config: `~/.config/nvim/`

## Plugin-Übersicht

### Core

| Plugin | Ladezeit | Trigger | Beschreibung |
|--------|----------|---------|--------------|
| **LazyVim** | 10.48ms | start | Framework — stellt Defaults, Keymaps, Autocmds bereit |
| **lazy.nvim** | — | start | Plugin-Manager — bootstrap, lazy-loading, UI (:Lazy) |
| **snacks.nvim** | 1.72ms | start | Utility-Sammlung von folke — Dashboard, Picker, Bufdelete, Notifications, Profiler |

### UI

| Plugin | Ladezeit | Trigger | Beschreibung |
|--------|----------|---------|--------------|
| **lualine.nvim** | 20.68ms | VeryLazy | Statusleiste — Mode, Branch, Diagnostics, Dateiname, Uhrzeit |
| **bufferline.nvim** | 5.57ms | VeryLazy | Tab-Leiste — zeigt offene Buffer als Tabs mit Icons und Close-Buttons |
| **noice.nvim** | 2.32ms | VeryLazy | Ersetzt cmdline, messages, popupmenu durch moderne UI |
| **nui.nvim** | 0.25ms | noice.nvim | UI-Komponenten-Library — Dependency von noice.nvim |
| **mini.icons** | 7.19ms | (dependency) | Datei-Icons — ersetzt nvim-web-devicons, performanter |

### Editor

| Plugin | Ladezeit | Trigger | Beschreibung |
|--------|----------|---------|--------------|
| **which-key.nvim** | 1.19ms | VeryLazy | Zeigt Keybinding-Popup nach Leader/Prefix-Key |
| **flash.nvim** | 1.80ms | VeryLazy | Schnelle Navigation — Labels auf Suchergebnisse zum Springen |
| **mini.pairs** | 2.63ms | VeryLazy | Auto-Pairing von Klammern, Quotes, etc. |
| **mini.ai** | 2.20ms | VeryLazy | Erweiterte Textobjects — `a)`, `i"`, `af` (function), etc. |
| **trouble.nvim** | 2.50ms | :Trouble / keys | Diagnostics/Quickfix-Liste als schönes Panel |
| **todo-comments.nvim** | — | LazyFile | Highlights TODO/FIXME/HACK in Kommentaren |
| **grug-far.nvim** | — | :GrugFar / keys | Find & Replace über gesamtes Projekt |
| **persistence.nvim** | — | BufReadPre | Session-Management — speichert/restored Fenster-Layout |

### Code & LSP

| Plugin | Ladezeit | Trigger | Beschreibung |
|--------|----------|---------|--------------|
| **nvim-treesitter** | 4.99ms | LazyFile/VeryLazy | Syntax-Highlighting, Indentation, Textobjects via AST-Parsing |
| **nvim-treesitter-textobjects** | 0.68ms | VeryLazy | Treesitter-basierte Textobjects (Funktionen, Klassen, etc.) |
| **ts-comments.nvim** | 1.61ms | VeryLazy | Treesitter-aware Kommentar-Toggling (gcc/gc) |
| **nvim-ts-autotag** | — | LazyFile | Auto-Close/Rename von HTML/JSX-Tags |
| **nvim-lspconfig** | — | LazyFile | LSP-Server-Konfiguration |
| **mason.nvim** | 9.92ms | :Mason | LSP/Linter/Formatter-Installer mit UI |
| **mason-lspconfig.nvim** | — | nvim-lspconfig | Brücke zwischen Mason und lspconfig |
| **conform.nvim** | — | :ConformInfo / keys | Code-Formatter (ersetzt null-ls für Formatting) |
| **nvim-lint** | — | LazyFile | Linter-Integration (ersetzt null-ls für Linting) |
| **lazydev.nvim** | — | ft=lua | Lua-Entwicklung — Typ-Annotations für Neovim-API |

### Completion & Snippets

| Plugin | Ladezeit | Trigger | Beschreibung |
|--------|----------|---------|--------------|
| **blink.cmp** | 40.14ms | InsertEnter/CmdlineEnter | Autocompletion — LSP, Snippets, Buffer, Pfade |
| **friendly-snippets** | 1.91ms | blink.cmp | Snippet-Sammlung für viele Sprachen |

### Colorscheme

| Plugin | Ladezeit | Trigger | Beschreibung |
|--------|----------|---------|--------------|
| **tokyonight.nvim** | 1.07ms | (colorscheme) | Default-Colorscheme — mehrere Varianten (night, moon, storm, day) |
| ~~catppuccin~~ | — | deaktiviert | Alternatives Colorscheme — via [`plugins/disabled.lua`](~/.config/nvim/lua/plugins/disabled.lua) |

### Utility

| Plugin | Ladezeit | Trigger | Beschreibung |
|--------|----------|---------|--------------|
| **plenary.nvim** | — | (dependency) | Lua-Utility-Library — von vielen Plugins genutzt |
| **gitsigns.nvim** | — | LazyFile | Git-Änderungen in der Sign-Column, Hunk-Navigation |

## Performance-Tuning

### Delays & Timeouts (aktuelle Werte)

| Setting | Wert | Default | Config |
|---------|------|---------|--------|
| `timeoutlen` | 300ms | 300ms | (LazyVim default) |
| `ttimeoutlen` | **5ms** | 50ms | [`config/options.lua`](~/.config/nvim/lua/config/options.lua) |
| `updatetime` | **100ms** | 200ms | [`config/options.lua`](~/.config/nvim/lua/config/options.lua) |
| `redrawtime` | **500ms** | 2000ms | [`config/options.lua`](~/.config/nvim/lua/config/options.lua) |
| `synmaxcol` | **300** | 3000 | [`config/options.lua`](~/.config/nvim/lua/config/options.lua) |
| which-key `delay` | **0ms** | 200ms | [`plugins/which-key.lua`](~/.config/nvim/lua/plugins/which-key.lua) |
| blink.cmp docs delay | **150ms** | 500ms | [`plugins/blink-cmp.lua`](~/.config/nvim/lua/plugins/blink-cmp.lua) |
| blink.cmp brackets timeout | **200ms** | 400ms | [`plugins/blink-cmp.lua`](~/.config/nvim/lua/plugins/blink-cmp.lua) |
| snacks animate | **false** | true | [`plugins/snacks.lua`](~/.config/nvim/lua/plugins/snacks.lua) |
| snacks scroll | **false** | true | [`plugins/snacks.lua`](~/.config/nvim/lua/plugins/snacks.lua) |
| noice LSP progress | **false** | true | [`plugins/noice.lua`](~/.config/nvim/lua/plugins/noice.lua) |

### Custom Config-Dateien

| Datei | Zweck |
|-------|-------|
| [`lua/config/options.lua`](~/.config/nvim/lua/config/options.lua) | Vim-Optionen: ttimeoutlen, updatetime, redrawtime, synmaxcol |
| [`lua/plugins/which-key.lua`](~/.config/nvim/lua/plugins/which-key.lua) | which-key delay=0 |
| [`lua/plugins/blink-cmp.lua`](~/.config/nvim/lua/plugins/blink-cmp.lua) | Completion docs/brackets Delays |
| [`lua/plugins/snacks.lua`](~/.config/nvim/lua/plugins/snacks.lua) | Animationen und Scroll deaktiviert |
| [`lua/plugins/noice.lua`](~/.config/nvim/lua/plugins/noice.lua) | LSP Progress aus, Suche unten |
| [`lua/plugins/disabled.lua`](~/.config/nvim/lua/plugins/disabled.lua) | Catppuccin deaktiviert |

### Top Startup-Kostenträger

1. **blink.cmp** (40ms) — WASM/native Completion-Engine, schwer optimierbar
2. **lualine.nvim** (21ms) — Statusleiste mit vielen Segmenten
3. **LazyVim** (10ms) — Framework-Init, Config-Merge
4. **mason.nvim** (10ms) — Registry-Check beim Start
5. **mini.icons** (7ms) — Icon-Database laden
