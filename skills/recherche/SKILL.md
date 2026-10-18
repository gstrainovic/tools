---
name: recherche
description: Webrecherche günstig und belegt - Suche per Skript (ddgs, Exa) mit Auswertung per Skript, Codex mit Websuche als Gegenprobe, Jina Reader für Einzelseiten, wann ein Recherche-Agent (Sonnet) und mit welchem Auftrag, «Gibt es X irgendwo?», ganze Websites und Listen durchsuchen. Laden, bevor recherchiert, nachgeschlagen (Anbieter, Preise, Konkurrenz, Vorschriften, Doku), WebSearch oder WebFetch benutzt oder ein Recherche-Agent gestartet wird.
---

# Recherche

Vorher lokal suchen (`rg` über `~/projects`), Skill `arbeitsweise`, «Erst lokal, dann Web»; der Hook `erst-lokal.sh`
erzwingt das. Formulare und alles, was erst im Browser entsteht oder ein Login braucht: Skill `browser-wahl`.

## Zuerst per Skript, nicht per Agent

Nachschlagen (Anbieter, Preise, Produktvergleiche, Marktlücken) sucht per Skript und liest nur dessen Auszüge, nie
ganze Seiten im Modell:

1. **`~/projects/tools/recherche.py`** sucht mit 2 bis 3 Formulierungen in **ddgs** (gratis, ohne Schlüssel) und
   **Exa** (`type: auto`, rund 0,007 USD je Anfrage; 10 USD Gratisguthaben pro Monat plus aufgeladenes Guthaben,
   Gorans Entscheid: lieber Exa-Dollar als Claude-Tokens, also bei Bedarf `deep` nehmen und nicht sparen), holt die
   Trefferseiten per curl und gibt je Seite nur Titel, PLZ mit Ort, Preise und Stichwortstellen (50 Zeichen Umfeld)
   als Tabelle aus: `recherche.py -q "…" -q "…" --muster "regex" -m 8` (`--json` für Rohdaten, `--ohne-exa`).
   Ausgabe in eine Datei im Scratchpad schreiben und mit `rg`/`awk` nur die Zeilen mit Preisen lesen.
