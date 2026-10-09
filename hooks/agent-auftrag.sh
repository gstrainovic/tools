#!/usr/bin/env bash
# PreToolUse-Hook für Agent und Workflow: Ein Auftrag zu Video oder Film muss die Regeln aus dem Skill produktvideos
# enthalten, sonst wird er abgelehnt. Grund: Agenten sehen nur den Auftrag; fehlt dort «Untertitel nie eingebrannt»,
# übernehmen sie die Montage der Social-Kurzfassungen (so am 09.10.2026 beim Tutorial-Film).
export LC_ALL=C.UTF-8
ein=$(cat)
prompt=$(jq -r '.tool_input.prompt // .tool_input.script // empty' <<<"$ein" 2>/dev/null)
grep -qiE 'video|film|rendern|untertitel|vertonen|aufnahme' <<<"$prompt" || exit 0
grep -qi 'nie eingebrannt' <<<"$prompt" && exit 0
grund="Auftrag zu Video/Film ohne die Regeln aus dem Skill produktvideos. In den Auftrag schreiben: Untertitel als VTT-Spur, abschaltbar, nie eingebrannt (Kästen nur in Social-Kurzfassungen); echte Oberflächen; Zoom lesbar auf 375 px; Reihenfolge der Freigaben. Dann erneut starten."
jq -n --arg g "$grund" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $g}}'
