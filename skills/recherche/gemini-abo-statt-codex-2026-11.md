# Google AI Pro statt ChatGPT Plus (Codex)? Stand 14.11.2026

Frage (Goran): Kann ein Gemini-Abo Bilder, Recherche und Videos wie Codex, damit Codex gekündigt werden kann?
Bezug: `codex-abo-2026-11.md` (Nutzung von Codex, Gorans Entscheid 886a: ab 15.11. Plus).

## Preise Schweiz

| Abo | Preis | Quelle |
|---|---|---|
| ChatGPT Plus | CHF 20 im Monat | chatgpt.com/de-DE/pricing; aisub.yuanwu.ai (November 2026) |
| Google AI Pro | CHF 17 im Monat | gemini.google/ch/subscriptions; aisub.yuanwu.ai; PCtipp |
| Google AI Plus | CHF 5 im Monat | promptpiggy.com/de/schweiz |

## Was Google AI Pro für unsere Abläufe hergibt

| Ablauf heute mit Codex | Mit Google AI Pro | Quelle |
|---|---|---|
| Skriptaufruf `codex exec` | Antigravity CLI `agy -p` (Headless-Modus), Anmeldung über das Google-Konto, kein API-Schlüssel. Die Gemini CLI (`gemini`, hier 0.38.2 installiert) läuft seit 18.06.2026 nicht mehr mit Google AI Pro | antigravity.google/docs/cli/headless; README google-gemini/gemini-cli |
| Bilder (`ki-bild.sh`, `ki-set-bild.sh`, `lorinna-bilder.sh`) | Werkzeug `generate_image` in agy (Nano Banana Pro) | antigravity.google/blog/nano-banana-pro; github.com/wjb127/agy-image (Drittprojekt) |
| Recherche-Gegenprobe `codex --search exec` | Google-Suche in agy (Search Grounding) | Drittprojekte signalcompose/claude-tools, leonardo-ferioli/SuearchHermes; bei Google nicht nachgelesen |
| Videos (fehlt bei Codex ganz) | In der Gemini-App und in Flow (1'000 Flow-Credits im Monat zusätzlich zu 50 am Tag), Gemini Omni 1.2 Flash; nur Oberfläche, ob agy Videos erzeugt, ungeprüft | support.google.com/gemini/answer/16126339; support.google.com/flow/answer/16526234 |
| Kontingent | Keine veröffentlichten Zahlen: Erneuerung alle 5 Stunden bis zu einer Wochengrenze, bei Engpass AI-Credits kaufbar | antigravity.google/docs/plans; toolcolumn.com (10.11.2026) |

Das Abo enthält kein Guthaben für die Gemini API: Die Clips per Skript (`vesna/action-dupes/werbung/youtube/omni_clips.py`)
brauchen weiterhin die Abrechnung im Google-Cloud-Projekt.

## Weitere Abos

| Abo | Preis | Inhalt | Quelle |
|---|---|---|---|
| xAI Premium (SuperGrok) | USD 30 im Monat | Chat, Bilder, Videos (erst ab Premium), Grok-API und Build aus einem gemeinsamen Wochenkontingent ohne veröffentlichte Zahlen | x.ai/pricing; troiana.net/guides/grok |
| xAI Plus | USD 8 im Monat | Bilder, keine Videos | genativity.com/guides/grok-imagine-pricing |
| MiniMax M Plan Go | USD 264 im Jahr | Text, Bild, Sprache, Websuche, Agent MiniMax Code (CLI); Video erst in höheren Stufen laut Planseite (nicht eindeutig) | minimax.io/m-plan; platform.minimax.io/docs/m-plan/faq |

## Ungeprüft

- Gleiche Qualität wie Codex bei Produktfotos (Etikett unverändert) und bei der Recherche-Gegenprobe: nur durch
  einen Vergleich mit denselben Aufträgen zu klären.
- Wie viele Bilder und Recherchen das Pro-Kontingent trägt (Codex Pro 100 lag bei 3–8 % Wochenauslastung, 45
  Bilder in zwei Wochen).
- agy ist hier nicht installiert.

## Umstellungsaufwand

Codex-Aufrufe stehen in `vesna/action-dupes/fotos/ki-bild.sh`, `ki-set-bild.sh`, `lorinna-bilder.sh`, im Skill
`recherche` (SKILL.md, Stufe 3) und in den Hooks `befunde-eingetragen.sh` (lässt `codex exec` durch) samt Tests.
