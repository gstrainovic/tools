---
name: browser-wahl
description: Welches Werkzeug für Browserarbeit (API, playwright-cli an Gorans Chrome oder Skript; Claude in Chrome verboten), Formularfelder lesen, Login per Autofill, Sessions, Kennwörter, erkundete Abläufe als Skill festhalten. Laden, bevor im Browser etwas erkundet, eingerichtet oder geprüft wird und wenn ein Login oder das Anhängen an Chrome hakt. Recherche ohne Browser steht im Skill recherche.
---

# Browser-Werkzeug wählen

Reihenfolge, das erste passende nehmen:

1. **API oder CLI des Systems.** Kein Browser, wenn es eine Schnittstelle gibt. Fehlt ein Token: Abschnitt
   «API-Token statt Durchklicken» in `~/.claude/CLAUDE.md` (Token anlegen lassen, Übergabe per Zwischenablage).
   Manche Systeme geben einen Token auch gegen Benutzername und Kennwort aus (Flarum `POST /api/token`); welche
   Portale das können und welche verbieten, steht in `find-jobs/akquise/recherche/token-statt-browser-2026-10.md`.
2. **playwright-cli angehängt an Gorans laufenden Chrome** (Skill `playwright-cli`, Abschnitt «Gorans Chrome
   anhängen») für alles Interaktive: Masken erkunden, einrichten, prüfen, Formulare, Portale mit Login. Gorans
   Cookies, Logins und Captcha-Vertrauen gelten so überall. Kein Tool-Schema im Kontext, Snapshots landen als Datei.
   **Verboten: frische oder kopierte Profile** (Gorans Regel): kein `playwright-cli … open`, kein `state-load`, kein
   `chrome-sitzung`. Ohne Gorans Cookies erscheinen Captchas (hCaptcha bei Zendesk) und Logins fehlen. Der Hook
   `~/projects/tools/hooks/browser-profil.sh` sperrt diese Befehle.
3. **Skript** (Playwright mit `playwright-core`, `channel: 'chrome'`) nur für fertige, wiederholte Abläufe ohne
   Login und ohne fremde Website: E2E-Tests und Screenshots gegen localhost oder die eigene Website.
**Claude in Chrome ist verboten** (Gorans Regel), auch als Rückfall: keine `mcp__claude-in-chrome__*`-Werkzeuge.
Geht das Anhängen per CDP nicht, Goran den Fehler in einem Satz melden und warten.

**Je Teilaufgabe neu wählen, nicht je Sitzung:** Wer schon im Browser ist, liest vor jeder neuen Teilaufgabe (anderes
Objekt, anderer Ablauf) zuerst lokal (`rg` in `~/projects`), dann die API-Doku des Systems und fehlende Rechte des
Tokens, bevor er weiterklickt. Nur was die Oberfläche selbst prüfen soll (Verhalten des Editors, Weg des Kunden),
bleibt im Browser.

Das Playwright-MCP-Plugin ist abgeschaltet (`~/.claude/settings.json`), playwright-cli deckt alles ab. Nie
`npx playwright install`: playwright-cli nutzt den installierten Chrome.

## Recherche

Nachschlagen, Websuche, Jina, Exa, Codex-Websuche und Recherche-Agenten: Skill `recherche`. Hier gilt nur:
Formularfelder (Pflichtfelder, Optionen, Zeichengrenzen, Captcha) liest playwright-cli im Browser, nicht Jina oder
curl: Viele Formulare entstehen erst per JavaScript, und ohne Browser bleibt «nicht geprüft» stehen. Agenten, die
Formulare vorbereiten, darum nie playwright-cli verbieten, nur Claude in Chrome.

## Mehrere Seiten nacheinander

- Mehrere Seiten in einem `run-code`: `goto` mit `waitUntil: 'load'`, nach einem Fehler erst
  `waitForLoadState` und ein paar Sekunden warten, sonst reisst eine noch laufende Weiterleitung alle folgenden
  Aufrufe mit («interrupted by another navigation»). Fehlt ein Login-Indikator (find-jobs: Skill `portal-login`):
  Seite in Gorans Chrome per Autofill anmelden, dann weiter.
