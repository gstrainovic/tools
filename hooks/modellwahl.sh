#!/usr/bin/env bash
# PreToolUse-Hook für Agent und Workflow: legt Claude vor jedem Agentenstart die Modellwahl aus dem Skill
# arbeitsweise vor, damit sie nicht davon abhängt, ob der Skill geladen wurde. Blockiert nie.
modell=$(jq -r '.tool_input.model // empty' 2>/dev/null)
if [ -n "$modell" ]; then
  gewaehlt="Gewählt: model=$modell."
else
  gewaehlt="Kein model gesetzt: der Agent erbt das Hauptmodell (teuerste Stufe)."
fi
text="Modellwahl (Skill arbeitsweise) vor diesem Agentenstart prüfen. $gewaehlt
1. Skript statt Modell, wenn es ohne Sprachmodell geht.
2. Haiku, Denkstufe low: mechanisch nach Vorgabe, Lesen mit festem Rückgabeformat.
3. Sonnet, Denkstufe medium: Lesen und Vorsortieren nach Kriterien, Übersetzungen, Tests nach fertigem Plan.
4. Opus, Denkstufe high: Code-Änderungen mit TDD, Fehleranalyse, Umsetzungspläne, Prüfung fremden Codes.
5. Hauptmodell: Entscheide, Preise, Freigaben, Deutung von Rückmeldungen.
Bewerbungs- und Kundentexte (Mail, Anschreiben, Freitext für Formulare): immer Fable (model=fable), auch wenn das Hauptmodell Opus ist; Formular ausfüllen und Senden nach fertigem Text: Sonnet oder Haiku.
Passt das gewählte Modell nicht: den eben gestarteten Agenten stoppen und mit passendem model neu starten."
jq -n --arg t "$text" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $t}}'
