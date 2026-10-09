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
| `link.sh` | Scripts nach `~/.local/bin` und Skills nach `~/.claude/skills` verknüpfen (Teil von `setup.sh`) |
| `hooks/modellwahl.sh` | Claude-Code-Hook vor Agent und Workflow: legt die Modellwahl aus dem Skill arbeitsweise vor |
| `hooks/agent-auftrag.sh` | Claude-Code-Hook vor Agent und Workflow: lehnt Aufträge zu Video/Film ohne die Regeln aus produktvideos ab («nie eingebrannt») |
| `hooks/erst-lokal.sh` | Claude-Code-Hook vor WebSearch, WebFetch, Jina sowie Agent und Workflow mit Recherche-Auftrag: lehnt ab, solange seit der letzten Nutzernachricht keine lokale Suche (rg/grep, Grep, Glob) im Transkript steht; Aufträge mit «zuerst lokal» laufen durch |
| `hooks/bash-bearbeiten.sh` | Claude-Code-Hook vor Bash: Hinweis «Edit/Write statt sed, Heredoc oder Umleitung», wenn ein Befehl eine Datei schreibt |
| `hooks/skill-hinweis.sh` | Claude-Code-Hook vor Bash, Edit/Write, Claude in Chrome und bei jedem Prompt: Hinweis, welcher noch nicht geladene Skill zum Schritt gehört (Tabelle «Anlass → Skill» im Script) |

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
geheimnisse hochladen dms/.env ~/.config/jina/key
geheimnisse holen                          # fehlende Dateien an ihren Platz, --ueberschreiben für abweichende
```

Dateien mit Zugangsdaten (`.env`, Schlüssel, Tokens) liegen im Bitwarden Secrets Manager
(vault.bitwarden.eu, Organisation «Strainovic IT», Projekt `strainovic`, Gratisplan mit 3 Projekten und
3 Gerätekonten). Ein Geheimnis heisst wie der Pfad der Datei: relativ zu `~/projects` (`dms/apps/dms/.env`)
oder mit `~/` relativ zum Home-Verzeichnis (`~/.config/jina/key`); der Wert ist der Dateiinhalt. Werte
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
