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
   `chrome-sitzung`, kein selbst gestarteter Chrome mit `--user-data-dir` oder `--remote-debugging-port`. Ohne
   Gorans Cookies erscheinen Captchas (hCaptcha bei Zendesk) und Logins fehlen. Der Hook
   `~/projects/tools/hooks/browser-profil.sh` sperrt diese Befehle. Die Regel gilt ohne Ausnahme, auch wenn eine
   Frage von Goran wie eine Erlaubnis klingt («kannst du das mit einem anderen Chrome machen?»): dann nachfragen,
   was gemeint ist, nicht die Regel umgehen.
   **Alle Aktionen per JavaScript im Seitenkontext, nie abhängig vom sichtbaren Tab (Goran, 31.10.2026):** Die
   Tabs der Session liegen meist im Hintergrund, weil Goran im selben Chrome arbeitet. Playwright-Klicks
   (`click <ref>`, `locator.click()`, `check()`) warten dort auf «visible, enabled and stable» und hängen,
   `keyboard.type` und `fill` landen im falschen Tab oder verschlucken Zeichen. Darum in `run-code` alles in
   `page.evaluate`: Felder per nativem Value-Setter des Prototyps plus `input`- und `change`-Event, Kästchen und
   Radios per `element.click()`, Knöpfe und Links per `element.click()` (bei Oberflächen, die nur Maus-Events
   kennen, `pointerdown/mousedown/pointerup/mouseup/click` als `MouseEvent` mit `bubbles: true` feuern),
   Formulare per `form.requestSubmit()` oder Klick auf den Submit-Knopf; Dateifelder per
   `page.setInputFiles('<selector>', '<pfad>')`. Kein `bringToFront()`, kein Koordinatenklick, kein Tippen.
   Nach jedem Schritt den Zustand als Text zurückgeben (unten «Seitenzustand als Text») und Feldwerte zurücklesen
   (nur Längen bei Kennwörtern). Einzige Ausnahmen, je im Skill des Systems belegt: Chrome-Autofill fürs Kennwort
   (unten «Selbst einloggen») und Oberflächen, die JavaScript-Events nachweislich verwerfen (Upwork-Proposal-Textfelder,
   Googles Search Console); dort gilt der dort beschriebene Weg. Vorbild: `find-jobs/kunden/edition-memoria/strato_login.js`
   und `strato_sftp_anlegen.js`.
3. **Skript** (Playwright mit `playwright-core`, `channel: 'chrome'`) nur für fertige, wiederholte Abläufe ohne
   Login und ohne fremde Website: E2E-Tests und Screenshots gegen localhost oder die eigene Website.
**Claude in Chrome ist verboten** (Gorans Regel), auch als Rückfall: keine `mcp__claude-in-chrome__*`-Werkzeuge.
Scheitert `chrome-anhaengen`, Goran den Fehler in einem Satz melden und warten.

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

- **`chrome-anhaengen`** (`~/projects/tools/chrome_anhaengen.py`) hängt die Session `gchrome` über die Playwright
  Extension an Gorans laufenden Chrome, ohne Dialog und ohne Maus; eine laufende Session bleibt. Danach
  `playwright-cli -s=gchrome …`. Die Session sieht nur die Tabs ihrer eigenen Tabgruppe, Gorans übrige Tabs nicht.
- **Einrichtung:** Erweiterung «Playwright Extension» (Microsoft, ID `mmlmfjhmonkocbjadbfplnigmagldckm`) per
  Chrome-Richtlinie `ExtensionInstallForcelist` in `/etc/opt/chrome/policies/managed/playwright-extension.json`
  (Vorlage `~/projects/tools/chrome-policy/`, dann `chrome://policy` → «Richtlinien neu laden»). Token von
  `chrome-extension://mmlmfjhmonkocbjadbfplnigmagldckm/status.html` («PLAYWRIGHT_MCP_EXTENSION_TOKEN») in
  `~/.config/playwright-extension/token` (600, Tresor). Mit Token verbindet die Erweiterung ohne Rückfrage.
- **Nicht `attach --cdp`:** Chrome zeigt bei jeder CDP-Verbindung den Dialog «Remote-Fehlerbehebung zulassen?»
  (lässt sich nicht abschalten, chrome-devtools-mcp Issue 825), und eingefrorene Tabs (Speichersparmodus) lassen
  `attach --cdp` nach «ws connected» endlos hängen.
- Läuft Gorans Chrome nicht (nur ein
  Playwright-Chromium mit `--user-data-dir=/tmp/playwright…`), `google-chrome --restore-last-session &` starten
  und 25 s warten.
