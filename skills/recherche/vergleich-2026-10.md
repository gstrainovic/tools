# Recherche-Werkzeuge: Kosten und Trefferqualität

Grundlage der Regel «Zuerst per Skript» in `SKILL.md`. Stand Oktober 2026.

## Vergleichstest

Dieselbe Frage für alle: Welche Anbieter von Spray-Tanning gibt es im Umkreis von etwa 25 km um 9323 Steinach SG,
und was kostet eine Ganzkörperbehandlung? Gezählt sind nur Preise, die auf der Anbieterseite selbst stehen.

| Werkzeug | Claude-Tokens | Geld | Belegte Preise in der Region | Eigene Funde |
|---|---|---|---|---|
| Exa (3 Anfragen, `type: auto`, Highlights) plus curl-Skript, das PLZ und Preis aus den Seiten zieht | rund 5000 (nur die Auszüge) | 0,021 USD aus dem Gratisguthaben | 4: Jasmin Beauty St. Gallen 45, SA Cosmetics Rorschacherberg 55, Make-up-Art Rorschacherberg 50 (gleiche Adresse), Pearlbody Herisau 49 | Sun-Star Arbon (ohne Preis) |
| ddgs (DuckDuckGo und andere, gratis, ohne Schlüssel) plus dasselbe Skript | rund 3000 | 0 | 2 (Jasmin Beauty, SA Cosmetics) | Alpstein Drogerie St. Gallen, House of Harmony Altstätten, Salonkee-Listen |
| Codex mit Websuche (`codex --search exec`) | 0 (läuft über Gorans ChatGPT-Abo «Pro Lite», 101'205 Codex-Tokens) | 0 zusätzlich | 1 (Jasmin Beauty) | kleine Anbieter aus Verzeichnissen: Honey Beauty und Haarmonie Gossau, Coiffeur&Kosmetik Romanshorn, SunLess Diepoldsau |
| Sonnet-Agent mit WebSearch und Jina Reader | 81'635 | 0 zusätzlich | 1 (Jasmin Beauty) | A-Cosmetics St. Gallen, Alpstein Drogerie, Haarmonie Gossau |
| wigolo (lokal, `npx wigolo search`) | rund 3000 | 0 | 1 (Make-up-Art) | A-Cosmetics; viel Rauschen (Coiffeur-Preislisten, Sky-Forum) |

Ergebnis: Suche per Skript (Exa und ddgs) und eine Auswertung per Skript, die nur Ort und Preis zurückgibt,
liefert die meisten belegten Preise für einen Bruchteil der Tokens. Der Sonnet-Agent kostet am meisten und belegt
am wenigsten, weil er jede Seite ganz liest. Codex kostet keine Claude-Tokens und findet kleine Anbieter über
Verzeichnisse (local.ch, search.ch, truvuna), die die Such-APIs nicht liefern; seine Preise sind selten belegt.

## Geprüfte Such-APIs ohne Test

Preise laut Anbieterseite, gelesen am 17.10.2026 über Jina Reader. Alle brauchen ein Konto; keines ist angelegt.

| Dienst | Gratis | Preis je 1000 Anfragen | Quelle |
|---|---|---|---|
| Exa | 10 USD Guthaben pro Monat | 7 USD (auto), 4 USD (instant) | https://exa.ai/pricing |
| Brave Search API | 5 USD Guthaben pro Monat | 5 USD | https://api-dashboard.search.brave.com/documentation/pricing |
| Parallel Search | 5000 Anfragen pro Monat | 1 bis 5 USD | https://parallel.ai/pricing |
| Tavily | 1000 Credits pro Monat, ohne Kreditkarte | 8 USD | https://tavily.com/pricing |
| Serper.dev (Google-Treffer) | 2500 Anfragen einmalig, ohne Kreditkarte | 0,30 bis 1 USD | https://serper.dev |
| Firecrawl Search | 1000 Credits pro Monat | rund 7,60 USD | https://firecrawl.dev/pricing |
| Perplexity Search API | nicht genannt | 5 USD, Fast 1 USD | https://docs.perplexity.ai/docs/getting-started/pricing |
| Linkup | 20 USD pro Monat, nur mit Firmenmail | 5 USD, Antwort mit Quellen 6 USD | https://docs.linkup.so/pages/documentation/development/pricing |
| SerpApi | 250 pro Monat | 25 USD | https://serpapi.com/pricing |
| Gemini API mit Google-Suche | in der Gratisstufe nicht verfügbar | 14 USD | https://ai.google.dev/gemini-api/docs/pricing |

Entfallen: Bing Web Search API (eingestellt 2025), Google Custom Search JSON API (keine Neukunden, endet 1.1.2027).

## GitHub (Suche per `gh search repos`, nach Sternen)

- **ddgs** (deedy5/ddgs, rund 3000 Sterne, gewartet): Metasuche als Python-Paket und CLI ohne Schlüssel, im Test
  brauchbar. Inoffiziell, kann blockiert werden.
- **wigolo** (KnockOutEZ/wigolo, rund 5500 Sterne): lokale Suche, Abruf und Crawl für Agenten ohne Schlüssel,
  rund 1,5 GB Download. Im Test ähnliche Treffer wie ddgs mit mehr Rauschen; Lizenz auf GitHub nicht erkannt.
- **SearXNG** (rund 38'000 Sterne): selbst gehostete Metasuche, gratis; lohnt erst, wenn ddgs blockiert wird.
- **local-deep-research**, **gpt-researcher**, **open_deep_research**: Recherche-Agenten mit lokalem Modell; brauchen
  ein Modell ab etwa 20 Milliarden Parametern, der Laptop hat eine Quadro P1000 mit 4 GB.
- **hyperresearch**: Deep-Research-Skill für Claude Code und Codex mit 100 bis 250 Quellen je Lauf, das Gegenteil
  von sparsam.

## Wie Exa funktioniert

Exa betreibt einen eigenen Suchindex: Es crawlt und zerlegt laut eigenem Blog «tens of billions of webpages» und
frischt sie laufend auf, berechnet dazu mit einem selbst trainierten Embedding-Modell Vektoren und sucht in einer
eigenen Vektordatenbank nach Bedeutung statt nur nach Stichworten
([Exa 2.0](https://exa.ai/blog/exa-api-2-0)). Der Modus `auto` mischt semantische und Stichwortsuche, `deep`
fährt mehrere Suchrunden mit Zusammenfassung ([Doku](https://exa.ai/docs/reference/how-exa-search-works)). Die
Highlights sind die zur Frage passenden Sätze aus dem gespeicherten Seitentext; deshalb liefert Exa Preise oft
schon ohne eigenen Seitenabruf.