- Für jede Aufgabe einen eigenen Tab (`tab-new`) und ihn bis zum Ende nicht für anderes benutzen; ein Formular, auf
  das Goran wartet (Captcha, Freigabe), bleibt in seinem Tab stehen.
- Cookies reichen für die Logins aller find-jobs-Portale (Stand der Prüfung: LinkedIn, Upwork, freelancermap,
  freelance.de, Freelancer.com, Wellfound). Local Storage wird nicht übernommen; braucht eine Seite ihn, die
  Werte per `localstorage-set` nachtragen oder anhängen (unten).

## Gorans Chrome anhängen

- `playwright-cli attach --cdp=chrome --session=gchrome` hängt sich an den laufenden Chrome mit Gorans Profil;
  danach `playwright-cli -s=gchrome …`. Voraussetzung: in `chrome://inspect/#remote-debugging` ist «Allow remote
  debugging for this browser instance» angehakt; scheitert das Anhängen, Goran darum bitten. Chrome 155 antwortet
  auf `/json/version` mit 404 und `--cdp=chrome` scheitert: dann die WebSocket-Adresse aus
  `~/.config/google-chrome/DevToolsActivePort` nehmen, `attach --cdp="ws://127.0.0.1:9222$(sed -n 2p
  ~/.config/google-chrome/DevToolsActivePort)" --session=gchrome`.
- **Dialog «Remote-Debugging zulassen»:** Chrome fragt bei jeder neuen Verbindung, nicht einmal pro Chrome-Lauf.
  Dauerhaft erlauben geht nicht (Chrome-Team, chrome-devtools-mcp Issue 825, «not planned»: sonst könnte jedes
  Programm unbemerkt das Profil auslesen); empfohlen sind lange Verbindungen. Darum: vor jedem Anhängen
  `playwright-cli -s=gchrome tab-list` probieren und eine laufende Session weiterverwenden, nie schliessen. Hängt
  das Anhängen im Timeout («ws connecting»), wartet der Dialog: Goran einmal bitten, ihn zu bestätigen, und erst
  nach seinem «freigegeben» genau einmal neu anhängen. Nicht mehrfach versuchen (jeder Versuch öffnet einen neuen
  Dialog, ein bestätigter alter nützt dann nichts) und Chrome dafür nie neu starten (der Neustart verlangt die
  Freigabe erneut).
- Läuft Gorans Chrome nicht (nur ein
  Playwright-Chromium mit `--user-data-dir=/tmp/playwright…`), `google-chrome --restore-last-session &` starten
  und 25 s warten.
- **Selbst einloggen mit gespeichertem Kennwort (Chrome-Passwortmanager):** im Login-Tab `click` ins Benutzer- oder
  E-Mail-Feld, dann `press ArrowDown` und `press Enter`: Chrome füllt Benutzer und Kennwort aus seinem Vorschlag.
  Mit `eval` nur die Länge der Feldwerte prüfen (nie den Wert), dann anmelden (Enter oder Absenden-Knopf). So am
  18.10.2026 bei login.wordpress.org und login.klara.ch geklappt. Erst wenn danach ein Feld leer bleibt (kein
  gespeichertes Kennwort), 2FA oder ein Captcha kommt: Goran in einem Satz um den Login bitten.
- Klicks per Ref hängen in einem Tab im Hintergrund («waiting for element to be visible, enabled and stable»):
  `run-code` mit `await page.bringToFront()`, Formulare dann per `el.form.requestSubmit(el)` absenden; Dateifelder
  per `page.setInputFiles('<selector>', '<pfad>')` statt Dateidialog.
- Passwort-Rückfragen von Meta («Bitte gib dein Passwort erneut ein» beim Anlegen einer App, beim Anzeigen des
  App-Geheimcodes) kann playwright-cli nicht ausfüllen: in einem Satz melden, Goran tippt es
  im offenen Dialog, danach weiterarbeiten.
- Eigene Arbeit in einem eigenen Tab (`tab-new <URL>`), Gorans offene Tabs nicht anfassen, eigene Tabs am Schluss
  schliessen (`tab-close`). Popups öffnen sich als neuer Tab: `tab-list`, dann `tab-select <Nummer>`.
