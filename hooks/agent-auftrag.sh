#!/usr/bin/env bash
# PreToolUse-Hook für Agent und Workflow: lehnt Aufträge ab, denen die Regeln eines Pflicht-Skills fehlen.
# - Video oder Film: Regeln aus dem Skill produktvideos. Grund: Agenten sehen nur den Auftrag; fehlt dort «Untertitel
#   nie eingebrannt», übernehmen sie die Montage der Social-Kurzfassungen (so am 09.10.2026 beim Tutorial-Film).
# - Recherche oder Websuche: Verweis auf den Skill recherche. Grund: Ohne ihn lesen Agenten ganze Seiten per
#   WebSearch und Jina (17.10.2026: rund 190'000 Tokens für 20 Firmen); der Hinweis von skill-hinweis.sh reicht
#   nicht, wenn der Auftrag selbst WebSearch und Jina als Werkzeuge vorgibt.
export LC_ALL=C.UTF-8
ein=$(cat)
prompt=$(jq -r '.tool_input.prompt // .tool_input.script // .tool_input.message // empty' <<<"$ein" 2>/dev/null)

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

if grep -qiE 'recherch|websearch|websuche|jina|r\.jina\.ai' <<<"$prompt" && ! grep -qiE 'skill[ `«]*recherche|skills/recherche' <<<"$prompt"; then
  ablehnen "Recherche-Auftrag ohne Skill recherche. In den Auftrag schreiben: «Zuerst /home/g/.claude/skills/recherche/SKILL.md lesen und einhalten: Suche per ~/projects/tools/recherche.py, Seiten per curl und rg auf Stichworte, Jina nur für einzelne gesperrte Seiten, nie ganze Seiten ins Modell.» Dann erneut starten."
fi
exit 0
