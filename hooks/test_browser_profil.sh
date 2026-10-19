#!/usr/bin/env bash
# Tests für browser-profil.sh: bash hooks/test_browser_profil.sh
set -u
hier=$(cd "$(dirname "$0")" && pwd)
fehler=0

fall() { # name, erwartet (sperre|frei), befehl
  local name=$1 erwartet=$2 befehl=$3 aus ist=frei
  aus=$(jq -n --arg c "$befehl" '{hook_event_name:"PreToolUse", tool_name:"Bash", tool_input:{command:$c}}' |
    "$hier/browser-profil.sh")
  grep -q '"permissionDecision": *"deny"' <<<"$aus" && ist=sperre
  if [ "$ist" = "$erwartet" ]; then echo "ok   $name"; else echo "FAIL $name: erwartet $erwartet, ist $ist"; fehler=1; fi
}

fall "open mit Sitzung sperrt" sperre "playwright-cli -s=partner open https://example.ch --browser=chrome --headed"
fall "open ohne Sitzung sperrt" sperre "playwright-cli open about:blank"
fall "open nach cd sperrt" sperre "cd ~/projects/find-jobs && playwright-cli -s=x open https://a.ch"
fall "open mit --session sperrt" sperre "playwright-cli --session=gsc open about:blank"
fall "state-load sperrt" sperre "playwright-cli -s=x state-load /tmp/stand.json"
fall "chrome-sitzung sperrt" sperre "chrome-sitzung /tmp/stand.json linkedin.com"
fall "attach an Gorans Chrome ist frei" frei "playwright-cli attach --cdp=chrome --session=gchrome"
fall "attach über die Erweiterung ist frei" frei "playwright-cli attach --extension=chrome --session=gchrome"
fall "chrome-anhaengen ist frei" frei "chrome-anhaengen"
fall "Befehle in angehängter Sitzung sind frei" frei "playwright-cli -s=gchrome goto https://partner.zendesk.com"
fall "tab-new in angehängter Sitzung ist frei" frei "playwright-cli -s=gchrome tab-new https://a.ch"
fall "close ist frei" frei "playwright-cli -s=partner close"
fall "Commit-Nachricht mit dem Wort ist frei" frei "git commit -m 'playwright-cli open verboten'"
fall "anderer Befehl ist frei" frei "ls -la"
exit $fehler
