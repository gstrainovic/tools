# Tools — TUI/Terminal Automation

Hilfsmittel zum Steuern und Beobachten von Terminal-Anwendungen unter GNOME Wayland.
Stack: Ghostty → tmux → TUI-Tools. Reine Terminal-Werkzeuge, keine Editor- oder Dateimanager-Configs.

## Setup auf neuem PC

```bash
bash ~/projects/tools/setup.sh
```

Installiert: System-Pakete (tmux, wkhtmltopdf, timg, ydotool, ImageMagick), tmux2html,
mcp-tui-driver, die Konten-Vorlage für mailbox und die MCP-Config. `link.sh` (läuft in `setup.sh`,
auch allein ausführbar, idempotent) verknüpft die Scripts nach `~/.local/bin` und jeden Ordner unter
`skills/` nach `~/.claude/skills/<name>`, dazu die Skills aus dem privaten Repo
`~/projects/skills-privat` (setup.sh klont es) und von dort die globale `~/.claude/CLAUDE.md`
(`skills-privat/claude/CLAUDE.md`; eine vorhandene echte Datei wird als `CLAUDE.md.vor-link-<Zeit>` gesichert).

**Voraussetzungen:** `uv`, `cargo`, `python3`.

## Dateien

| Datei | Beschreibung |
|-------|-------------|
| `tmux2png` | tmux-Session → lesbares PNG via tmux2html + wkhtmltoimage |
| `gui-screenshot.sh` | Vollbild-Screenshot via ydotool Shift+Print (GNOME Wayland), als `~/.local/bin/gui-screenshot` verknüpft |
| `img-proto-test` | Vergleich der drei Terminal-Bildprotokolle via timg |
| `mailbox.py` | Postfächer per IMAP/SMTP lesen und schreiben, als `~/.local/bin/mailbox` verknüpft |
| `test_mailbox.py` | Unit-Tests für `mailbox.py` ohne Netz (`python3 -m unittest test_mailbox.py`) |
| `mailbox-accounts.example.toml` | Vorlage für `~/.config/mail/accounts.toml` |
| `.bashrc` | Shell-Aliase, wird von `~/.bashrc` gesourced |
| `setup.sh` | Einrichtungs-Script für neuen PC |
| `link.sh` | Verknüpfungen für Scripts und Skills |
| `skills/` | User-Skills für Claude Code, je Ordner eine `SKILL.md` |
| `mcps.json` | MCP-Server-Konfigurationen (aus `~/.claude.json`) |
| `tests/` | Konsistenz-Tests für Doku, Scripts und Skills |

## Screenshots und TUI-Steuerung

tmux2png, gui-screenshot, tmux-mcp und tui-driver: Skill screenshots (`skills/screenshots/SKILL.md`).

## img-proto-test

Zeigt dasselbe Bild nacheinander per iTerm2-Protokoll, Kitty Graphics Protocol und Sixel,
mit Zeitmessung. **Muss außerhalb von tmux laufen** — tmux filtert die Protokolle weg.
Ghostty spricht Kitty Graphics Protocol nativ.

## mailbox

Konten, IMAP/SMTP, Befehle und Entwicklung: Skill mailbox (im privaten Repo `~/projects/skills-privat`).

## Tests

```bash
bash tests/test-repo-consistency.sh
```

Prüft, dass Doku und `setup.sh` nur auf real vorhandene Dateien verweisen, dass keine
Referenzen auf abgeschaffte Tools zurückkommen, dass alle Scripts syntaktisch valide
und ausführbar sind, dass jeder Skill gültiges Frontmatter hat und dass `link.sh` in einem
leeren HOME alle Verknüpfungen anlegt.
