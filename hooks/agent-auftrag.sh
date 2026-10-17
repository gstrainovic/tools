#!/usr/bin/env bash
# PreToolUse-Hook für Agent und Workflow: lehnt Aufträge ab, denen die Regeln eines Pflicht-Skills fehlen.
# - Video oder Film: Regeln aus dem Skill produktvideos. Grund: Agenten sehen nur den Auftrag; fehlt dort «Untertitel
#   nie eingebrannt», übernehmen sie die Montage der Social-Kurzfassungen (so am 09.10.2026 beim Tutorial-Film).
# - Recherche oder Websuche: Verweis auf den Skill recherche. Grund: Ohne ihn lesen Agenten ganze Seiten per
#   WebSearch und Jina (17.10.2026: rund 190'000 Tokens für 20 Firmen); der Hinweis von skill-hinweis.sh reicht
#   nicht, wenn der Auftrag selbst WebSearch und Jina als Werkzeuge vorgibt.
#   Dazu, wie der Skill es verlangt: der wörtliche Satz gegen Chrome und Playwright im Auftrag, und seit der
#   letzten Nutzernachricht eine eigene Skript-Suche im Transkript (recherche.py, Exa, ddgs oder Codex). Grund:
#   Am 18.10.2026 reichte der blosse Verweis auf den Skill; drei breit gefasste Agenten verbrauchten je über
#   100'000 Tokens, weil das Hauptmodell die Skript-Suche übersprungen hatte. Aufträge mit «keine neue Recherche»
#   (Bauaufträge, die nur die Recherche-Datei nennen) sind davon frei; ohne lesbares Transkript wird nie blockiert.
export LC_ALL=C.UTF-8
ein=$(cat)
prompt=$(jq -r '.tool_input.prompt // .tool_input.script // .tool_input.message // empty' <<<"$ein" 2>/dev/null)
transkript=$(jq -r '.transcript_path // empty' <<<"$ein" 2>/dev/null)

ablehnen() {
  jq -n --arg g "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $g}}'
  exit 0
}

# «rendern» und «Aufnahme» allein sind keine Videoarbeit (PDF rendern, Aufnahme in eine Liste);
# Aufträge, die Videos nur ausschliessen («Videos nicht ändern»), tragen den Vermerk «Keine Videoarbeit»
if grep -qiE 'video|film|untertitel|vertonen|screencast|bildschirmaufnahme|tonaufnahme|sprachaufnahme' <<<"$prompt" &&
  ! grep -qi 'nie eingebrannt' <<<"$prompt" && ! grep -qi 'keine videoarbeit' <<<"$prompt"; then
  ablehnen "Auftrag zu Video/Film ohne die Regeln aus dem Skill produktvideos. In den Auftrag schreiben: Untertitel als VTT-Spur, abschaltbar, nie eingebrannt (Kästen nur in Social-Kurzfassungen); echte Oberflächen; Zoom lesbar auf 375 px; Reihenfolge der Freigaben. Dann erneut starten. Betrifft der Auftrag Videos nur als Ausschluss, den Vermerk «Keine Videoarbeit» hineinschreiben."
fi

grep -qiE 'recherch|websearch|websuche|jina|r\.jina\.ai' <<<"$prompt" || exit 0
if ! grep -qiE 'skill[ `«]*recherche|skills/recherche' <<<"$prompt"; then
  ablehnen "Recherche-Auftrag ohne Skill recherche. In den Auftrag schreiben: «Zuerst /home/g/.claude/skills/recherche/SKILL.md lesen und einhalten: Suche per ~/projects/tools/recherche.py, Seiten per curl und rg auf Stichworte, Jina nur für einzelne gesperrte Seiten, nie ganze Seiten ins Modell.» Dann erneut starten."
fi
# Kein Rechercheauftrag, nur ein Verweis auf vorhandene Recherche: nichts weiter prüfen
grep -qiE 'keine (neue |web)?recherche' <<<"$prompt" && exit 0

if ! grep -qiE 'keine claude-in-chrome-werkzeuge und kein playwright' <<<"$prompt"; then
  ablehnen "Recherche-Auftrag ohne das Werkzeugverbot aus dem Skill recherche. Wörtlich in den Auftrag: «Keine Claude-in-Chrome-Werkzeuge und kein Playwright; was so nicht lesbar ist, als ‹nicht geprüft› markieren.» Dann erneut starten."
fi

# Eigene Skript-Suche seit der letzten Nutzernachricht (Skill recherche, «Zuerst per Skript, nicht per Agent»).
# Je Transkriptzeile: U = Nutzernachricht, S = Skript-Suche, X = anderes; nach dem letzten U muss ein S stehen.
[ -n "$transkript" ] && [ -r "$transkript" ] || exit 0
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
        | select(.name == "Bash" and ((.input.command // "")
            | test("recherche\\.py|api\\.exa\\.ai|(^|[;&|(\\s\"])ddgs\\s|(^|[;&|(\\s\"])codex\\s.*--search")))]
       | if length > 0 then "S" else "X" end)
    elif $e.type == "response_item" then
      ($e.payload // {}) as $p
      | if $p.type == "message" and $p.role == "user" then "U"
        elif $p.type == "function_call" or $p.type == "custom_tool_call" then
          (($p.arguments // $p.input // "") | if type == "string" then . as $s | (fromjson? // {command:$s}) else . end) as $i
          | if ($p.name | split(".") | last | IN("exec_command", "Bash", "shell", "shell_command", "exec"))
             and (($i.command // $i.cmd // "") | test("recherche\\.py|api\\.exa\\.ai|(^|[;&|(\\s\"])ddgs\\s|(^|[;&|(\\s\"])codex\\s.*--search")) then "S" else "X" end
        else "X" end
    else "X" end
' "$transkript" 2>/dev/null)
[ -n "$spur" ] || exit 0
nach_nutzer=$(tr -d '\n' <<<"$spur")
nach_nutzer=${nach_nutzer##*U}
[[ $nach_nutzer == *S* ]] && exit 0
ablehnen "Recherche-Auftrag ohne eigene Skript-Suche seit der letzten Nutzernachricht. Zuerst selbst suchen (~/projects/tools/recherche.py mit ddgs und Exa, dazu Codex mit --search im Hintergrund), die Funde in den Auftrag schreiben und den Agenten nur für das einsetzen, was Seiten lesen und beurteilen muss (Skill recherche, «Zuerst per Skript, nicht per Agent»)."
