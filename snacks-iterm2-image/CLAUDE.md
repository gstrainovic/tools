# snacks-iterm2-image

Neovim-Plugin das snacks.nvim patcht, um Bild-Previews via iTerm2 OSC 1337 Protokoll zu rendern.

## Architektur

- `lua/snacks-iterm2-image/protocol.lua` — iTerm2 OSC 1337 Escape-Sequenz-Generator
- `lua/snacks-iterm2-image/override.lua` — Monkey-patching von snacks.nvim Image-Pipeline
- `lua/snacks-iterm2-image/init.lua` — Plugin-Setup + Config

## Kritische Learnings

### nvim TUI filtert OSC 1337 (Root Cause)

`io.stdout:write()` aus nvim Lua geht NICHT direkt ans Terminal. nvim's TUI-Prozess (PID != embedded-Server PID) empfängt die Daten via internes RPC. Der TUI-Layer erkennt und leitet KGP-Sequenzen (`\27_G...`) durch, aber **filtert/ignoriert OSC 1337** (`\27]1337;...`).

**Lösung:** Direkt an die PTY des Parent-Prozesses schreiben:
```lua
local ppid = vim.fn.system("ps -o ppid= -p " .. vim.fn.getpid()):gsub("%s+", "")
local pty_path = vim.fn.system("readlink /proc/" .. ppid .. "/fd/1"):gsub("%s+", "")
local tty = io.open(pty_path, "wb")  -- z.B. /dev/pts/1
tty:write(osc_sequence)
tty:flush()
tty:close()
```

### iTerm2 vs KGP: Persistenz-Problem

- **KGP:** Bilder werden in WezTerms GPU-Layer gespeichert → überleben nvim-Redraws
- **iTerm2:** Bilder sind Zell-Inhalt → werden bei jedem nvim-Redraw überschrieben
- **Lösung:** `vim.api.nvim_set_decoration_provider` mit `on_end` + `vim.schedule` — nach jedem Redraw-Zyklus wird das Bild neu gesendet

### OSC 1337 Sequenz-Format (WezTerm-kompatibel)

```
\x1b]1337;File=inline=1;preserveAspectRatio=1;doNotMoveCursor=1;size=BYTES;width=CELLS;height=CELLS;name=BASE64NAME:BASE64DATA\x07
```

Wichtige Parameter:
- `doNotMoveCursor=1` — Cursor springt nicht nach dem Bild (WezTerm-Extension)
- `size=N` — Byte-Count der Rohdaten (vor Base64)
- `width=N` / `height=N` — Zellen (ohne Suffix), auch `Npx` für Pixel möglich
- `inline=1` — Pflicht für Inline-Anzeige

### snacks.nvim Render-Pipeline (Hook-Points)

```
Image:send()           → wir: no-op (markiere sent=true, kein KGP-Upload)
Placement:update()     → ruft render_fallback() auf (WezTerm hat keine Placeholders)
Placement:render_fallback() → wir: OSC 1337 via PTY-Direct-Write
```

`render_fallback` wird aufgerufen wenn `terminal.env().placeholders == false` (WezTerm-Pfad).

### ratatui-image Referenz

ratatui-image löst das gleiche Problem anders:
- `cell.set_skip(true)` — ratatui schreibt KEINE Zellen in den Bildbereich (gibt es in nvim nicht)
- Re-emit jedes Frame — genau wie unser decoration_provider Ansatz
- ECH Pre-Clear vor dem Bild — `\27[NX` pro Zeile (Erase Character Horizontal)
- Blacklistet Kitty+Sixel für WezTerm, erzwingt iTerm2

## Test-Framework

- busted (via luarocks)
- Tests in `tests/`
- Ausführen: `busted tests/`

## Konventionen

- TDD: Tests zuerst
- Lua-Style: snacks.nvim-kompatibel
- Kein direktes Editieren von snacks.nvim Dateien
- Debug-Log: `/tmp/iterm2-debug.log` (in Produktion deaktivieren)
