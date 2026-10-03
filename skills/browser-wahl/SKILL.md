---
name: browser-wahl
description: Welches Werkzeug für Browserarbeit (API, playwright-cli, Skript oder Claude in Chrome), Sessions, Kennwörter, erkundete Abläufe als Skill festhalten. Laden, bevor im Browser etwas erkundet, eingerichtet oder geprüft wird, besonders in Kundensystemen (ERP, CMS, Portale).
---

# Browser-Werkzeug wählen

Reihenfolge, das erste passende nehmen:

1. **API oder CLI des Systems.** Kein Browser, wenn es eine Schnittstelle gibt.
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

## Kennwörter

Nie als Befehlsparameter. Login als `run-code`-Datei mit Platzhalter, eine kleine Shell-Hülle setzt das Kennwort
aus `.secrets/` ein und filtert es aus der Ausgabe (`run-code` kennt weder `require` noch `process`). Vorbild:
`bexio-formular-connector/myfactory/cli_login.sh` mit `cli_login.js`.

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
