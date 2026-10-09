#!/usr/bin/env bash
# Prüft hooks/modellwahl.sh: vor Agent- und Workflow-Aufrufen kommt die Modellwahl aus dem Skill arbeitsweise
# als additionalContext zurück, gültiges JSON, Aufruf wird nie blockiert.
set -euo pipefail
cd "$(dirname "$0")/.."
hook=hooks/modellwahl.sh
fehler=0
pruefe() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fehler=1; fi; }

aus=$(echo '{"tool_name":"Agent","tool_input":{"model":"sonnet","prompt":"x"}}' | "$hook")
pruefe "gültiges JSON" "echo '$aus' | jq -e . >/dev/null"
pruefe "Ereignis PreToolUse" "[ \"\$(echo '$aus' | jq -r .hookSpecificOutput.hookEventName)\" = PreToolUse ]"
kontext=$(echo "$aus" | jq -r .hookSpecificOutput.additionalContext)
pruefe "nennt Opus für TDD" "grep -q 'Opus' <<<\"\$kontext\" && grep -q 'TDD' <<<\"\$kontext\""
pruefe "nennt Haiku und Sonnet" "grep -q 'Haiku' <<<\"\$kontext\" && grep -q 'Sonnet' <<<\"\$kontext\""
pruefe "Bewerbungstexte immer Fable" "grep -q 'Bewerbungs.*Fable' <<<\"\$kontext\""
pruefe "verweist auf arbeitsweise" "grep -q 'arbeitsweise' <<<\"\$kontext\""
pruefe "nennt gewähltes Modell" "grep -q 'sonnet' <<<\"\$kontext\""
pruefe "blockiert nicht" "[ \"\$(echo '$aus' | jq -r '.hookSpecificOutput.permissionDecision // \"keine\"')\" = keine ]"

aus=$(echo '{"tool_name":"Agent","tool_input":{"prompt":"x"}}' | "$hook")
pruefe "ohne Modell: Hinweis auf Erbe des Hauptmodells" "echo '$aus' | jq -r .hookSpecificOutput.additionalContext | grep -q 'Hauptmodell'"

exit $fehler
