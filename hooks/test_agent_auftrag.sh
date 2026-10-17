#!/usr/bin/env bash
# Tests für agent-auftrag.sh: bash hooks/test_agent_auftrag.sh
set -u
hier=$(cd "$(dirname "$0")" && pwd)
fehler=0

fall() { # name, erwartet (abgelehnt|frei), auftrag
  local name=$1 erwartet=$2 auftrag=$3 aus ist=frei
  aus=$(jq -n --arg p "$auftrag" '{hook_event_name:"PreToolUse", tool_name:"Agent", tool_input:{prompt:$p}}' |
    "$hier/agent-auftrag.sh")
  grep -q '"deny"' <<<"$aus" && ist=abgelehnt
  if [ "$ist" = "$erwartet" ]; then echo "ok   $name"; else echo "FAIL $name: erwartet $erwartet, ist $ist"; fehler=1; fi
}

fall "Recherche ohne Skill wird abgelehnt" abgelehnt \
  "Recherche-Auftrag: suche 20 Firmen. Werkzeuge: curl, Jina Reader, WebSearch."
fall "Websuche ohne Skill wird abgelehnt" abgelehnt "Finde per WebSearch die Preise von drei Anbietern."
fall "Recherche mit Skill recherche läuft" frei \
  "Recherche-Auftrag nach Skill recherche (/home/g/.claude/skills/recherche/SKILL.md): suche 20 Firmen."
fall "Mailtext ohne Recherche läuft" frei "Schreibe vier Mails nach diesen Belegen. Nichts senden."
fall "Videoauftrag ohne Regeln bleibt abgelehnt" abgelehnt "Schneide das Video neu."
exit $fehler
