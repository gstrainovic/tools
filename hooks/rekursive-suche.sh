#!/usr/bin/env bash
# PreToolUse-Hook für Bash und PowerShell: sperrt die rekursive Dateisuche mit Get-ChildItem -Recurse (auch gci,
# ls, dir) und dir /s (Regel «Werkzeugwahl», gemeinsam.md). Sie ist auf Netzlaufwerken und grossen Bäumen um ein
# Vielfaches langsamer als fd. Erlaubt bleiben Get-ChildItem ohne -Recurse und -Recurse bei anderen Befehlen
# (Remove-Item, Copy-Item).
cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null)
[ -n "$cmd" ] || exit 0
# Text in Anführungszeichen (Commit-Nachrichten, Pfade) und Heredoc-Inhalt fallen weg
cmd=$(awk '{print} /<</{exit}' <<<"$cmd" | sed -zE "s/\"([^\"\\\\]|\\\\.)*\"//g; s/'[^']*'//g" | tr -d '\0')

kopf='^[[:space:]]*(\$[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=[[:space:]]*)?(cmd(\.exe)?[[:space:]]+/{1,2}c[[:space:]]+)?(get-childitem|gci|ls|dir)([[:space:]]|$)'
rekursiv='[[:space:]](-r|-rec[a-z]*|/s)([[:space:]]|$)'

treffer=""
# in Befehle zerlegen (; && || | Zeilenumbruch und Skriptblöcke { })
while IFS= read -r befehl; do
  if grep -qiE "$kopf" <<<"$befehl" && grep -qiE "$rekursiv" <<<"$befehl"; then treffer=$befehl; break; fi
done < <(sed -E 's/\|\|/\n/g; s/&&/\n/g; s/[;|{}]/\n/g' <<<"$cmd")
[ -n "$treffer" ] || exit 0

text="Verboten (Regel «Werkzeugwahl», gemeinsam.md): keine rekursive Dateisuche mit Get-ChildItem -Recurse oder dir /s, sie ist auf Netzlaufwerken sehr langsam. Erkannt: ${treffer}. Stattdessen Glob bzw. Grep; brechen die ab: fd für Dateinamen (C:\\Users\\g.strainovic\\scoop\\shims\\fd.exe -i -t f <muster> <ordner…>), rg für Inhalte."
jq -n --arg t "$text" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $t}}'
