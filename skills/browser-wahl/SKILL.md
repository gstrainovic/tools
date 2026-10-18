---
name: browser-wahl
description: Welches Werkzeug für Browserarbeit (API, playwright-cli, Skript oder Claude in Chrome), Formularfelder lesen, Chrome-Extension und Login per Autofill, Sessions, Kennwörter, erkundete Abläufe als Skill festhalten. Laden, bevor im Browser etwas erkundet, eingerichtet oder geprüft wird und wenn ein Login oder die Chrome-Extension hakt. Recherche ohne Browser steht im Skill recherche.
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
4. **Claude in Chrome** nur als Rückfall, wenn das Anhängen per CDP nicht geht. Den Grund in den Skill des Portals
   schreiben, damit der Rückfall dort gilt und nicht überall.

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
Formulare vorbereiten, darum nie Browser-Werkzeuge verbieten, nur Claude in Chrome.

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
  ~/.config/google-chrome/DevToolsActivePort)" --session=gchrome`. Hängt dieses Anhängen im Timeout («ws
  connecting»), zeigt Chrome einen Dialog «Remote-Debugging zulassen»: Goran bestätigt ihn, dann neu anhängen.
  Läuft Gorans Chrome nicht (nur ein
  Playwright-Chromium mit `--user-data-dir=/tmp/playwright…`), `google-chrome --restore-last-session &` starten
  und 25 s warten.
- Passwort-Rückfragen von Meta («Bitte gib dein Passwort erneut ein» beim Anlegen einer App, beim Anzeigen des
  App-Geheimcodes) kann weder playwright-cli noch die Extension ausfüllen: in einem Satz melden, Goran tippt es
  im offenen Dialog, danach weiterarbeiten.
- Eigene Arbeit in einem eigenen Tab (`tab-new <URL>`), Gorans offene Tabs nicht anfassen, eigene Tabs am Schluss
  schliessen (`tab-close`). Popups öffnen sich als neuer Tab: `tab-list`, dann `tab-select <Nummer>`.
- Ref-Namen ändern sich nach einem Seitenwechsel (`e123` wird `f2e123`): vor jedem Klick frischen Snapshot nehmen,
  nicht alte Refs wiederverwenden.
- In Popups (OAuth, Facebook-Einrichtung) nie Escape drücken: Es schliesst das ganze Fenster, alle Schritte samt
  Bestätigungscode sind verloren, und Meta sperrt einen neuen Anruf für 60 Minuten. Offene Listen per Klick auf
  eine Option schliessen.
- Eigene Auswahllisten (Facebook, Meta) reagieren nicht auf `click <ref>`: per `run-code` die `boundingBox()` der
  Option holen und `page.mouse.click()` auf die Mitte setzen.

## Claude in Chrome (Rückfall)

- **Extension «not connected»:** Chrome selbst starten bzw. den Tab öffnen (`google-chrome "<URL>" &`, auch
  bei laufendem Chrome) und erneut verbinden; hilft das nicht, Chrome per `kill -TERM` beenden, warten, bis
  kein Prozess mehr läuft, `google-chrome --restore-last-session &`, 25 s warten. Erst danach Goran fragen.
- **Erst wiederholen, dann melden:** Fehler aus Batch-Aufrufen («Navigation to this domain is not allowed»,
  Timeouts) einzeln mit `navigate` in einem frischen Tab wiederholen. Nur berichten, was im Tool-Ergebnis
  steht; ungeprüfte Ursachen weglassen oder als Vermutung kennzeichnen. Liefert ein Tab kaputte (weisse)
  Screenshots, einen neuen Tab nehmen.
- **Selbst einloggen:** Jede Login-Seite, auch mitten in einem OAuth-Ablauf, meldet Claude selbst an: E-Mail-
  oder Benutzerfeld anklicken, den Autofill-Vorschlag von Chromes Passwortmanager wählen, «Anmelden» klicken.
  Nie «Mit Google fortfahren» (Popup bzw. FedCM ist für die Extension unsichtbar), nie ein Passwort tippen
  oder auslesen. Autofill füllt nur im sichtbaren Vordergrund-Tab. Nur bei fehlendem Autofill, 2FA oder Captcha
  Goran melden; nie «das macht Goran» in eine Doku schreiben.
- **Bestehenden Tab nehmen:** Nach einem Login durch Goran oder dem Neuverbinden der Extension zuerst alle
  Fenster und Tabs nach der eingeloggten Seite absuchen und dort weiterarbeiten statt einen neuen Tab zu öffnen.
- **Lesen verweigert:** Lehnt die Extension das Lesen einer Seite ab, trotzdem Screenshot und Klick versuchen,
  bevor gemeldet wird.
- **Datei-Uploads:** `file_upload` auf das `input[type=file]`, je Datei ein Aufruf. Viele Formulare (etwa Codester)
  laden sofort beim Auswählen hoch, ohne weiteren Knopf. Scheitert ein Upload (Status-Platzhalter, 5xx), erst mit
  einer Datei in einem frisch geladenen Formular wiederholen, bevor eine Störung beim Anbieter gemeldet wird.

## Kennwörter

Nie als Befehlsparameter. Login als `run-code`-Datei mit Platzhalter, eine kleine Shell-Hülle setzt das Kennwort
aus `.secrets/` ein und filtert es aus der Ausgabe (`run-code` kennt weder `require` noch `process`). Vorbild:
`myfactory-anbindung/myfactory/cli_login.sh` mit `cli_login.js`.

Liegt kein Kennwort in einer Datei, keine Passwort-Datei von Goran verlangen: in Gorans Chrome per Autofill
anmelden und angehängt per CDP weiterarbeiten.

## Arbeiten mit playwright-cli

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
