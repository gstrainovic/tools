#!/usr/bin/env bash
# PreToolUse-Hook für Bash: sperrt frische Browser-Profile (Gorans Regel, Skill browser-wahl). Browserarbeit läuft
# nur in Gorans laufendem Chrome (`chrome-anhaengen`, Session gchrome über die Playwright Extension). Gesperrt sind
# `playwright-cli … open` (startet ein leeres Profil), `state-load` und `chrome-sitzung` (Cookie-Kopie in ein
# fremdes Profil), `attach --cdp` (Dialog in Gorans Chrome) sowie ein selbst gestarteter Chrome mit
# `--user-data-dir` oder `--remote-debugging-port`.
# Grund: Ohne Gorans Cookies erscheinen Captchas und Logins fehlen.
cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null)
[ -n "$cmd" ] || exit 0
# Text in Anführungszeichen (Commit-Nachrichten) und Heredoc-Inhalt fallen weg
cmd=$(awk '{print} /<</{exit}' <<<"$cmd" | sed -zE "s/\"([^\"\\\\]|\\\\.)*\"//g; s/'[^']*'//g" | tr -d '\0')

grund=""
if grep -qE '(^|[;&|[:space:]])playwright-cli([[:space:]]+-[^[:space:]]+)*[[:space:]]+open([[:space:]]|$)' <<<"$cmd"; then
  grund="playwright-cli open startet ein frisches Profil"
elif grep -qE '(^|[;&|[:space:]])playwright-cli([[:space:]]+-[^[:space:]]+)*[[:space:]]+state-load([[:space:]]|$)' <<<"$cmd"; then
  grund="state-load lädt Cookie-Kopien in ein fremdes Profil"
elif grep -qE '(^|[;&|[:space:]])chrome-sitzung([[:space:]]|$)' <<<"$cmd"; then
  grund="chrome-sitzung kopiert Cookies für ein fremdes Profil"
elif grep -qE '(google-chrome|chromium|chrome)[^;&|]*--user-data-dir' <<<"$cmd"; then
  grund="Chrome mit --user-data-dir startet ein eigenes, leeres Profil"
elif grep -qE '(^|[;&|[:space:]])playwright-cli[^;&|]*[[:space:]]attach[^;&|]*--cdp' <<<"$cmd"; then
  grund="attach --cdp löst in Gorans Chrome den Dialog «Remote-Fehlerbehebung zulassen?» aus"
elif grep -qE '(google-chrome|chromium|chrome)[^;&|]*--remote-debugging-port' <<<"$cmd"; then
  grund="Chrome mit --remote-debugging-port umgeht die Playwright Extension (CDP-Dialog oder fremdes Profil)"
fi
[ -n "$grund" ] || exit 0

text="Verboten (Gorans Regel, Skill browser-wahl): kein frisches oder kopiertes Browser-Profil. Erkannt: $grund. Stattdessen an Gorans laufenden Chrome anhängen: chrome-anhaengen, dann eigene Tabs mit -s=gchrome tab-new."
jq -n --arg t "$text" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $t}}'