- **Vor jedem `goto`, `run-code` oder Skript zuerst `tab-list`:** Nach dem Anhängen ist der aktive Tab einer von
  Gorans, und `page` in `run-code` zeigt auf ihn; ein `page.goto` überschreibt dann seine Arbeit. Darum erst einen
  eigenen Tab öffnen (`tab-new`) und prüfen, dass er `(current)` ist; Skripte öffnen ihren Tab selbst
  (`const tab = await page.context().newPage()`, am Ende `tab.close()`, Muster `find-jobs/linkedin/suche_cli.py`).
- Ref-Namen ändern sich nach einem Seitenwechsel (`e123` wird `f2e123`): vor jedem Klick frischen Snapshot nehmen,
  nicht alte Refs wiederverwenden.
- In Popups (OAuth, Facebook-Einrichtung) nie Escape drücken: Es schliesst das ganze Fenster, alle Schritte samt
  Bestätigungscode sind verloren, und Meta sperrt einen neuen Anruf für 60 Minuten. Offene Listen per Klick auf
  eine Option schliessen.
- Eigene Auswahllisten (Facebook, Meta) reagieren nicht auf `click <ref>`: per `run-code` die `boundingBox()` der
  Option holen und `page.mouse.click()` auf die Mitte setzen.

## Kennwörter

Nie als Befehlsparameter. Login als `run-code`-Datei mit Platzhalter, eine kleine Shell-Hülle setzt das Kennwort
aus `.secrets/` ein und filtert es aus der Ausgabe (`run-code` kennt weder `require` noch `process`). Vorbild:
`myfactory-anbindung/myfactory/cli_login.sh` mit `cli_login.js`.

Liegt kein Kennwort in einer Datei, keine Passwort-Datei von Goran verlangen: in Gorans Chrome per Autofill
anmelden und angehängt per CDP weiterarbeiten.

## Arbeiten mit playwright-cli

- **Vor dem Ausfüllen eines Formulars zuerst den Cookie-Banner akzeptieren** (Screenshot nach dem Laden, Banner
  wegklicken), dann ausfüllen. Grund: Akzeptiert Goran den Banner danach, lädt die Seite neu und alle Eingaben sind
  weg (Bailaho, 18.10.2026).
- Kästchen und Optionen, bei denen `check()` oder `click` in «waiting for element to be visible, enabled and
  stable» hängt, per `locator.evaluate(e => { if (!e.checked) e.click() })` setzen und danach mit `isChecked()`
  zurücklesen. Knöpfe in Googles Oberflächen (Search Console) reagieren nur auf `page.mouse.click()` auf die Mitte der
  `boundingBox()`.
- Schleifen über viele Seiten nie unbeaufsichtigt im Hintergrund starten: zuerst ein Durchgang im Vordergrund mit
  Bildschirmfoto, dann jede weitere Seite einzeln prüfen.

- Einfache Seiten: `snapshot`, dann `click e15`, `fill e7 "…"`, `select`, `dblclick`.
- Seiten mit Frames und Knöpfen, deren Text Zeilenumbrüche hat (ältere ERP-Oberflächen): `run-code` mit einer
  Funktion, die den Frame über `page.frames()` und die URL sucht und Felder per ID anspricht; Ergebnis als JSON
  zurückgeben und erst danach weiterklicken.
- Nachschlagefelder nach dem Tippen mit Tab verlassen, sonst übernimmt die Maske den Wert nicht.
- Gespeichert ist erst, was nach einem Wechsel auf einen anderen Datensatz und zurück wieder dasteht.
- Screenshots für die eigene Kontrolle in den Scratchpad oder `/tmp/<system>-ui/`.
- Protokolle landen in `.playwright-cli/` im Arbeitsverzeichnis und enthalten Seiteninhalte: Ordner in
  `.gitignore`.
- Blockiert der Klassifikator trotz Allow-Regel `Bash(playwright-cli:*)` einen Klick, kann Goran im Dashboard
  (`playwright-cli show`) den einen Knopf selbst drücken, die Session bleibt erhalten.

## Wiederverwendung

Jede erkundete Befehlsfolge kommt sofort in den Skill des Systems (etwa `myfactory`) bzw. als `run-code`-Datei
neben die Skripte des Projekts. Beim nächsten Kunden wird sie abgespielt, nicht neu erkundet.
