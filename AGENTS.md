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
`~/projects/skills-privat` (setup.sh klont es) und von dort aus `skills-privat/claude/` die globalen Dateien
`~/.claude/CLAUDE.md`, `~/.claude/settings.json`, `~/.claude/caveman-statusline.sh`, `~/projects/AGENTS.md`
(Quelle `projects-AGENTS.md`) und `~/.agents/.skill-lock.json` (Quelle `skill-lock.json`, Liste der fremden Skills
für `npx skills`); eine vorhandene echte Datei wird als `<ziel>.vor-link-<Zeit>` gesichert.

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
| `thunderbird_konten.py` | Thunderbird (Flatpak ESR) um fehlende Konten aus `accounts.toml` ergänzen, als `~/.local/bin/thunderbird-konten` verknüpft |
| `test_thunderbird_konten.py` | Unit-Tests gegen ein Test-Profil im tmp-Ordner, NSS echt (`python3 -m unittest test_thunderbird_konten.py`) |
| `fr_po_pruefen.py` | Französische `.po` prüfen (SPTE-Typografie, Glossar, Platzhalter), als `~/.local/bin/fr-po-pruefen` verknüpft; Aufruf in den `bin-test.sh` der WordPress-Plugin-Repos |
| `test_fr_po_pruefen.py` | Tests dazu, Fälle aus SPTEs `regex.test.js` (`uv run --with regex python3 -m unittest test_fr_po_pruefen.py`) |
| `fr-po/` | Glossar des französischen Teams als CSV mit Quelle und Abrufdatum (`fr-po-pruefen --glossar-aktualisieren`) |
| `chrome_sitzung.py` | Cookies gewählter Domains aus Gorans Chrome entschlüsseln und als Speicherstand für `playwright-cli state-load` schreiben, als `~/.local/bin/chrome-sitzung` verknüpft; gesperrt durch `hooks/browser-profil.sh` (Gorans Regel: nur Gorans Chrome per CDP, Skill browser-wahl) |
| `test_chrome_sitzung.py` | Tests gegen eine Cookie-Datenbank im tmp-Ordner (`uv run --with cryptography python -m unittest test_chrome_sitzung.py`) |
| `chrome_anhaengen.py` | playwright-cli-Session `gchrome` über die Playwright Extension an Gorans Chrome hängen, ohne Dialog, als `~/.local/bin/chrome-anhaengen` verknüpft; Einrichtung im Skill browser-wahl |
| `test_chrome_anhaengen.py` | Tests mit falschem playwright-cli im PATH (`python3 -m unittest test_chrome_anhaengen.py`) |
| `chrome-policy/` | Chrome-Richtlinie, die die Playwright Extension ohne Klick installiert (nach `/etc/opt/chrome/policies/managed/`) |
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
