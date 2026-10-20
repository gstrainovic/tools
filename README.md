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
| `mailbox.py` | Postfächer per IMAP/SMTP aus der Kommandozeile lesen und schreiben |
| `thunderbird_konten.py` | Thunderbird um die fehlenden Konten aus der mailbox-Konfiguration ergänzen |
| `geheimnisse.py` | Dateien mit Zugangsdaten über den Bitwarden Secrets Manager zwischen Geräten abgleichen |
| `ads.py` | Google-Ads-Konto über die Google Ads API: Kampagnen auflisten, abfragen, entfernen |
| `gsc.py` | Google Search Console über die Search Console API: Properties, Sitemaps, URL-Prüfung, Suchanfragen; `add-domain DOMAIN` legt eine Domain-Property an (TXT-Token per Site Verification API, Eintrag per Infomaniak-API, bestätigen, Property und Sitemap hinzufügen) |
| `bing.py` | Microsoft-Advertising-Konto über die Bing Ads API: Kampagnen, Anzeigen, Ziel-URLs, Budget |
| `fr_po_pruefen.py` | Französische Texte (`.po`, Shopware-Snippets, config.xml, composer.json, REDAXO `.lang`, PHP-Export) nach den Regeln des französischen WordPress-Teams prüfen (SPTE-Typografie, Glossar, Platzhalter), gemeinsame Prüfung der Plugin-Repos |
| `leerlauf-aus.sh` | Dev-Instanz (Infomaniak) schaltet sich nach 2 h ohne SSH-Verbindung ab; Einrichtung per `leerlauf-aus-installieren.sh user@host` |
| `dev-instanz-wecken.sh` | Abgeschaltete oder zurückgestellte Dev-Instanz starten, bis SSH antwortet; richtet fehlende Leerlauf-Abschaltung ein |
| `setup.sh` | Einrichtung auf einem neuen Rechner |
| `link.sh` | Scripts nach `~/.local/bin`, Skills nach `~/.claude/skills` und die globalen Dateien aus `skills-privat/claude/` verknüpfen (Teil von `setup.sh`) |
| `hooks/modellwahl.sh` | Claude-/Codex-Hook vor Agent, Workflow und spawn_agent: Modellhinweis passend zum Programm |
| `hooks/agent-auftrag.sh` | Claude-/Codex-Hook vor Agentenaufträgen: lehnt Video/Film ohne die Regeln aus produktvideos ab («nie eingebrannt») |
| `hooks/erst-lokal.sh` | Claude-/Codex-Hook vor unterstützten Recherche-Werkzeugen und Agentenaufträgen: verlangt seit der letzten Nutzernachricht lokale Suche; Aufträge mit «zuerst lokal» laufen durch |
| `hooks/bash-bearbeiten.sh` | Claude-/Codex-Hook vor Bash: Hinweis «Edit/Write statt sed, Heredoc oder Umleitung», wenn ein Befehl eine Datei schreibt |
| `hooks/browser-profil.sh` | Claude-Hook vor Bash: sperrt frische oder kopierte Browser-Profile (`playwright-cli … open`, `state-load`, `chrome-sitzung`); erlaubt ist nur das Anhängen an Gorans Chrome (`chrome-anhaengen`). Tests `bash hooks/test_browser_profil.sh` |
| `hooks/skill-hinweis.sh` | Claude-/Codex-Hook vor Shellbefehlen, Dateiänderungen, Browserarbeit und bei jedem Prompt: erinnert an passende, noch nicht gelesene Skills |
| `hooks/befunde-eingetragen.sh` | Stop-Hook für beide Programme: verlangt bei Befunden eine TODO-Änderung seit der letzten Nutzernachricht, liefert auch bei Freigabe JSON |
| `hooks/transkript-sichern.sh` | PreCompact-Hook für beide Programme: sichert `transcript_path` aus der JSON-Eingabe unter einem eindeutigen Namen |
| `hooks/security-guidance-codex.py` | Zusätzlicher Codex-PostToolUse-Hook für `^apply_patch$`: reicht jede Patchdatei als Edit/Write an die Regeln des aktivierten Plugins security-guidance weiter |
| `hooks/codex-hook-ausgabe.py` | Entfernt die in Codex unzulässigen Claude-Telemetriefelder `metrics` und `rewakeSummary`; richtet den Adapter in den Codex-Startskripten von security-guidance und claude-security ein |

### Hooks in Claude Code und Codex

