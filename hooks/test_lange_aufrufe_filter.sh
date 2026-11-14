#!/usr/bin/env bash
# Tests für lange-aufrufe-filter.sh: bash hooks/test_lange_aufrufe_filter.sh
set -u
hier=$(cd "$(dirname "$0")" && pwd)
fehler=0

fall() { # name, erwartet (sperre|frei), befehl
  local name=$1 erwartet=$2 befehl=$3 aus ist=frei
  aus=$(jq -n --arg c "$befehl" '{hook_event_name:"PreToolUse", tool_name:"Bash", tool_input:{command:$c}}' |
    "$hier/lange-aufrufe-filter.sh")
  grep -q '"permissionDecision": *"deny"' <<<"$aus" && ist=sperre
  if [ "$ist" = "$erwartet" ]; then echo "ok   $name"; else echo "FAIL $name: erwartet $erwartet, ist $ist"; fehler=1; fi
}

fall "uv run in grep sperrt" sperre "cd /tmp && uv run --with x python probe.py 2>&1 | grep -E 'OK|FEHLER'"
fall "python in tail sperrt" sperre "python3 skript.py 2>&1 | tail -5"
fall "uv run in head sperrt" sperre "uv run --quiet --with google-genai python omni.py preis | head -20"
fall "curl in grep sperrt" sperre "curl -s https://api.example.com/x | grep -o id"
fall "codex in tail sperrt" sperre "codex exec 'frage' | tail -3"
fall "playwright run-code in head sperrt" sperre "playwright-cli -s=gchrome run-code --filename a.js 2>&1 | head -3"
fall "ads in grep sperrt" sperre "~/projects/tools/ads.py query 'SELECT x' | grep campaign"
fall "Ausgabe in Datei ist frei" frei "uv run python probe.py > /tmp/aus.txt 2>&1; tail -5 /tmp/aus.txt"
fall "Datei lesen und filtern ist frei" frei "cat /tmp/aus.txt | grep FEHLER"
fall "git log in head ist frei" frei "git log --oneline | head -5"
fall "ls in head ist frei" frei "ls -la | head"
fall "ps in grep ist frei" frei "ps aux | grep python"
fall "Ausgabe ohne Filter ist frei" frei "timeout 300 uv run python -u probe.py"
fall "grep im Commit-Text ist frei" frei "git commit -m \"uv run x | grep y\""

exit $fehler
