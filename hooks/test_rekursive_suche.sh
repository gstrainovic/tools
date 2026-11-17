#!/usr/bin/env bash
# Tests für rekursive-suche.sh: bash hooks/test_rekursive_suche.sh
set -u
hier=$(cd "$(dirname "$0")" && pwd)
fehler=0

fall() { # name, erwartet (sperre|frei), werkzeug, befehl
  local name=$1 erwartet=$2 werkzeug=$3 befehl=$4 aus ist=frei
  aus=$(jq -n --arg w "$werkzeug" --arg c "$befehl" '{hook_event_name:"PreToolUse", tool_name:$w, tool_input:{command:$c}}' |
    "$hier/rekursive-suche.sh")
  grep -q '"permissionDecision": *"deny"' <<<"$aus" && ist=sperre
  if [ "$ist" = "$erwartet" ]; then echo "ok   $name"; else echo "FAIL $name: erwartet $erwartet, ist $ist"; fehler=1; fi
}

fall "Get-ChildItem -Recurse sperrt" sperre PowerShell "Get-ChildItem 'O:\\340_WebGIS' -Recurse -File -Include '*.docx'"
fall "gci -r sperrt" sperre PowerShell "gci O:\\ -r -Filter *.pdf"
fall "ls -Recurse sperrt" sperre PowerShell "ls C:\\x -Recurse | Select-Object Name"
fall "dir -rec sperrt" sperre PowerShell "dir F:\\BM -rec"
fall "Get-ChildItem in Start-Job sperrt" sperre PowerShell "\$job = Start-Job { Get-ChildItem 'O:\\a','O:\\b' -Recurse -File }"
fall "dir /s sperrt" sperre PowerShell "cmd /c dir /s /b O:\\*.docx"
fall "dir /s in Bash sperrt" sperre Bash "cmd //c dir /s /b"
fall "Get-ChildItem ohne Recurse ist frei" frei PowerShell "Get-ChildItem O:\\ -Directory | Select-Object Name"
fall "fd ist frei" frei PowerShell "fd -i -t f 'protokoll' 'O:\\340_WebGIS'"
fall "Remove-Item -Recurse ist frei" frei PowerShell "Remove-Item -Recurse -Force C:\\tmp\\x"
fall "Copy-Item -Recurse ist frei" frei PowerShell "Copy-Item -Recurse a b"
fall "Recurse im Commit-Text ist frei" frei PowerShell "git commit -m 'Get-ChildItem -Recurse ersetzt'"
fall "Get-ChildItem und danach Remove-Item -Recurse ist frei" frei PowerShell "Get-ChildItem C:\\x; Remove-Item -Recurse C:\\y"

exit $fehler