- **Selbst einloggen mit gespeichertem Kennwort (Chrome-Passwortmanager):** im Login-Tab `click` ins Benutzer- oder
  E-Mail-Feld, dann `press ArrowDown` und `press Enter`: Chrome füllt Benutzer und Kennwort aus seinem Vorschlag.
  Mit `eval` nur die Länge der Feldwerte prüfen (nie den Wert), dann anmelden (Enter oder Absenden-Knopf). So am
  18.10.2026 bei login.wordpress.org und login.klara.ch geklappt. Erst wenn danach ein Feld leer bleibt (kein
  gespeichertes Kennwort), 2FA oder ein Captcha kommt: Goran in einem Satz um den Login bitten.
- Klicks per Ref hängen in einem Tab im Hintergrund («waiting for element to be visible, enabled and stable»):
  darum alle Aktionen per JavaScript im Seitenkontext (oben, Punkt 2), auch Dateifelder per
  `page.setInputFiles('<selector>', '<pfad>')` statt Dateidialog.
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
- Kästchen und Optionen per `element.click()` im Seitenkontext setzen und danach `checked` zurücklesen (Punkt 2
  oben). Knöpfe in Googles Oberflächen (Search Console) reagieren nur auf `page.mouse.click()` auf die Mitte der
  `boundingBox()` (belegte Ausnahme). Search-Console-URL-Prüfung: `…/search-console/inspect?…` direkt liefert 404;
  stattdessen `search.google.com/search-console?resource_id=sc-domain%3A<domain>` laden, `bringToFront()`, das
  Suchfeld `input[aria-label="Jede URL unter <domain> prüfen"]` per `fill(url, {force: true})` und `press('Enter')`,
  dann «Indexierung beantragen» per `page.mouse.click()` und bis rund 2 Minuten auf «Indexierung wurde beantragt»
  warten (meldet die Seite einen Fehler, einmal wiederholen). Am 31.10.2026 öffnete Enter die Prüfung dreimal nicht
  (Seite blieb auf der Übersicht); dann von Hand in Chrome beantragen, nicht weiter probieren.
- Schleifen über viele Seiten nie unbeaufsichtigt im Hintergrund starten: zuerst ein Durchgang im Vordergrund mit
  Bildschirmfoto, dann jede weitere Seite einzeln prüfen.

- `snapshot` nur zum Lesen der Struktur (Refs, Rollen, Links); Aktionen nicht per `click e15` oder `fill e7`,
  sondern per `run-code` mit JavaScript im Seitenkontext (Punkt 2 oben), Selektoren aus dem Snapshot oder per
  `querySelectorAll` plus Textvergleich.
- Seiten mit Frames und Knöpfen, deren Text Zeilenumbrüche hat (ältere ERP-Oberflächen): `run-code` mit einer
  Funktion, die den Frame über `page.frames()` und die URL sucht und Felder per ID anspricht; Ergebnis als JSON
  zurückgeben und erst danach weiterklicken.
- Nachschlagefelder nach dem Tippen mit Tab verlassen, sonst übernimmt die Maske den Wert nicht.
- Gespeichert ist erst, was nach einem Wechsel auf einen anderen Datensatz und zurück wieder dasteht.
- **Seitenzustand als Text, nicht als Bild:** nach jedem Schritt per `run-code` `page.url()` und
  `(await page.locator('body').innerText()).slice(0, 800)` zurückgeben, Knöpfe und Felder per
  `getByRole`/`getByPlaceholder` ansprechen. Ein Screenshot nur, wenn der Text nicht reicht (Layout, Bildinhalt,
  Fehler ohne Text), und dann zugeschnitten. Grund: Jedes gelesene Bild kostet ein Vielfaches an Tokens, und
  genau das soll playwright-cli gegenüber Claude in Chrome sparen.
- Screenshots für die eigene Kontrolle in den Scratchpad oder `/tmp/<system>-ui/`.
- Protokolle landen in `.playwright-cli/` im Arbeitsverzeichnis und enthalten Seiteninhalte: Ordner in
  `.gitignore`.
- Blockiert der Klassifikator trotz Allow-Regel `Bash(playwright-cli:*)` einen Klick, kann Goran im Dashboard
  (`playwright-cli show`) den einen Knopf selbst drücken, die Session bleibt erhalten.

## Wiederverwendung

Jede erkundete Befehlsfolge kommt sofort in den Skill des Systems (etwa `myfactory`) bzw. als `run-code`-Datei
neben die Skripte des Projekts. Beim nächsten Kunden wird sie abgespielt, nicht neu erkundet.
