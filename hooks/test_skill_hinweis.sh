#!/usr/bin/env bash
# Tests für skill-hinweis.sh: bash hooks/test_skill_hinweis.sh
set -u
hier=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fehler=0

skill='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"stellenboersen-api"}}]}}'
gelesen='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"/home/g/projects/find-jobs/.claude/skills/stellenboersen-api/SKILL.md"}}]}}'

# Hauptprotokoll und Subagent-Protokoll wie Claude Code sie ablegt: <sitzung>.jsonl, <sitzung>/subagents/agent-<id>.jsonl
mkdir -p "$tmp/sitzung/subagents"
fall() { # name, erwartet (hinweis|still), agent_id, zeilen Hauptprotokoll, zeilen Subagent
  local name=$1 erwartet=$2 aid=$3 haupt=$4 agent=$5
  printf '%s\n' "$haupt" >"$tmp/sitzung.jsonl"
  printf '%s\n' "$agent" >"$tmp/sitzung/subagents/agent-a1.jsonl"
  local aus ist=still
  aus=$(jq -n --arg t "$tmp/sitzung.jsonl" --arg a "$aid" \
    '{hook_event_name:"PreToolUse", tool_name:"Bash", tool_input:{command:"python3 suche/karriereseiten.py"},
      transcript_path:$t} + (if $a == "" then {} else {agent_id:$a} end)' | "$hier/skill-hinweis.sh")
  grep -q "Skill stellenboersen-api laden" <<<"$aus" && ist=hinweis
  if [ "$ist" = "$erwartet" ]; then echo "ok   $name"; else echo "FAIL $name: erwartet $erwartet, ist $ist"; fehler=1; fi
}

fall "Hauptsitzung ohne Skill mahnt" hinweis "" "" ""
fall "Hauptsitzung mit geladenem Skill schweigt" still "" "$skill" ""
fall "Subagent mit geladenem Skill schweigt" still a1 "" "$skill"
fall "Subagent mit per Read gelesener SKILL.md schweigt" still a1 "" "$gelesen"
fall "Subagent ohne Skill mahnt" hinweis a1 "" ""
fall "Skill nur in fremdem Subagenten zählt nicht für die Hauptsitzung" hinweis "" "" "$skill"
exit $fehler
