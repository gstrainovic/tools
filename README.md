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
| `ads.py` | Google-Ads-Konto über die Google Ads API: Kampagnen auflisten, abfragen, entfernen |
| `bing.py` | Microsoft-Advertising-Konto über die Bing Ads API: Kampagnen, Anzeigen, Ziel-URLs, Budget |
| `setup.sh` | Einrichtung auf einem neuen Rechner |

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

## Setup

```bash
bash ~/projects/tools/setup.sh
```

Voraussetzungen: `uv`, `cargo`, `python3`. Alles Weitere installiert das Script.

## Tests

```bash
bash tests/test-repo-consistency.sh
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
