#!/usr/bin/env bash
# Tests für befunde-eingetragen.sh: bash hooks/test_befunde_eingetragen.sh
set -u
hier=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fehler=0

nutzer='{"type":"user","message":{"content":"mach X"}}'
bericht='{"type":"assistant","message":{"content":[{"type":"text","text":"Fertig.\n\n**Befunde**\n- Der Export ist kaputt."}]}}'
ohne='{"type":"assistant","message":{"content":[{"type":"text","text":"Fertig, alles hochgeladen."}]}}'
todo_edit='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{"file_path":"/home/g/projects/x/todo.md"}}]}}'
alt_edit='{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{"file_path":"/home/g/projects/x/TODO.md"}}]}}'

fall() { # name, erwartet (block|frei), stop_hook_active, zeilen...
  local name=$1 erwartet=$2 aktiv=$3; shift 3
  printf '%s\n' "$@" >"$tmp/t.jsonl"
  local aus
  aus=$(jq -n --arg t "$tmp/t.jsonl" --argjson a "$aktiv" '{transcript_path:$t, stop_hook_active:$a}' | "$hier/befunde-eingetragen.sh")
  local ist=frei
  grep -q '"decision": *"block"' <<<"$aus" && ist=block
  if [ "$ist" = "$erwartet" ]; then echo "ok   $name"; else echo "FAIL $name: erwartet $erwartet, ist $ist"; fehler=1; fi
}

fall "Befund ohne todo.md-Änderung blockiert" block false "$nutzer" "$bericht"
fall "Befund mit todo.md-Änderung läuft durch" frei false "$nutzer" "$todo_edit" "$bericht"
fall "Änderung vor der letzten Nutzernachricht zählt nicht" block false "$alt_edit" "$nutzer" "$bericht"
fall "Bericht ohne Befund läuft durch" frei false "$nutzer" "$ohne"
fall "zweiter Stopp nach Hinweis läuft durch" frei true "$nutzer" "$bericht"
fall "ohne Transkript läuft durch" frei false
exit $fehler
