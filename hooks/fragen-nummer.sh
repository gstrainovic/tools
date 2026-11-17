#!/usr/bin/env bash
# Stop-Hook: Stellt die letzte Antwort eine Frage an Goran, braucht jede eine Nummer aus `fragen neu` (Regel
# «Fragen» in skills-privat/claude/gemeinsam.md). Abgelehnt wird eine Zeile «**Frage:**» ohne Nummer und eine
# Optionsliste «- a)» ohne irgendeine «Frage <Nummer>» in der Antwort. Beim zweiten Stopp (stop_hook_active) nie.
export LC_ALL=C.UTF-8
freigeben() { printf '{}\n'; exit 0; }
ein=$(cat)
[ "$(jq -r '.stop_hook_active // false' <<<"$ein" 2>/dev/null)" = "true" ] && freigeben
text=$(jq -r '.last_assistant_message // empty' <<<"$ein" 2>/dev/null)
[ -n "$text" ] || freigeben

ohne_nummer=false
grep -qE '^\*\*Frage(:|\*| *$| [^0-9])' <<<"$text" && ohne_nummer=true
if grep -qE '^- (\*\*)?[a-e]\)' <<<"$text" && ! grep -qE 'Frage [0-9]+' <<<"$text"; then ohne_nummer=true; fi
$ohne_nummer || freigeben

jq -cn '{decision: "block", reason: "Die Antwort stellt eine Frage ohne Nummer. Nummern per `python ~/projects/tools/fragen.py neu [anzahl]` holen (Linux: `fragen neu`) und jede Frage als «**Frage <Nummer>:**» stellen (Regel «Fragen», skills-privat/claude/gemeinsam.md), dann die Antwort wiederholen."}'
