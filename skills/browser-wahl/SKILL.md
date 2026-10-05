---
name: browser-wahl
description: Welches Werkzeug für Browserarbeit (API, playwright-cli, Skript oder Claude in Chrome), Recherche ohne Browser (WebSearch, Jina), Chrome-Extension und Login per Autofill, Sessions, Kennwörter, erkundete Abläufe als Skill festhalten. Laden, bevor im Browser etwas erkundet, eingerichtet oder geprüft wird, bevor recherchiert oder ein Recherche-Agent gestartet wird, und wenn ein Login oder die Chrome-Extension hakt.
---

# Browser-Werkzeug wählen

Reihenfolge, das erste passende nehmen:

1. **API oder CLI des Systems.** Kein Browser, wenn es eine Schnittstelle gibt. Bei jedem System, für das noch
   kein Schlüssel in `.secrets/` oder `~/.config/` liegt, zuerst in den Einstellungen nach «API», «API-Tokens»,
   «Entwickler» oder einer CLI suchen und einen Token mit den nötigen Rechten (lesen und schreiben) anlegen lassen,
   bevor irgendetwas durchgeklickt wird; Ablage in `.secrets/` bzw. `~/.config/<system>/` und sofort
   `geheimnisse hochladen` (Tresor). Token nie in den Chat oder als Befehlszeile eingeben lassen. Ablauf: Goran
   kopiert den Token und schreibt «bereit»; dann selbst `wl-paste -n > <datei> && chmod 600 <datei>` ausführen
   (Bash läuft in seiner Wayland-Sitzung), nur Länge und Zeichenart ausgeben, mit einem lesenden API-Aufruf prüfen,
   hochladen und die Zwischenablage mit `wl-copy --clear` leeren. Beim Anlegen per API die zurückgegebene ID
   festhalten (zum Ändern und Löschen).
2. **playwright-cli** (Skill `playwright-cli`) für alles Interaktive: unbekannte Masken erkunden, einrichten,
   prüfen (myfactory, bexio, REDAXO, WordPress, Portale ohne Bot-Schutz). Kein Tool-Schema im Kontext, Snapshots
   landen als Datei, `find "Text"` sucht darin. Eine benannte Session je Kunde oder System (`-s=<name>`), Login
   einmal, die Session bleibt zwischen Aufrufen offen (`playwright-cli list`).
3. **Skript** (Playwright mit `playwright-core`, `channel: 'chrome'`) nur für fertige, wiederholte Abläufe ohne
   Entscheidungen: E2E-Tests, Screenshots, Login-Vorstufe.
4. **Claude in Chrome** nur, wo Gorans eigene Sitzung mit Bot-Schutz nötig ist (LinkedIn, Upwork, freelancermap,
   Google-Konten) oder Goran zusehen will. Nicht für Kundensysteme.

Das Playwright-MCP-Plugin ist abgeschaltet (`~/.claude/settings.json`), playwright-cli deckt alles ab. Nie
`npx playwright install`: playwright-cli nutzt den installierten Chrome.

## Recherche ohne Browser

Nachschlagen (Preise, Produktvergleiche, Doku, Marktlücken) läuft über WebSearch, im Notfall über Jina
(`https://r.jina.ai/<URL>` oder MCP `jina-reader`), nie über Playwright oder Claude in Chrome, weil das Tokens
kostet und Chrome Gorans eingeloggter Sitzung vorbehalten ist. Recherche-Agenten bekommen im Auftrag wörtlich:
«Keine Claude-in-Chrome-Werkzeuge und kein Playwright; was so nicht lesbar ist, als ‹nicht geprüft›
markieren.», sonst greifen sie zu den verfügbaren Chrome-Werkzeugen.

Jina: Schlüssel in `~/.config/jina/key` (nie anzeigen), für curl
`-H "Authorization: Bearer $(tr -d '\n' < ~/.config/jina/key)"`. Mit Schlüssel geht auch `jina_search`, eine
Suche kostet rund 55'000 Tokens Guthaben. Meldet Jina HTTP 402 (`InsufficientBalanceError`), ohne Schlüssel
aufrufen (20 Abrufe pro Minute). Bot-Schutz (Cloudflare, eBay, DATEV-Community) umgeht Jina nicht.

## Claude in Chrome

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

## Kennwörter

Nie als Befehlsparameter. Login als `run-code`-Datei mit Platzhalter, eine kleine Shell-Hülle setzt das Kennwort
aus `.secrets/` ein und filtert es aus der Ausgabe (`run-code` kennt weder `require` noch `process`). Vorbild:
`bexio-formular-connector/myfactory/cli_login.sh` mit `cli_login.js`.

Liegt kein Kennwort in einer Datei, keine Passwort-Datei von Goran verlangen: in Chrome per Autofill anmelden
und die Sitzung für Playwright übernehmen (Cookies per Skript exportieren, Werte nie ausgeben, Kopien danach
löschen).

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
