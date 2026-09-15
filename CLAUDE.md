# Tools — TUI/Terminal Automation

Hilfsmittel zum Steuern und Beobachten von Terminal-Anwendungen unter GNOME Wayland.
Stack: Ghostty → tmux → TUI-Tools. Reine Terminal-Werkzeuge, keine Editor- oder Dateimanager-Configs.

## Setup auf neuem PC

```bash
bash ~/projects/tools/setup.sh
```

Installiert: System-Pakete (tmux, wkhtmltopdf, timg, ydotool, ImageMagick), tmux2html,
mcp-tui-driver, die Scripts nach `~/.local/bin` (mailbox als Verknüpfung), die Konten-Vorlage für mailbox,
den Claude-Skill und die MCP-Config.

**Voraussetzungen:** `uv`, `cargo`, `python3`.

## Dateien

| Datei | Beschreibung |
|-------|-------------|
| `tmux2png` | tmux-Session → lesbares PNG via tmux2html + wkhtmltoimage |
| `gui-screenshot.sh` | Vollbild-Screenshot via ydotool Shift+Print (GNOME Wayland) |
| `img-proto-test` | Vergleich der drei Terminal-Bildprotokolle via timg |
| `mailbox.py` | Postfächer per IMAP/SMTP lesen und schreiben, als `~/.local/bin/mailbox` verknüpft |
| `test_mailbox.py` | Unit-Tests für `mailbox.py` ohne Netz (`python3 -m unittest test_mailbox.py`) |
| `mailbox-accounts.example.toml` | Vorlage für `~/.config/mail/accounts.toml` |
| `.bashrc` | Shell-Aliase, wird von `~/.bashrc` gesourced |
| `setup.sh` | Einrichtungs-Script für neuen PC |
| `tui-screenshot-skill.md` | Claude-Skill-Dokumentation für tui-screenshot |
| `mcps.json` | MCP-Server-Konfigurationen (aus `~/.claude.json`) |
| `tests/` | Konsistenz-Tests für Doku und Scripts |

## tmux2png

```bash
tmux2png                        # aktuelle Session → /tmp/tmux-TIMESTAMP.png
tmux2png dev                    # Session "dev"
tmux2png dev:0.0                # spezifische Pane
tmux2png dev /tmp/out.png       # mit Ausgabepfad
```

**Intern:** `tmux2html TARGET -o HTML` → `wkhtmltoimage --width 1400 HTML PNG`

**LIMITATION: Erfasst NUR den Text-Layer (ANSI-Zeichen/Farben).**
Kitty-Graphics- und Sixel-Pixel werden vom Terminal-Emulator außerhalb des tmux-Buffers
gerendert → NICHT sichtbar in tmux2png. Für echte Pixel: `gui-screenshot.sh`.

## gui-screenshot.sh

Simuliert Shift+Print via ydotool und wartet auf die neue Datei in `~/Bilder/Bildschirmfotos`.
Startet `ydotoold` bei Bedarf per sudo. `grim` und `gnome-screenshot` funktionieren auf
GNOME 49 nicht (Portal-Bug `Failed to associate portal window`).

## img-proto-test

Zeigt dasselbe Bild nacheinander per iTerm2-Protokoll, Kitty Graphics Protocol und Sixel,
mit Zeitmessung. **Muss außerhalb von tmux laufen** — tmux filtert die Protokolle weg.
Ghostty spricht Kitty Graphics Protocol nativ.

## mailbox

```bash
mailbox accounts                                   # Konten und Verbindungstest
mailbox list [KONTO] --unread                      # ohne KONTO: alle Konten mit Passwortdatei
mailbox read KONTO UID
mailbox search KONTO 'SINCE 01-Sep-2026'           # IMAP-Suchsyntax
mailbox send KONTO --to x@y.ch --subject "…" --body-file text.txt [--attach datei.pdf] [--dry-run]
mailbox reply KONTO UID --body-file text.txt       # Re:, In-Reply-To und References gesetzt
mailbox move KONTO UID Trash
```

Konten in `~/.config/mail/accounts.toml`, Passwörter je Konto in einer eigenen Datei, nie im Repo.
Gesendete Mails landen per IMAP APPEND im Server-Ordner (`sent_folder`), ein fehlender Ordner wird angelegt.
Infomaniak vergibt Gerätekennwörter pro Programm (Manager → Adresse → «Geräte verbunden»).
Python 3.13+: `email.utils.getaddresses` liefert für leere Felder `('', '')`, darum filtert `addresses()` leere
Kopfzeilen vorher; ohne das weist SMTP die Nachricht mit `SMTPRecipientsRefused: {}` ab.

## MCPs für Terminal-Automation

### tmux-mcp (`npx -y tmux-mcp`)
- Sessions/Panes auflisten, Output capturen, Befehle ausführen
- Tools: `list-sessions`, `list-panes`, `capture-pane`, `execute-command`

### tui-driver (`~/.cargo/bin/mcp-tui-driver`)
- TUI-Apps starten, Key-Events senden, Accessibility-Snapshots
- **Achtung:** `tui_screenshot` liefert unlesbaren Pixelbrei → stattdessen `tmux2png`

## Empfohlener Workflow: Screenshot

```
1. tmux ls                          # Session-Namen herausfinden
2. tmux2png SESSION_NAME            # PNG erzeugen
3. Read-Tool → /tmp/tmux-*.png      # PNG in Claude Code anzeigen
```

## Tests

```bash
bash tests/test-repo-consistency.sh
```

Prüft, dass Doku und `setup.sh` nur auf real vorhandene Dateien verweisen, dass keine
Referenzen auf abgeschaffte Tools zurückkommen und dass alle Scripts syntaktisch valide
und ausführbar sind.

## Skill

Der `tui-screenshot` Skill liegt unter `~/.claude/skills/tui-screenshot/SKILL.md`.
