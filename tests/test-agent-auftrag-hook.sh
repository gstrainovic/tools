#!/usr/bin/env bash
# Prüft hooks/agent-auftrag.sh: Ein Agenten-Auftrag zu Video oder Film ohne die Regeln aus dem Skill produktvideos
# wird abgelehnt (permissionDecision deny mit Grund); mit den Regeln oder ohne Videobezug läuft er durch.
set -euo pipefail
cd "$(dirname "$0")/.."
hook=hooks/agent-auftrag.sh
fehler=0
ein() { jq -n --arg p "$1" '{hook_event_name:"PreToolUse",tool_name:"Agent",tool_input:{prompt:$p}}'; }
entscheid() {
  local aus; aus=$(ein "$1" | "$hook")
  if [ -z "$aus" ]; then echo keine; else jq -r '.hookSpecificOutput.permissionDecision // "keine"' <<<"$aus"; fi
}
pruefe() { if [ "$(entscheid "$2")" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1"; fehler=1; fi; }

pruefe "Video ohne Regeln wird abgelehnt" "Nimm den Tutorial-Film auf, Sprechertext als Untertitel." deny
pruefe "Rendern ohne Regeln wird abgelehnt" "Video rendern und schneiden, ohne Ton." deny
pruefe "mit Regeln läuft durch" "Film aufnehmen. Regeln aus Skill produktvideos: Untertitel als VTT-Spur, nie eingebrannt." keine
pruefe "ohne Videobezug läuft durch" "Korrigiere die fr_FR.po aller Plugins." keine
grund=$(ein "Werbefilm neu montieren" | "$hook" | jq -r '.hookSpecificOutput.permissionDecisionReason // ""')
if grep -q "nie eingebrannt" <<<"$grund" && grep -q "produktvideos" <<<"$grund"; then echo "ok   Grund nennt Regel und Skill"; else echo "FAIL Grund nennt Regel und Skill"; fehler=1; fi
aus=$(ein "Korrigiere Texte" | "$hook")
if [ -z "$aus" ] || jq -e . >/dev/null <<<"$aus"; then echo "ok   gültige Ausgabe"; else echo "FAIL gültige Ausgabe"; fehler=1; fi

exit $fehler
