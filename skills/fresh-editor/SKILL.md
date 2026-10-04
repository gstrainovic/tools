---
name: fresh-editor
description: Fresh (Terminal-Editor) einrichten, Plugins schreiben und per tmux fernsteuern: Pfade, Plugin-API mit Byte-Offsets, registerCommand-Kontext, Tastenbelegung. Laden bei Arbeit an Fresh-Konfiguration oder Fresh-Plugins.
---

# Fresh Editor

## Pfade

- Programm `/usr/share/fresh-editor/fresh`, Aufruf `/usr/bin/fresh`
- Konfiguration `~/.config/fresh/` (config.json, plugins/, themes/), Logs `~/.local/state/fresh/logs/`
- Sitzungen als Unix-Sockets unter `/run/user/1000/fresh/`
- Typen der Plugin-API: `/usr/share/fresh-editor/plugins/lib/fresh.d.ts`

## Plugins

- TypeScript in einer QuickJS-Sandbox. Beim Start gescannt: `/usr/share/fresh-editor/plugins/` und `~/.config/fresh/plugins/`; Pakete des pkg-Plugins unter `~/.config/fresh/plugins/packages/`.
- Alle Positionen der API (`addOverlay`, `insertText`, `deleteRange`, `getCursorPosition`, `getBufferText`) sind UTF-8-Byte-Offsets, keine Zeichenindizes. Bei Umlauten und Rahmenzeichen Zeichenindex in Byte-Offset umrechnen.
- `registerCommand` mit Kontext `null`, nicht `"normal"`: `"normal"` gehört zum vi-Modus und versteckt den Befehl in der normalen Palette.
- Eigene Befehle dürfen Klartextnamen haben; `%cmd.name` ist nur für Übersetzungen eingebauter Befehle.

## Bedienung und Fernsteuerung

- Befehlspalette `Ctrl+P` (nicht Ctrl+Shift+P), Präfix `>` filtert auf Befehle.
- Sitzungen kennen nur `open-file`, es gibt keine Fernsteuer-API: Tests laufen über `tmux send-keys`, Prüfung über `tmux capture-pane -e -p` (Screenshots: Skill screenshots).
- Nie `pkill fresh`, Goran hat womöglich eine eigene Instanz offen. Nur die eigene Pane beenden (`tmux send-keys -t %PANE C-q`) oder die eigene PID gezielt.
- F2 ist mit `lsp_rename` bzw. `file_explorer_rename` belegt, nicht überschreiben; F6 wechselt konfliktfrei zwischen Editor und Dateibaum.
