#!/usr/bin/env bash
# PreToolUse-Hook für Bash: sperrt lange Aufrufe, deren Ausgabe direkt in grep, tail, head & Co. läuft (Gorans
# Regel, Skill arbeitsweise). Der Filter hält die Ausgabe bis zum Ende zurück; hängt der Aufruf, sieht niemand
# etwas. Lange Aufrufe sind Programme mit Netz- oder Rechenzeit: uv run, python, node, curl, codex,
# playwright-cli, ads, npm/npx, pytest. Erlaubt bleibt: Ausgabe in eine Datei schreiben und die Datei filtern.
cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null)
[ -n "$cmd" ] || exit 0
# Text in Anführungszeichen (Commit-Nachrichten, Prompts) und Heredoc-Inhalt fallen weg
cmd=$(awk '{print} /<</{exit}' <<<"$cmd" | sed -zE "s/\"([^\"\\\\]|\\\\.)*\"//g; s/'[^']*'//g" | tr -d '\0')

lang='(^|[[:space:]/(])(uv[[:space:]]+run|python3?|node|curl|codex|playwright-cli|ads(\.py)?|npm|npx|pytest)([[:space:]]|$)'
filter='^[[:space:]]*(grep|egrep|rg|tail|head|cut|awk|sed|sort|uniq|wc|tr)([[:space:]]|$)'

treffer=""
# in Befehle zerlegen (; && || Zeilenumbruch), je Befehl die Stufen einer Pipe prüfen
while IFS= read -r befehl; do
  [[ "$befehl" == *"|"* ]] || continue
  IFS='|' read -r -a stufen <<<"$befehl"
  grep -qE "$lang" <<<"${stufen[0]}" || continue
  for s in "${stufen[@]:1}"; do
    if grep -qE "$filter" <<<"$s"; then treffer="${stufen[0]}|$s"; break; fi
  done
  [ -n "$treffer" ] && break
done < <(sed -E 's/\|\|/\n/g; s/&&/\n/g; s/;/\n/g; s/\|&/|/g' <<<"$cmd")
[ -n "$treffer" ] || exit 0

text="Verboten (Gorans Regel, Skill arbeitsweise): kein langer Aufruf mit der Ausgabe direkt in grep, tail oder head. Erkannt: ${treffer}. Stattdessen Ausgabe in eine Datei schreiben (> datei 2>&1), Python mit -u, Zeitlimit setzen, dann die Datei lesen."
jq -n --arg t "$text" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $t}}'
