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
| Bilder (Skripte für Produktfotos in einem privaten Repo) | Werkzeug `generate_image` in agy (Nano Banana Pro) | antigravity.google/blog/nano-banana-pro; github.com/wjb127/agy-image (Drittprojekt) |
| Recherche-Gegenprobe `codex --search exec` | Google-Suche in agy (Search Grounding) | Drittprojekte signalcompose/claude-tools, leonardo-ferioli/SuearchHermes; bei Google nicht nachgelesen |
| Videos (fehlt bei Codex ganz) | In der Gemini-App und in Flow (1'000 Flow-Credits im Monat zusätzlich zu 50 am Tag), Gemini Omni 1.2 Flash; nur Oberfläche. agy hat kein Videowerkzeug: Die Doku nennt als eingebautes Bildmodell nur Nano Banana 2 für das Bildwerkzeug, Videos gehen nur über einen MCP-Server mit kostenpflichtigem Gemini-API-Schlüssel oder Drittanbieter; im Forum steht eine offene Anfrage nach Veo im Abo | antigravity.google/docs/models; discuss.ai.google.dev (Feature Request «Native Imagen & Veo Tool Integration»); aifeatures.ai/does/google-antigravity-have-video-generation |
| Kontingent | Keine veröffentlichten Zahlen: Erneuerung alle 5 Stunden bis zu einer Wochengrenze, bei Engpass AI-Credits kaufbar | antigravity.google/docs/plans; toolcolumn.com (10.11.2026) |

Das Abo enthält USD 10 im Monat Guthaben für die Gemini API (je Gutschrift 12 Monate gültig, nur für den
Hauptabonnenten), einzulösen in Google AI Studio. Es wird nur verbraucht, solange auf dem Abrechnungskonto eigenes
Vorauszahlungsguthaben über 0 liegt: mindestens USD 5 einzahlen, die liegen bleiben (verfällt nach 12 Monaten, nicht
erstattbar). Bei Gemini Omni 1.2 Flash (rund USD 1.04 je 15-s-Clip) reichen USD 10 für etwa neun Clips im Monat per
Skript. Quellen: aistudio.google.com/learn/claim-google-ai-plan-credits-in-ai-studio; blog.google (13.11.2026,
«Claim your Google Cloud Credits in Google AI Studio»); yuphora.com/news/google-ai-studio-cloud-credits-ai-pro-ultra.
Ein Forumsbeitrag nennt im Kaufdialog eine Mindestvorauszahlung von EUR 30 statt USD 5
(discuss.ai.google.dev/t/…/189625); für die Schweiz ungeprüft. Ältere Forenberichte: Gutschrift im Projekt mit
Vorauszahlung nicht nutzbar, nur über Vertex AI (discuss.ai.google.dev/t/…/170841, vor der Änderung vom 13.11.).

## Abo oder Einzelabrechnung, mit Videos (Frage 1007)

| Weg | Monatlich | Einmalig | Recherche, Bilder | Video per Skript |
|---|---|---|---|---|
| ChatGPT Plus und Gemini API | CHF 20 | USD 5 (oder EUR 30) Vorauszahlung, rund USD 1 je Clip | Codex wie bisher | ja, Omni |
| ChatGPT Plus und MiniMax API | CHF 20 | USD 25 Mindestaufladung (Drittquelle agento.host), USD 0.08 je s | Codex wie bisher | ja, H3 |
| Google AI Pro allein | CHF 17 | USD 5 Einlage | agy statt Codex, Skripte umbauen, Qualität ungeprüft | ja, etwa neun Omni-Clips im Monat inbegriffen |
| beide Abos | CHF 37 | USD 5 | Codex | ja |

Omni veränderte im Fremdtest von Voyager die Form eines Produkts; die Etikett-Treue für unsere Flakons ist erst mit
einem Probeclip geklärt. Das Abrechnungskonto unter g.strainovic@gmail.com ist geschlossen (Frage 1006); ob der neue
Ablauf in AI Studio ein neues Konto anlegt, ungeprüft.

## Weitere Abos

| Abo | Preis | Inhalt | Quelle |
|---|---|---|---|
| xAI Premium (SuperGrok) | USD 30 im Monat | Chat, Bilder, Videos (erst ab Premium), Grok-API und Build aus einem gemeinsamen Wochenkontingent ohne veröffentlichte Zahlen | x.ai/pricing; troiana.net/guides/grok |
| xAI Plus | USD 8 im Monat | Bilder, keine Videos | genativity.com/guides/grok-imagine-pricing |
| MiniMax M Plan Go | USD 22 im Monat (USD 220 bei Jahreszahlung) | Text, Bilder (H3 Image), Sprache, Websuche, Agent MiniMax Code samt TUI, API-Schlüssel für Agenten; **kein Video** | minimax.io/m-plan; platform.minimax.io/docs/m-plan/faq («Explore and Build also support the H3 video model») |
| MiniMax M Plan Explore | USD 55 im Monat (USD 550 im Jahr) | wie Go mit dreifachem Kontingent und Video H3; Bild- und Videokontingent mit 5-Stunden- und Wochenfenster | ebenso |
| MiniMax ohne Abo | je Aufruf vom Guthaben (Standard-API-Schlüssel), H3-Video USD 0.08 je s bei 768p | Abo-Schlüssel und Standard-Schlüssel sind getrennt und nicht austauschbar | platform.minimax.io/docs/m-plan/faq; wireflow.ai/blog/hailuo-pricing |

## Ungeprüft

- Gleiche Qualität wie Codex bei Produktfotos (Etikett unverändert) und bei der Recherche-Gegenprobe: nur durch
  einen Vergleich mit denselben Aufträgen zu klären.
- Wie viele Bilder und Recherchen das Pro-Kontingent trägt (Codex Pro 100 lag bei 3–8 % Wochenauslastung, 45
  Bilder in zwei Wochen).
- agy ist hier nicht installiert.

## Umstellungsaufwand

Codex-Aufrufe stehen in drei Bildskripten eines privaten Repos, im Skill
`recherche` (SKILL.md, Stufe 3) und in den Hooks `befunde-eingetragen.sh` (lässt `codex exec` durch) samt Tests.
