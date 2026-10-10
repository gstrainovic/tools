#!/usr/bin/env bash
# Prüft hooks/erst-lokal.sh: Websuche (WebSearch, WebFetch, Jina) und Recherche-Aufträge an Agenten werden abgelehnt,
# solange seit der letzten echten Nutzernachricht keine lokale Suche (rg/grep in Bash, Grep, Glob) im Transkript
# steht. Ein Agenten-Auftrag, der selbst «zuerst lokal» verlangt, läuft durch; ohne Transkript wird nie blockiert.
set -euo pipefail
cd "$(dirname "$0")/.."
hook=hooks/erst-lokal.sh
fehler=0
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Bausteine eines Transkripts im Format echter Sitzungen (JSONL)
nutzer()   { printf '{"type":"user","message":{"role":"user","content":"%s"}}\n' "$1"; }
nutzer_a() { printf '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"%s"}]}}\n' "$1"; }
ergebnis() { printf '{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"toolu_01","content":"ok"}]}}\n'; }
meldung()  { printf '{"type":"user","message":{"role":"user","content":"<task-notification>Agent fertig</task-notification>"}}\n'; }
bash_cmd() { jq -cn --arg c "$1" '{type:"assistant",message:{content:[{type:"tool_use",id:"toolu_01",name:"Bash",input:{command:$c}}]}}'; }
werkzeug() { jq -cn --arg n "$1" '{type:"assistant",message:{content:[{type:"tool_use",id:"toolu_01",name:$n,input:{pattern:"WooCommerce"}}]}}'; }
text()     { jq -cn --arg t "$1" '{type:"assistant",message:{content:[{type:"text",text:$t}]}}'; }
# transkript: liest Zeilen von stdin, gibt den Pfad aus
transkript() { local f; f=$(mktemp "$tmp/t.XXXXXX"); cat >"$f"; echo "$f"; }

web_ein()   { jq -n --arg w "$1" --arg t "$2" '{hook_event_name:"PreToolUse",tool_name:$w,tool_input:{query:"WooCommerce Partner"},transcript_path:$t}'; }
agent_ein() { jq -n --arg p "$1" --arg t "$2" '{hook_event_name:"PreToolUse",tool_name:"Agent",tool_input:{prompt:$p},transcript_path:$t}'; }

entscheid() {
  local aus; aus=$(printf '%s' "$1" | "$hook")
  if [ -z "$aus" ]; then echo keine; else jq -r '.hookSpecificOutput.permissionDecision // "keine"' <<<"$aus"; fi
}
pruefe() { local e; e=$(entscheid "$2"); if [ "$e" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1 (erwartet $3, war $e)"; fehler=1; fi; }

ohne_rg=$( { nutzer "Prüf den WooCommerce-Partnerantrag"; text "Ich suche im Web."; } | transkript)
mit_rg=$( { nutzer "Prüf den WooCommerce-Partnerantrag"; bash_cmd "rg -i woocommerce ~/projects"; ergebnis; } | transkript)
mit_grep=$( { nutzer "Prüf das"; bash_cmd "cd ~/projects && grep -ri partner find-jobs"; ergebnis; } | transkript)
rg_davor=$( { nutzer "Alte Aufgabe"; bash_cmd "rg -i shopify ~/projects"; ergebnis; nutzer_a "Neue Frage: WooCommerce-Partner?"; } | transkript)
rg_vor_ergebnis=$( { nutzer "Frage"; bash_cmd "rg partner ~/projects"; ergebnis; meldung; ergebnis; } | transkript)
grep_wz=$( { nutzer "Frage"; werkzeug Grep; ergebnis; } | transkript)
glob_wz=$( { nutzer "Frage"; werkzeug Glob; ergebnis; } | transkript)
rg_im_text=$( { nutzer "Frage"; bash_cmd "git log --grep=x; echo 'rg '"; text "rg wäre gut"; } | transkript)
kaputt=$(printf 'kein json\n{"type":"user"\n' | transkript)

pruefe "WebSearch ohne lokale Suche wird abgelehnt" "$(web_ein WebSearch "$ohne_rg")" deny
pruefe "WebFetch ohne lokale Suche wird abgelehnt" "$(web_ein WebFetch "$ohne_rg")" deny
pruefe "WebSearch nach Bash rg läuft durch" "$(web_ein WebSearch "$mit_rg")" keine
pruefe "WebSearch nach Bash grep läuft durch" "$(web_ein WebSearch "$mit_grep")" keine
pruefe "rg nur vor der letzten Nutzernachricht zählt nicht" "$(web_ein WebSearch "$rg_davor")" deny
pruefe "Tool-Ergebnis und Agentenmeldung sind keine Nutzernachricht" "$(web_ein WebSearch "$rg_vor_ergebnis")" keine
pruefe "Grep-Werkzeug zählt" "$(web_ein WebSearch "$grep_wz")" keine
pruefe "Glob-Werkzeug zählt" "$(web_ein WebFetch "$glob_wz")" keine
pruefe "rg nur in Text oder git --grep zählt nicht" "$(web_ein WebSearch "$rg_im_text")" deny
pruefe "fehlendes Transkript läuft durch" "$(web_ein WebSearch "$tmp/fehlt.jsonl")" keine
pruefe "unlesbares Transkript läuft durch" "$(web_ein WebSearch "$kaputt")" keine
pruefe "Transkript ohne Pfad läuft durch" '{"hook_event_name":"PreToolUse","tool_name":"WebSearch","tool_input":{"query":"x"}}' keine

pruefe "Agent mit Recherche ohne lokalen Hinweis wird abgelehnt" "$(agent_ein "Recherchiere WooCommerce-Marktplatz und Shopify im Web." "$ohne_rg")" deny
pruefe "Agent mit Jina-Auftrag wird abgelehnt" "$(agent_ein "Lies die Seite über r.jina.ai und fasse zusammen." "$ohne_rg")" deny
pruefe "Agent mit «zuerst lokal» läuft durch" "$(agent_ein "Recherchiere Marktplätze. Zuerst lokal mit rg über ~/projects suchen." "$ohne_rg")" keine
pruefe "Agent mit Recherche nach eigener rg-Suche läuft durch" "$(agent_ein "Websuche zu WooCommerce-Partnern." "$mit_rg")" keine
pruefe "Agent ohne Recherchebezug läuft durch" "$(agent_ein "Korrigiere die fr_FR.po aller Plugins." "$ohne_rg")" keine
pruefe "Workflow-Skript mit Websuche wird abgelehnt" "$(jq -n --arg t "$ohne_rg" '{hook_event_name:"PreToolUse",tool_name:"Workflow",tool_input:{script:"WebSearch nach Preisen"},transcript_path:$t}')" deny

grund=$(web_ein WebSearch "$ohne_rg" | "$hook" | jq -r '.hookSpecificOutput.permissionDecisionReason // ""')
if grep -q "Erst lokal suchen" <<<"$grund" && grep -q "arbeitsweise" <<<"$grund"; then echo "ok   Grund nennt rg und Skill"; else echo "FAIL Grund nennt rg und Skill"; fehler=1; fi

exit $fehler
