# Codex-Abo: Nutzung und Bedarf (Stand 08.11.2026)

Frage: Lohnt sich ChatGPT Pro 100 (100 USD im Monat) für Codex, oder reicht Plus (20 USD)?

## Wofür Codex hier läuft

- **Recherche-Gegenprobe:** `codex --search exec` im Hintergrund (Skill `recherche`, Stufe 3), kostet keine
  Claude-Tokens und findet kleine Anbieter aus Verzeichnissen, die ddgs und Exa nicht liefern (Beleg:
  `vergleich-2026-10.md`, virtuelle Mobilnummer nur von Codex gefunden).
- **Bilder:** Produktfotos für pink-deko.ch (`vesna/action-dupes/fotos/ki-bild.sh`, `ki-set-bild.sh`) und
  Bilder für Berichte (`codex exec … -i`).
- **Chrome-Aufgaben in Codex:** nur GPT-6 Astra (find-jobs/AGENTS.md), seit Mitte Oktober in den Protokollen
  nicht genutzt.

## Messung aus `~/.codex/sessions`

- 13.–14.10.: Go-Abo (Monatsgrenze) in einer Nacht bei 95 %, danach Plus in rund 1 Stunde bei 100 % der
  5-Stunden-Grenze (grosser Lauf Partnersuche, `akquise/partnersuche/codex-liste.md`). Danach Wechsel auf
  Pro 100 (`plan_type: prolite`).
- Seit 15.10. höchste Wochenauslastung von Pro 100: 8 % (Woche bis 22.10.), sonst 1–5 %.
- Sitzungen: Oktober 430, November bis 06.11. 71; fast alle `codex exec` mit GPT-6.1 Sol (323), 6 mit Luna.
- Bilder seit 15.10.: 75, seit 25.10.: 45.
- Die 100 USD API-Guthaben von Pro 100 nutzt kein Projekt (kein `OPENAI_API_KEY` im Code ausser Beispielen).

## Grenzen laut OpenAI

- Plus: GPT-6.1 Sol 15–160 lokale Nachrichten je 5 Stunden, dazu Wochengrenze; Bilder verbrauchen das
  Kontingent 3–5-mal schneller; bei Erreichen Credits nachkaufbar (developers.openai.com/codex/pricing).
- Pro: keine 5-Stunden-Grenze; Pro 100 hat seit kurzem das doppelte Codex-Kontingent, Plus unverändert
  (help.openai.com/en/articles/9793128).
- Verhältnis Plus zu Pro 100 nennt OpenAI nicht in Zahlen (ungeprüft, nur geschätzt).

## Gorans Entscheid 886a

Plus statt Pro 100, bei Engpass Credits nachkaufen. Pro 100 ist gekündigt und endet am 14.11.2026, Plus wird
dann abgeschlossen (Frist in `find-jobs/TODO.md`).

## Einschätzung

Bei 3–5 % Wochenauslastung von Pro 100 nutzt der heutige Betrieb das Abo zu rund einem Zwanzigstel. Plus reicht
für den Alltag wahrscheinlich, Risiko sind die 5-Stunden-Grenze bei Bilderserien oder grossen Recherchelisten
(wie am 14.10.); dafür lassen sich Credits nachkaufen oder Läufe verteilen.
