#!/usr/bin/env bash
# Stop-Hook: Enthält der Schlussbericht Befunde, muss seit der letzten echten Nutzernachricht eine todo.md (oder
# TODO.md) geändert worden sein (Edit, Write oder Bash mit todo.md). Sonst einmal zurück an Claude mit dem Hinweis,
# die Befunde einzutragen (Regel «Knapp berichten» in ~/.claude/CLAUDE.md). Grund: Befunde standen nur im
# Gesprächsverlauf und gingen mit /clear verloren. Beim zweiten Stopp (stop_hook_active) und ohne lesbares
# Transkript nie blockieren.
export LC_ALL=C.UTF-8
ein=$(cat)
[ "$(jq -r '.stop_hook_active // false' <<<"$ein" 2>/dev/null)" = "true" ] && exit 0
transkript=$(jq -r '.transcript_path // empty' <<<"$ein" 2>/dev/null)
[ -n "$transkript" ] && [ -r "$transkript" ] || exit 0

# Je Zeile: U = echte Nutzernachricht, T = Änderung an einer todo.md, B:<text> = Text von Claude
spur=$(jq -R -r '
  (fromjson? // empty) as $e
  | if ($e | type) != "object" then empty
    elif $e.type == "user" and ($e.isMeta | not) then
      ($e.message.content) as $c
      | if ($c | type) == "string" then
          (if ($c | test("^\\s*<")) then empty else "U" end)
        elif ($c | type) == "array" and any($c[]?; .type? == "text")
             and (any($c[]?; .type? == "tool_result") | not) then "U"
        else empty end
    elif $e.type == "assistant" then
      ($e.message.content[]?
        | if .type? == "tool_use"
             and (((.input.file_path // "") | test("(?i)todo\\.md$"))
                  or (.name == "Bash" and ((.input.command // "") | test("(?i)todo\\.md")))) then "T"
          elif .type? == "text" then "B:" + (.text | gsub("\n"; " "))
          else empty end)
    elif $e.type == "response_item" then
      ($e.payload // {}) as $p
      | if $p.type == "message" and $p.role == "user" then "U"
        elif $p.type == "message" and $p.role == "assistant" then
          ($p.content[]?
            | select((.type == "output_text" or .type == "text") and (.text | type == "string"))
            | "B:" + (.text | gsub("\\n"; " ")))
        elif ($p.type == "custom_tool_call" or $p.type == "function_call")
             and ((($p.input // $p.arguments // "") | tostring) | test("(?i)todo\\.md")) then "T"
        else empty end
    else empty end' "$transkript" 2>/dev/null)

nach=$(awk '/^U$/ {buf=""; next} {buf = buf $0 "\n"} END {printf "%s", buf}' <<<"$spur")
# Das Transkript kann beim Stopp der letzten Antwort hinterherhinken; massgeblich ist last_assistant_message
letzter=$(jq -r '.last_assistant_message // empty' <<<"$ein" 2>/dev/null)
[ -n "$letzter" ] || letzter=$(grep '^B:' <<<"$nach" | tail -1)
# Befunde heissen nicht immer so (Entscheid 3a, 11.10.2026): auch Risiken, Ungeklärtes, Fehlendes, Widersprüche
grep -qiE 'befund|risiko|ungeklärt|unklar|fehlt|nicht aufgeht' <<<"$letzter" || exit 0
grep -q '^T$' <<<"$nach" && exit 0

jq -cn '{decision: "block", reason: "Der Schlussbericht nennt Befunde, aber seit der letzten Nutzernachricht wurde keine todo.md geändert. Befunde und offene Fragen in die todo.md des betroffenen Repos eintragen, committen und hochladen (Regel «Knapp berichten», ~/.claude/CLAUDE.md), dann den Bericht wiederholen. Stehen sie dort schon, kurz so melden."}'
