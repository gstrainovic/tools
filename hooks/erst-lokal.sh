#!/usr/bin/env bash
# PreToolUse-Hook für WebSearch, WebFetch, mcp__jina-reader__* sowie Agent und Workflow mit Recherche-Auftrag:
# lehnt ab, solange seit der letzten echten Nutzernachricht keine lokale Suche im Transkript steht (Bash mit rg
# oder grep, Werkzeug Grep oder Glob). Grund: Am 09.10.2026 standen WooCommerce-Partnerantrag, Händlervertrag und
# Shopify-Machbarkeit im Repo, wurden aber als offen bezeichnet (Skill arbeitsweise, «Erst lokal, dann Web»).
# Ein Agenten-Auftrag, der selbst «zuerst lokal» verlangt, läuft durch. Ohne lesbares Transkript nie blockieren.
export LC_ALL=C.UTF-8
ein=$(cat)
feld() { jq -r "$1 // empty" <<<"$ein" 2>/dev/null; }
werkzeug=$(feld .tool_name)
transkript=$(feld .transcript_path)

case "$werkzeug" in
WebSearch | WebFetch | mcp__jina-reader__*) ;;
Agent | Workflow)
  prompt=$(jq -r '.tool_input.prompt // .tool_input.script // empty' <<<"$ein" 2>/dev/null)
  grep -qiE 'recherch|websuche|websearch|webfetch|jina|im web|online suchen' <<<"$prompt" || exit 0
  grep -qiE 'zuerst lokal|lokal lesen|(^|[^[:alnum:]_-])rg ' <<<"$prompt" && exit 0
  ;;
*) exit 0 ;;
esac

[ -n "$transkript" ] && [ -r "$transkript" ] || exit 0

# Je Zeile: U = echte Nutzernachricht, L = lokale Suche, X = lesbarer Eintrag; danach zählt nur, was nach dem
# letzten U kommt. Unlesbare Zeilen fallen weg.
spur=$(jq -R -r '
  (fromjson? // empty) as $e
  | if ($e | type) != "object" then empty
    elif $e.type == "user" and ($e.isMeta | not) then
      ($e.message.content) as $c
      | if ($c | type) == "string" then
          (if ($c | test("^\\s*<(task-notification|agent-message)")) then "X" else "U" end)
        elif ($c | type) == "array" and any($c[]?; .type? == "text")
             and (any($c[]?; .type? == "tool_result") | not) then "U"
        else "X" end
    elif $e.type == "assistant" then
      ([$e.message.content[]? | select(.type? == "tool_use")
        | select(.name == "Grep" or .name == "Glob"
                 or (.name == "Bash" and ((.input.command // "") | test("(^|[;&|(`\\s])(rg|grep)\\s"))))]
       | if length > 0 then "L" else "X" end)
    else "X" end
' "$transkript" 2>/dev/null)

# Keine lesbaren Einträge: kein Beleg, also durchlassen
[ -n "$spur" ] || exit 0
nach_nutzer=$(tr -d '\n' <<<"$spur")
nach_nutzer=${nach_nutzer##*U}
[[ $nach_nutzer == *L* ]] && exit 0

grund="Erst lokal suchen: rg über ~/projects (AGENTS.md, todo.md, akquise/, Skills) nach dem Thema, dann Web. Eigene Erfahrungen und Recherchen im Repo gelten vor Websuchen (Skill arbeitsweise)."
jq -n --arg g "$grund" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $g}}'