Die gemeinsamen Skripte stehen unter `hooks/`. Eingerichtet sind sie in `~/.claude/settings.json`
und `~/.codex/hooks.json`; projektspezifische Hooks kommen im jeweiligen Repo dazu. Globale
Einstellungsdateien enthalten auch Zugangsdaten: nur den Schlüssel `hooks` lesen oder übertragen.
Neue oder geänderte Codex-Hookdefinitionen unter `/hooks` prüfen und freigeben.

Codex meldet Shellbefehle als `Bash` mit `tool_input.command` und Patches als `apply_patch`
mit dem Patch in demselben Feld. Die Matcher `Edit|Write` treffen auch Codex-Patches;
die Skripte behandeln trotzdem den tatsächlichen Namen `apply_patch`. Agenten verwenden
`message` statt Claudes `prompt`; Browserarbeit kann über `mcp__cua_repl__js` laufen.
Die Protokollauswertung versteht Claude-Nachrichten und Codex-`response_item`-Einträge.
Das Codex-Protokollformat ist laut Dokumentation keine stabile Schnittstelle.

Stop-Hooks geben bei Freigabe `{}` aus; Blockierungen verwenden `decision: "block"` und `reason`.
Codex 0.162.1 lehnt darüber hinaus unbekannte JSON-Felder ab. Claude-Plugins liefern unter anderem
`metrics` und `rewakeSummary`, die Codex nicht akzeptiert. Der Ausgabeadapter entfernt nur diese
Telemetriefelder; Sicherheitskontext, Entscheidungen, Standardfehler und Fehlercodes bleiben erhalten.
Beim SDK-Start wird Claudes vorgeschaltetes `async`-JSON in ein einzelnes Codex-Ergebnis übersetzt.
Die vorhandenen Hook-Befehle rufen den Adapter über die angepassten Startskripte im Codex-Plugin-Cache
auf. Unveränderte Sicherungen liegen jeweils als `*.vor-codex-adapter` daneben. Claudes Plugin-Cache
bleibt getrennt. Ein globaler Codex-SessionStart-Hook richtet den Adapter bei Sitzungsbeginn auch
für neu installierte Pluginversionen ein; diese Definition muss unter `/hooks` freigegeben sein.
Die Einrichtung lässt sich auch direkt ausführen:

```bash
uv run --no-project python hooks/codex-hook-ausgabe.py --einrichten
```

Der separate Sicherheitsadapter ergänzt die Patchprüfung des installierten Plugins.
Er benötigt Python ab 3.11 und wird mit `uv run --no-project python` aufgerufen.
Er respektiert ein deaktiviertes Plugin und sucht die installierten Versionen unter `CODEX_HOME`.

