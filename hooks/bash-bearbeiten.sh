#!/usr/bin/env bash
# PreToolUse-Hook für Bash: erinnert an die Regel aus ~/.claude/CLAUDE.md «Bearbeiten per Read/Edit/Write, nie sed,
# Python-Heredocs oder andere Bash-Umwege», sobald ein Befehl eine Datei ausserhalb von /tmp und /dev schreibt.
# Blockiert nie; erlaubte Fälle (etwa ein Build, der eine Datei erzeugt) laufen nach dem Hinweis weiter.
cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null)
[ -n "$cmd" ] || exit 0

grund=""
if grep -qE '(^|[;&|[:space:]])sed[[:space:]]+(-[a-zA-Z]*i|--in-place)' <<<"$cmd"; then
  grund="sed -i"
elif grep -qE '(^|[;&|[:space:]])perl[[:space:]]+-[a-zA-Z]*i' <<<"$cmd"; then
  grund="perl -i"
elif grep -qE '(^|[;&|[:space:]])python3?[[:space:]]+(-([[:space:]]|$)|<<)' <<<"$cmd"; then
  grund="Python-Skript aus Heredoc"
else
  # Ziele von Umleitungen (> und >>, ohne 2>&1 o. ä.) und von tee
  ziele=$(grep -oE '(^|[^0-9&<>])>>?[[:space:]]*[^[:space:]&|;<>]+' <<<"$cmd" | sed -E 's/^[^>]*>>?[[:space:]]*//')
  ziele+=$'\n'$(grep -oE '(^|[;&|[:space:]])tee([[:space:]]+-a)?[[:space:]]+[^[:space:]&|;<>]+' <<<"$cmd" | awk '{print $NF}')
  while IFS= read -r z; do
    [ -z "$z" ] && continue
    case "$z" in /tmp/*|/dev/*) ;; *) grund="Umleitung oder tee in $z"; break ;; esac
  done <<<"$ziele"
fi
[ -n "$grund" ] || exit 0

text="Regel ~/.claude/CLAUDE.md: Dateien per Read und Edit ändern, neue Dateien per Write; nie sed, Python-Heredocs oder andere Bash-Umwege zum Bearbeiten. Erkannt: $grund. Ist es eine Bearbeitung, stattdessen Edit oder Write nehmen."
jq -n --arg t "$text" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $t}}'
