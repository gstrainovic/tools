#!/usr/bin/env bash
# Tests für agent-auftrag.sh: bash hooks/test_agent_auftrag.sh
set -u
hier=$(cd "$(dirname "$0")" && pwd)
fehler=0

fall() { # name, erwartet (abgelehnt|frei), auftrag [, transkript]
  local name=$1 erwartet=$2 auftrag=$3 transkript=${4:-} aus ist=frei
  aus=$(jq -n --arg p "$auftrag" --arg t "$transkript" \
    '{hook_event_name:"PreToolUse", tool_name:"Agent", tool_input:{prompt:$p}} + (if $t == "" then {} else {transcript_path:$t} end)' |
    "$hier/agent-auftrag.sh")
  grep -q '"deny"' <<<"$aus" && ist=abgelehnt
  if [ "$ist" = "$erwartet" ]; then echo "ok   $name"; else echo "FAIL $name: erwartet $erwartet, ist $ist"; fehler=1; fi
}

# Transkripte wie Claude Code sie schreibt (JSONL): U = Nutzernachricht, danach Werkzeugaufrufe des Assistenten
tmp=$(mktemp -d)
nutzer() { jq -nc --arg t "$1" '{type:"user", message:{role:"user", content:$t}}'; }
bash_aufruf() { jq -nc --arg c "$1" '{type:"assistant", message:{content:[{type:"tool_use", name:"Bash", input:{command:$c}}]}}'; }
{ nutzer "such mir Anbieter"; bash_aufruf "rg -n anbieter ~/projects"; } >"$tmp/ohne-skript.jsonl"
{ nutzer "such mir Anbieter"; bash_aufruf "uv run ~/projects/tools/recherche.py -q 'tts deutsch' -m 8"; } >"$tmp/mit-skript.jsonl"
{ bash_aufruf "uv run ~/projects/tools/recherche.py -q 'tts deutsch'"; nutzer "und jetzt die Preise"; } >"$tmp/skript-vorher.jsonl"
{ nutzer "such mir Anbieter"; bash_aufruf "codex --search exec --skip-git-repo-check -s read-only 'Frage' -o /tmp/x.md"; } >"$tmp/mit-codex.jsonl"

VOLL="Recherche-Auftrag nach Skill recherche (/home/g/.claude/skills/recherche/SKILL.md): suche 20 Firmen. Keine Claude-in-Chrome-Werkzeuge und kein Playwright; was so nicht lesbar ist, als ‹nicht geprüft› markieren."

fall "Recherche ohne Skill wird abgelehnt" abgelehnt \
  "Recherche-Auftrag: suche 20 Firmen. Werkzeuge: curl, Jina Reader, WebSearch."
fall "Websuche ohne Skill wird abgelehnt" abgelehnt "Finde per WebSearch die Preise von drei Anbietern."
fall "Recherche mit Skill, aber ohne Chrome-Verbot wird abgelehnt" abgelehnt \
  "Recherche-Auftrag nach Skill recherche (/home/g/.claude/skills/recherche/SKILL.md): suche 20 Firmen."
fall "Recherche mit Skill und Chrome-Verbot läuft ohne Transkript" frei "$VOLL"
fall "Recherche ohne vorherige Skript-Suche wird abgelehnt" abgelehnt "$VOLL" "$tmp/ohne-skript.jsonl"
fall "Recherche nach Skript-Suche läuft" frei "$VOLL" "$tmp/mit-skript.jsonl"
fall "Recherche nach Codex-Suche läuft" frei "$VOLL" "$tmp/mit-codex.jsonl"
fall "Skript-Suche vor der letzten Nutzernachricht zählt nicht" abgelehnt "$VOLL" "$tmp/skript-vorher.jsonl"
fall "Bauauftrag, der nur die Recherche-Datei nennt, läuft" frei \
  "Baue die Testseite nach Skill recherche; Fakten in recherche/ki-telefonassistent-inbound.md, keine neue Recherche. Keine Claude-in-Chrome-Werkzeuge und kein Playwright." "$tmp/ohne-skript.jsonl"
fall "Mailtext ohne Recherche läuft" frei "Schreibe vier Mails nach diesen Belegen. Nichts senden."
fall "Videoauftrag ohne Regeln bleibt abgelehnt" abgelehnt "Schneide das Video neu."
rm -rf "$tmp"
exit $fehler