Die Programme bieten unterschiedliche Ereignisse: Codex' gehostete Websuche löst keine lokalen
Werkzeug-Hooks aus. Claude-spezifische Plugin-Ereignisse und Optionen wie `UserPromptExpansion`
und `asyncRewake` haben dadurch nicht automatisch dieselbe Wirkung in Codex.
Grundlagen: [Codex-Hooks](https://developers.openai.com/de-DE/docs/hooks),
[Claude-Code-Hooks](https://code.claude.com/docs/en/hooks).

Prüfung der gemeinsamen Skripte mit beiden Eingabeformaten:

```bash
uv run --no-project python -m unittest discover -s tests -p 'test_hook_kompatibilitaet.py'
uv run --no-project python -m unittest discover -s tests -p 'test_security_guidance_codex.py'
uv run --no-project python -m unittest discover -s tests -p 'test_codex_hook_ausgabe.py'
bash hooks/test_befunde_eingetragen.sh
```

Die Prüfung des installierten Stop-Hooks verwendet den Ausgabevertrag der tatsächlich installierten
Codex-Version 0.162.1 (`tests/fixtures/codex-0.162.1-stop.schema.json`), einschliesslich des Verbots
zusätzlicher Felder. Syntaktisch gültiges JSON allein reicht als Prüfung nicht aus.

Unter `skills/` liegen User-Skills für Claude Code, je Ordner eine `SKILL.md`.

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

### ads

```bash
ads login                                  # einmal: OAuth im Browser, Refresh-Token nach ~/.config/google-ads/
export GOOGLE_ADS_CUSTOMER_ID=8173987962
ads campaigns [--all]                      # ID, Status, Typ, Budget, Name
ads query "SELECT campaign.name FROM campaign"
ads remove ID [ID ...] [--dry-run]
ads create SPEC.json [--validate-only]     # Suchkampagne, immer pausiert, Gesamtbudget mit Enddatum
ads enable ID | ads pause ID
```

Läuft mit `uv` (Abhängigkeiten im Skriptkopf). Zugang: OAuth-Client «Google Ads CLI» (Desktop) im
Cloud-Projekt `auto-service` (`gen-lang-client-0650867108`), Zugriffsebene der Ads API mindestens Explorer;
Developer-Tokens gibt es seit 09.09.2026 nicht mehr. Google Ads Scripts sieht Smart-Kampagnen nicht, die API schon.

### bing

```bash
bing login                                 # einmal: Google-Anmeldung, Refresh-Token nach ~/.config/bing-ads/
bing campaigns | bing ads
bing replace-url ALT NEU [--dry-run]
bing budget ID CHF | bing pause ID | bing enable ID
bing report [--period Today|LastSevenDays|Last30Days]   # Standard Last30Days, Werte des API-Enums ReportTimePeriod
bing network [--set alle|bing]             # alle = mit DuckDuckGo, Yahoo, Ecosia (Microsoft-Partnernetz)
```

Developer-Token, Kunden- und Konto-ID in `~/.config/bing-ads/config.toml`; das Konto ist per Google angelegt,
angemeldet wird mit dem OAuth-Client von `ads`. suds schickt leere Felder mit, darum `blank()` vor jedem Update.

### mailbox

```bash
mailbox accounts                           # Konten und Verbindungstest
mailbox list --unread                      # ungelesene Mails aller Konten
mailbox read firma 42                      # Kopfzeilen, Anhänge, Text
mailbox send firma --to x@y.ch --subject "Offerte" --body-file text.txt --attach offerte.pdf
mailbox reply firma 42 --body-file antwort.txt
```

Für Agenten gedacht, die Mails im Namen einer Person lesen und senden, während die Person
dasselbe Postfach in einem normalen Mailprogramm sieht. Liest und schreibt direkt auf dem
Server: gesendete Mails landen im Ordner «Gesendet», gelesen ist überall gelesen, Antworten
hängen am Gesprächsfaden. Nur Python-Standardbibliothek. Konten nach der Vorlage
`mailbox-accounts.example.toml` in `~/.config/mail/accounts.toml`, Passwörter je Konto in
einer eigenen Datei.

### thunderbird-konten

```bash
thunderbird-konten --dry-run               # zeigt, welche Konten Thunderbird fehlen
thunderbird-konten                         # legt sie an (Thunderbird vorher schliessen)
```

Gleicht Thunderbird (Flatpak ESR, Profil aus `installs.ini`) mit `~/.config/mail/accounts.toml` ab:
fehlende Postfächer werden IMAP-Konto mit SMTP-Server (993/465 SSL), ein Konto mit dem `login` eines
vorhandenen Postfachs wird zusätzliche Identität dort. Ergänzt nur, sichert vorher `prefs.js`,
`logins.json` und `key4.db` im Profil und trägt die Passwörter über NSS verschlüsselt in `logins.json` ein.
Bricht ab, solange Thunderbird läuft. Ein zweiter Lauf ändert nichts.

### geheimnisse

```bash
geheimnisse status                         # Tresor gegen lokale Dateien: gleich, abweichend, fehlt lokal
geheimnisse hochladen dms/.env ~/.config/elevenlabs/key
geheimnisse holen                          # fehlende Dateien an ihren Platz, --ueberschreiben für abweichende
```

Dateien mit Zugangsdaten (`.env`, Schlüssel, Tokens) liegen im Bitwarden Secrets Manager
(vault.bitwarden.eu, Organisation «Strainovic IT», Projekt `strainovic`, Gratisplan mit 3 Projekten und
3 Gerätekonten). Ein Geheimnis heisst wie der Pfad der Datei: relativ zu `~/projects` (`dms/apps/dms/.env`)
oder mit `~/` relativ zum Home-Verzeichnis (`~/.config/elevenlabs/key`); der Wert ist der Dateiinhalt. Werte
werden nie ausgegeben, auch nicht der Fehlertext von `bws`, weil er Argumente wiederholt. Nach jeder
Änderung einer solchen Datei wieder hochladen. Tests ohne Netz: `python3 -m unittest test_geheimnisse.py`.

Neues Gerät:

1. `bws` installieren (bitwarden/sdk-sm): unter Linux die Binärdatei aus dem GitHub-Release nach
   `~/.local/bin`, unter Windows `iwr https://bws.bitwarden.com/install | iex`.
2. `bws config server-base https://vault.bitwarden.eu`
3. Zugriffstoken des Geräts nach `~/.config/bws/token` (Windows `%USERPROFILE%\.config\bws\token`),
   Rechte 600. Je Gerät ein eigenes Gerätekonto mit eigenem Token (`laptop`, `pc-2`, das dritte ist frei),
   damit sich ein Gerät einzeln sperren lässt. Ein Token zeigt der Web-Tresor nur beim Erzeugen
   (Gerätekonto → «Zugriffstoken erstellen»); Widerrufen verlangt das Master-Passwort.
4. `geheimnisse holen`

### fr-po-pruefen

```bash
fr-po-pruefen plugin/*/languages/*-fr_FR.po --ausnahmen fr-ausnahmen.toml   # Exit 1 bei Fund
fr-po-pruefen snippet/x.fr.json config/config.xml composer.json lang/fr_fr.lang fr-texte.json
fr-po-pruefen --glossar-aktualisieren   # Glossar-CSV von translate.wordpress.org neu laden
```

Läuft per `uv run --script` (Abhängigkeit `regex` für die Lookbehinds aus SPTE). Je Fund: Datei:Zeile, Regel,
englisches Original und französischer Text (geschützte Leerzeichen sichtbar als `<U+00A0>`, `<U+202F>`). Geprüft
werden Typografie und verbotene Wörter nach SPTE (Association-WPFR/SPTE 3.1.1, `utils/rules.js`, GPL-2.0-or-later,
nachgebaut, dazu U+00A0 vor `%` und vor Einheiten aus dem Handbuch), das Glossar des französischen Teams wie
GlotDict (`fr-po/glossar-fr.csv`, Abrufdatum in `fr-po/glossar-fr.quelle`) sowie Platzhalter und HTML-Tags wie im
Original. Formate: `.po`, Shopware-Snippet `*.fr.json` gegen `*.en.json`, Shopware `config.xml` (`lang="fr-FR"`
gegen das Element ohne `lang`), `composer.json` (`extra.*.fr-FR` gegen `en-GB`, ohne Links), REDAXO `fr_fr.lang`
gegen `en_gb.lang` und Textpaare-JSON `[{"stelle", "en", "fr"}]` aus einem PHP-Export (ohne `en` nur Typografie).
Regeln, Abweichungen von SPTE und das Format der Ausnahmedatei stehen im Kopf des Skripts; wann korrigiert und
wann eine Ausnahme eingetragen wird, im Skill wp-plugin-ch. klara-shop-connector und bexio-formular-connector
rufen es in `bin-test.sh` auf.

### Webseiten für Recherchen lesen

Reihenfolge, vom billigsten zum teuersten Weg; die Ausgabe immer durch einen Filter (`rg`, kurzes
Python) schicken, nie ganze Seiten in den Verlauf holen:

1. `curl -sL -A "Mozilla/5.0" <url>`: reicht für statische Seiten, Sitemaps und öffentliche JSON-Schnittstellen.
2. `LIGHTPANDA_DISABLE_TELEMETRY=true lightpanda fetch --dump markdown --wait-until networkidle <url>`:
   für Seiten, die erst per JavaScript entstehen. lightpanda (lightpanda-io/browser, Binärdatei aus dem
   GitHub-Release nach `~/.local/bin`) ist ein Browser ohne Oberfläche und gibt die fertige Seite als Markdown
   aus. Ohne `--wait-until networkidle` fehlen nachgeladene Inhalte; `--dump-selector <css>` schneidet auf
   ein Element zu.
3. `google-chrome --headless=new --virtual-time-budget=8000 --dump-dom <url>`: wenn lightpanda eine Seite
   nicht schafft; liefert rohes HTML und ist langsamer.
4. Playwright mit dem installierten Chrome nur, wenn geklickt werden muss; die Chrome-Erweiterung nur für
   Seiten hinter einem Login.

Bot-Schutz (Cloudflare-Prüfseite) umgeht keiner dieser Wege, auch Jina nicht.

Websites finden, die eine bestimmte Technik einbinden: `urlscan search 'domain:js.hs-scripts.com AND
page.domain:*.ch' --all --size 1000` (urlscan/urlscan-cli, Binärdatei aus dem GitHub-Release nach
`~/.local/bin`). Der Schlüssel des Kontos kommt per `urlscan key set -` aus der Standardeingabe in den
GNOME-Schlüsselbund oder als `URLSCAN_API_KEY` aus `~/.config/urlscan/key`; `urlscan search count` zählt nur.

## Setup

```bash
bash ~/projects/tools/setup.sh
```

Voraussetzungen: `uv`, `cargo`, `python3`. Alles Weitere installiert das Script.

## Tests

```bash
bash tests/test-repo-consistency.sh
uv run --with regex python3 -m unittest test_fr_po_pruefen.py
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
