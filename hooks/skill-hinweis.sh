#!/usr/bin/env bash
# Hook für PreToolUse (Bash, Edit|Write, mcp__claude-in-chrome__.*) und UserPromptSubmit: erkennt anhand einer
# festen Tabelle «Anlass → Skill», welcher Skill für den Schritt gilt, und erinnert per additionalContext daran,
# ihn zu laden. Gemeldet werden nur Skills, die laut Transkript (transcript_path, JSONL) in dieser Sitzung noch
# nicht per Skill-Werkzeug geladen wurden; fehlt das Transkript oder ist es unlesbar, kommt der Hinweis immer.
# Blockiert nie.
export LC_ALL=C.UTF-8
ein=$(cat)
feld() { jq -r "$1 // empty" <<<"$ein" 2>/dev/null; }
ereignis=$(feld .hook_event_name)
werkzeug=$(feld .tool_name)
transkript=$(feld .transcript_path)

skills=()
gruende=()
# Im Subagenten zählt auch dessen eigenes Transkript: <sitzung>/subagents/agent-<agent_id>.jsonl neben <sitzung>.jsonl
protokolle=("$transkript")
agent=$(feld .agent_id)
[ -n "$agent" ] && [[ $transkript == *.jsonl ]] && protokolle+=("${transkript%.jsonl}/subagents/agent-$agent.jsonl")
# Geladen = Aufruf des Skill-Werkzeugs, Form: "name":"Skill","input":{"skill":"<name>", oder (Subagenten) Read der
# Datei …/skills/<name>/SKILL.md
geladen() {
  local p
  for p in "${protokolle[@]}"; do
    [ -n "$p" ] && [ -r "$p" ] || continue
    jq -Rse --arg s "$1" '
      any(split("\n")[] | fromjson?
          | if .type == "assistant" then .message.content[]? | select(.type? == "tool_use")
            elif .type == "response_item" then .payload | select(.type == "function_call" or .type == "custom_tool_call")
            else empty end;
        (.name | split(".") | last) as $n
        | (.input // .arguments // {}) as $raw
        | ($raw | if type == "string" then . as $x | (fromjson? // {command:$x}) else . end) as $i
        | ($n == "Skill" and $i.skill == $s)
          or ($n == "Read" and (($i.file_path // "") | endswith("/skills/" + $s + "/SKILL.md")))
          or (($n | IN("Bash", "exec_command", "shell", "shell_command", "exec"))
              and (($i.command // $i.cmd // "") | test("(^|[;&|(\\s\"])(cat|head|tail|bat|sed)\\s"))
              and (($i.command // $i.cmd // "") | contains("/skills/" + $s + "/SKILL.md"))))
    ' "$p" >/dev/null 2>&1 && return 0
  done
  return 1
}
hinzu() {
  local x
  for x in "${skills[@]}"; do [ "$x" = "$1" ] && return; done
  geladen "$1" && return
  skills+=("$1")
  gruende+=("$2")
}

case "$werkzeug" in
Bash)
  bevor="dieser Befehl läuft"
  cmd=$(jq -r '.tool_input.command // .tool_input.cmd // empty' <<<"$ein")
  # Wie bash-bearbeiten.sh: Heredoc-Inhalt und Text in Anführungszeichen (Commit-Nachrichten, Mailtexte) fallen weg.
  cmd=$(awk '{print} /<</{exit}' <<<"$cmd" | sed -E "s/\"([^\"\\\\]|\\\\.)*\"//g; s/'[^']*'//g")
  hat() { grep -qE "$1" <<<"$cmd"; }
  a='(^|[;&|(`[:space:]])'   # Anfang eines Befehls
  p='(^|[;&|(`[:space:]/])'  # Anfang eines Befehls oder Dateinamens nach einem Pfad
  if hat "${p}mailbox(\.py)?[[:space:]]+(send|reply)([[:space:]]|$)"; then
    zusatz="Text der Mail von Fable geschrieben (Skill arbeitsweise, Punkt 6)? Wenn nicht: erst von einem Fable-Agenten schreiben lassen."
    hinzu mailbox "Befehle, Konten und Signatur von mailbox"
    rest=$(grep -oE "mailbox(\.py)?[[:space:]]+(send|reply)([[:space:]].*)?$" <<<"$cmd")
    if grep -qE '[[:space:]](strainovic|strainovic-dev|kmu-plugins|ki-flows|wartungsheft)([[:space:]]|$)' <<<"$rest"; then
      hinzu akquise-direkt "Prüfung «Rechte am Code» und Partnermodelle vor jeder Mail an Kunden, Agenturen und Partner"
      hinzu nachhalten "Freund-Feind-Check vor jeder Antwort auf eine Rückmeldung"
    fi
  fi
  hat "${p}mailbox(\.py)?[[:space:]]+(list|read|search)([[:space:]]|$)" &&
    hinzu nachhalten "Eingänge auswerten, wegräumen und jede Mail dem zuständigen Fach-Skill zuordnen"
  { hat "${a}svn[[:space:]]+(ci|commit)([[:space:]]|$)" || hat "${p}svn-ci\.sh" ||
    hat "${a}wp[[:space:]]+plugin[[:space:]]+check"; } &&
    hinzu wp-plugin-ch "Plugin Check, SVN-Ablauf und Übersetzungen der WordPress-Plugins"
  hat "${p}(jobs|karriereseiten|exa_inserate)\.py" &&
    hinzu stellenboersen-api "Aufrufvarianten, Quellen und Filter der Stellensuche"
  hat "${p}(foren|forum_antwort)\.py" &&
    hinzu foren "Treffer bewerten und die wenigen Konten, mit denen gepostet werden darf"
  hat "${p}(zustellbarkeit|versandlimit|postmaster)\.py" &&
    hinzu mail-versand "Absender-Domains, Zustellbarkeit und Drosselung"
  hat "${p}yt\.py" &&
    hinzu produktvideos "Hochladen, Ersetzen und Lokalisieren der Produktvideos"
  hat "${p}heimarbeit\.py" &&
    hinzu heimarbeit "Ausschlusskriterien gegen Vorkasse-Maschen und heimarbeit/geprueft.md"
  hat "${a}pgrep[[:space:]]+-[a-zA-Z]*f" &&
    hinzu arbeitsweise "pgrep -f findet auch den eigenen Befehl, Warte-Schleifen anders bauen"
  ;;
Edit | Write | MultiEdit | apply_patch)
  bevor="diese Datei geändert wird"
  if [ "$werkzeug" = apply_patch ]; then
    pfade=$(jq -r '.tool_input | if type == "string" then . else .command // .input // "" end' <<<"$ein" |
      awk '/^\*\*\* (Add File|Update File|Delete File|Move to): / {sub(/^\*\*\* [^:]+: /, ""); print}')
  else
    pfade=$(feld .tool_input.file_path)
  fi
  while IFS= read -r pfad; do
  name=${pfad##*/}
  case "$name" in
  TODO.md | todo.md | AGENTS.md | CLAUDE.md | README.md | SKILL.md)
    hinzu doku-pflege "nur geltender Stand, kein Changelog, Falsches löschen" ;;
  esac
  case "$pfad" in
  /tmp/*) ;;
  *.py | *.php | *.ts | *.tsx | *.js | *.mjs | *.rs | *.vue | *.sh)
    hinzu entwicklung "TDD mit Test vor dem Code, Verhalten testen, Python nur mit uv" ;;
  esac
  case "$pfad" in */languages/*.po) hinzu wp-plugin-ch "Übersetzungen de_DE, de_CH, fr_FR, it_IT der WordPress-Plugins" ;; esac
  case "$pfad" in */find-jobs/akquise/*) hinzu akquise-direkt "Kundenfakten, Preise und «Rechte am Code»" ;; esac
  [ "$name" = versand.md ] && hinzu akquise-direkt "Kundenfakten, Preise und «Rechte am Code»"
  done <<<"$pfade"
  ;;
mcp__claude-in-chrome__* | mcp__cua_repl__*)
  bevor="im Browser weitergearbeitet wird"
  hinzu browser-wahl "API oder playwright-cli vor Claude in Chrome, Login und Tab-Regeln"
  urls=$(feld .tool_input.url)
  if [[ $werkzeug == mcp__cua_repl__* ]]; then
    urls=$(feld .tool_input.code | grep -oE 'https?://[^" '\''<>)]+' || true)
  fi
  for url in $urls; do
  host=$url
  [[ $host == *://* ]] && host=${host#*://}
  host=${host%%[/?#]*}
  host=${host##*@}
  host=${host%%:*}
  host=${host,,}
  am() { [ -n "$host" ] && grep -qE "$1" <<<"$host"; }
  am '(^|\.)linkedin\.com$' && hinzu linkedin "Such-URLs, Easy Apply und Fallen auf LinkedIn"
  am '(^|\.)upwork\.com$' && hinzu upwork "Jobsuche, Connects und Proposals auf Upwork"
  am '(^|\.)freelancermap\.de$' && hinzu freelancermap "Postfach, Formularbewerbung und Monatskontingent auf freelancermap"
  am '(^|\.)freelance\.de$' && hinzu freelance-de "Projektliste, Bewerbungsformular und Doppelbewerbung auf freelance.de"
  am '(^|\.)(gulp\.de|freelancer\.com|himalayas\.app|wellfound\.com)$|(^|\.)malt\.' &&
    hinzu portale-gulp-freelancer-himalayas "Bewerbung und Profilpflege auf GULP, Freelancer.com, Himalayas, Malt, Wellfound"
  am '(^|\.)(greenhouse\.io|ashbyhq\.com|lever\.co|join\.com)$|personio|teamtailor|recruitee' &&
    hinzu ats-formulare "feste Formularangaben (Gehalt, Kündigungsfrist, Adresse) und Belege mit Links"
  am 'myfactory' && hinzu myfactory "SOAP-Zugang, Oberfläche und Testdaten bei myfactory-Kunden"
  am '(^|\.)wordpress\.org$' && hinzu wp-plugin-ch "Plugin-Verzeichnis, Prüfung und Übersetzungen auf wordpress.org"
  am '^wordpress[a-z]*\.slack\.com$' && hinzu wp-plugin-ch "Übersetzungsregeln der WordPress-Teams (fr-richtlinien.md) vor jeder Nachricht dort"
  done
  ;;
esac

if [ "$ereignis" = UserPromptSubmit ]; then
  bevor="du antwortest"
  prompt=$(feld .prompt)
  # Meldungen fertiger Hintergrund-Agenten kommen auch als Prompt an, sind aber nicht von Goran
  grep -qE '<task-notification>|<agent-message' <<<"$prompt" && exit 0
  wort() { grep -qiwE "$1" <<<"$prompt"; }
  wort 'mail|mails|e-mail|e-mails|eingänge|antworten|postfach' &&
    hinzu nachhalten "alle Postfächer samt Spam und Gesendet, Freund-Feind-Check, Zuordnung zum Fach-Skill"
  wort 'lauf|such jobs' && hinzu laptop-lauf "Reihenfolge und Schritte des Akquise-Laufs"
  wort 'übersetz[[:alpha:]]*|traductions?|polyglots?|pte' &&
    hinzu wp-plugin-ch "Übersetzungen der Plugins, Regeln der Polyglots-Teams (fr-richtlinien.md) und PTE"
  wort 'screenshot' && hinzu screenshots "tmux2png oder gui-screenshot unter GNOME Wayland"
  wort 'steuer|mwst|bank|preis|vertrag|recht' && hinzu schweiz "Schweizer Recht und CHF, nicht deutsches oder EU-Recht"
fi

[ ${#skills[@]} -gt 0 ] || [ -n "${zusatz:-}" ] || exit 0
text=""
[ -z "$(feld .turn_id)" ] || zusatz="${zusatz:+Text und Freigaberegeln aus dem Skill arbeitsweise vor dem Versand prüfen.}"
[ -n "${zusatz:-}" ] && text+="$zusatz"$'\n'
for i in "${!skills[@]}"; do
  if [ -n "$(feld .turn_id)" ] || [ "$werkzeug" = apply_patch ]; then
    text+="Skill ${skills[$i]} laden (SKILL.md lesen), bevor $bevor: ${gruende[$i]}"$'\n'
  else
    text+="Skill ${skills[$i]} laden (Skill-Tool), bevor $bevor: ${gruende[$i]}"$'\n'
  fi
done
jq -n --arg e "${ereignis:-PreToolUse}" --arg t "${text%$'\n'}" \
  '{hookSpecificOutput: {hookEventName: $e, additionalContext: $t}}'