2. **Exa-Stufe `deep`** (12 USD je 1000 Anfragen, `deep-reasoning` 15, `instant` 4, `fast`/`auto` 7; Doku
   https://docs.exa.ai/reference/search) für Fragen, die `auto`, ddgs und Codex nicht beantworten: Sie liest den
   Inhalt der Seiten und findet Einträge, die nur im Seitentext stehen (Moneyhouse-Löschungen, Inserattexte,
   Anbieter ohne Stichwort im Titel). Mit `"contents":{"text":{"maxCharacters":1500}}` liefert sie gleich den
   Seitentext, auch bei Seiten, die Jina und curl nicht lesen (immobilier.ch, lozart.ch). `deep-reasoning` brachte
   im Test dieselben Seiten wie `deep` für mehr Geld; `deep-lite` steht in der Doku, nicht in der Preistabelle.
   **Exa `/contents`** (1 USD je 1000 Seiten) holt den Text bekannter URLs, die Jina nicht lesen kann
   (ricardo, kleinanzeigen, moneyhouse); tutti und laendleanzeiger kann auch Exa nicht.
3. **Codex mit Websuche** parallel im Hintergrund: läuft über Gorans ChatGPT-Abo, kostet keine Claude-Tokens und
   findet kleine Anbieter über Verzeichnisse (local.ch, search.ch), die ddgs und Exa nicht liefern. Im Auftrag
   «Nur lesen, nichts in Dateien eintragen, keine TODO-Einträge, keine Commits» schreiben. Der Stop-Hook
   `befunde-eingetragen.sh` lässt `codex exec` durch, die Antwort steht also in der `-o`-Datei. Enthält sie
   nur eine Meta-Antwort, steht die eigentliche im stdout-Log im `codex`-Block vor `hook: Stop Blocked`.

Grund: Im Vergleichstest (`vergleich-2026-10.md` neben dieser Datei, dort auch geprüfte Such-APIs und
GitHub-Werkzeuge) belegten Exa und ddgs mit Skript vier Preise für rund 8000 Tokens, ein Sonnet-Agent mit WebSearch
und Jina einen Preis für 81'000 Tokens.

Befehle:
- Exa: `curl -s https://api.exa.ai/search -H "x-api-key: $(cat ~/.config/exa/key)" -H "Content-Type: application/json"
  -d '{"query":"…","type":"deep","numResults":10,"userLocation":"CH","contents":{"highlights":{"numSentences":3}}}'`;
  die Antwort nennt die Kosten in `costDollars`. Inhalte: `https://api.exa.ai/contents` mit
  `{"urls":["…"],"text":{"maxCharacters":4000}}`.
- Codex: `codex --search exec --skip-git-repo-check -s read-only "<Frage, Quelle je Aussage, Ungeprüftes
  markieren>" -o <scratchpad>/codex.md`.

## Einzelseiten und Agenten

Einzelne Seiten, die curl blockt oder die per JavaScript entstehen, über Jina Reader
(`curl https://r.jina.ai/<URL>`), nie über Playwright oder Claude in Chrome, weil das Tokens kostet und Chrome
Gorans eingeloggter Sitzung vorbehalten ist. Jina läuft ohne Schlüssel und kostenlos, 20 Abrufe pro Minute je IP;
kein Guthaben kaufen. Die Jina-Suche (`s.jina.ai`) braucht einen Schlüssel und entfällt. Bot-Schutz (Cloudflare,
eBay, DATEV-Community) umgeht Jina nicht, und playwright-cli bleibt in der Cloudflare-Prüfung («Nur einen
Moment…») hängen: Zeigt Jina diese Seite, gleich Claude in Chrome nehmen (Gorans Profil besteht die Prüfung, etwa
bei codecanyon.net und codester.com), nur zum Lesen.

Ein Recherche-Agent (Sonnet mit WebSearch und Jina) nur, wo Seiten wirklich gelesen und beurteilt werden müssen
(Vorschriften, Doku, Bewertungen); er bekommt die Funde aus «Zuerst per Skript» mit. Recherche-Agenten laufen als
Sonnet (Lesen und Vorsortieren) oder Haiku (reines Sammeln in festem Format), nie im Hauptmodell; Stufen im Skill
`arbeitsweise`, Abschnitt «Modellwahl beim Delegieren». Sie bekommen im Auftrag wörtlich:
«Keine Claude-in-Chrome-Werkzeuge und kein Playwright; was so nicht lesbar ist, als ‹nicht geprüft›
markieren.», sonst greifen sie zu den verfügbaren Chrome-Werkzeugen.

## «Gibt es X irgendwo?»

Bei Anbietern, Angeboten oder Produkten, die es vielleicht nicht gibt: nie aus einer Quelle allein «gibt es nicht»
schliessen, immer ddgs, Exa (mehrere Formulierungen und Sprachen) und Codex. Funde der Hauptaussage selbst an der
Anbieterseite prüfen (curl, Jina), bevor sie gemeldet werden. Grund: Bei der Suche nach einer virtuellen Schweizer
Mobilnummer mit Sprache fanden WebSearch und Exa nichts, Codex das Angebot.

## Ganze Websites und Listen

- **Ganze Website:** zuerst `/llms-full.txt` bzw. `/llms.txt`, sonst `/sitemap.xml` holen und die URLs per `rg`
  filtern; nur echte URLs lesen, keine Unterseiten raten (geratene Pfade liefern meist 404). Preise und AGB oft als
  PDF.
- **Listen** (Zielfirmen, Impressen, Referenzseiten) laufen nie über Jina, sondern über Skripte mit curl
  (`find-jobs/akquise/firmensuche.py` und Einzelskripte); Jina nur für die einzelne Seite, die curl blockt oder per
  JavaScript entsteht. Sind es viele solche Seiten, ein Playwright-Skript mit dem lokalen Chrome (Skill
  `browser-wahl`, Stufe 3), das rendert JavaScript gratis.
- **GitHub** per `gh` (`gh search repos "<Begriff>" --sort stars`, `gh api repos/<o>/<r>/readme`), nicht per Jina.
