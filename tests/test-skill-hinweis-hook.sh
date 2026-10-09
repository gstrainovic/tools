#!/usr/bin/env bash
# Prüft hooks/skill-hinweis.sh: je Anlass (Bash-Befehl, bearbeitete Datei, Chrome-Seite, Prompt) kommt ein Hinweis
# «Skill <name> laden» als additionalContext, aber nur für Skills, die laut Transkript noch nicht geladen sind.
# Gültiges JSON, nie blockieren, mehrere Skills in einem Hinweis.
set -euo pipefail
cd "$(dirname "$0")/.."
hook=hooks/skill-hinweis.sh
fehler=0
tmp=$(mktemp -d)
trap 'chmod -R u+rw "$tmp"; rm -rf "$tmp"' EXIT
leer=$tmp/leer.jsonl
: >"$leer"

# Transkript, in dem die genannten Skills per Skill-Werkzeug geladen wurden (Format wie in echten Sitzungen)
transkript() {
  local f; f=$(mktemp "$tmp/t.XXXXXX")
  printf '{"type":"user","message":{"role":"user","content":"Erwähnt mailbox und \\"skill\\":\\"nachhalten\\" nur im Text"}}\n' >"$f"
  for s in "$@"; do
    printf '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"toolu_01","name":"Skill","input":{"skill":"%s"},"caller":{"type":"direct"}}]}}\n' "$s" >>"$f"
  done
  echo "$f"
}
bash_ein()   { jq -n --arg c "$1" --arg t "${2:-$leer}" '{hook_event_name:"PreToolUse",tool_name:"Bash",tool_input:{command:$c},transcript_path:$t}'; }
datei_ein()  { jq -n --arg p "$1" --arg t "${2:-$leer}" '{hook_event_name:"PreToolUse",tool_name:"Edit",tool_input:{file_path:$p},transcript_path:$t}'; }
chrome_ein() { jq -n --arg n "$1" --arg u "$2" --arg t "${3:-$leer}" '{hook_event_name:"PreToolUse",tool_name:("mcp__claude-in-chrome__"+$n),tool_input:(if $u=="" then {} else {url:$u} end),transcript_path:$t}'; }
prompt_ein() { jq -n --arg p "$1" --arg t "${2:-$leer}" '{hook_event_name:"UserPromptSubmit",prompt:$p,transcript_path:$t}'; }

# meldet NAME "erwartete Skills" "verbotene Skills" EINGABE [EREIGNIS]
meldet() {
  local name=$1 soll=$2 nicht=$3 ein=$4 ereignis=${5:-PreToolUse} aus ok=1 s
  aus=$(printf '%s' "$ein" | "$hook" 2>&1) || ok=0
  [ "$(printf '%s' "$aus" | jq -s 'length' 2>/dev/null)" = 1 ] || ok=0
  if [ $ok = 1 ]; then
    [ "$(jq -r .hookSpecificOutput.hookEventName <<<"$aus")" = "$ereignis" ] || ok=0
    [ "$(jq -r '.hookSpecificOutput.permissionDecision // .decision // "keine"' <<<"$aus")" = keine ] || ok=0
    local k; k=$(jq -r '.hookSpecificOutput.additionalContext // ""' <<<"$aus")
    for s in $soll; do grep -qF "Skill $s laden (Skill-Tool), bevor" <<<"$k" || ok=0; done
    for s in $nicht; do grep -qF "Skill $s laden" <<<"$k" && ok=0; done
  fi
  if [ $ok = 1 ]; then echo "ok   meldet: $name"; else echo "FAIL meldet: $name"; echo "     Ausgabe: $aus"; fehler=1; fi
}
still() {
  local aus rc=0; aus=$(printf '%s' "$2" | "$hook" 2>&1) || rc=$?
  if [ -z "$aus" ] && [ $rc = 0 ]; then echo "ok   still: $1"; else echo "FAIL still: $1"; echo "     Ausgabe: $aus"; fehler=1; fi
}

# A) Bash
meldet "mailbox send gmail" "mailbox" "akquise-direkt nachhalten" "$(bash_ein 'mailbox send gmail --to a@b.ch --subject "x" --body-file t.txt')"
for konto in strainovic strainovic-dev kmu-plugins ki-flows wartungsheft; do
  meldet "mailbox reply $konto" "mailbox akquise-direkt nachhalten" "" "$(bash_ein "mailbox reply $konto 42 --body-file antwort.txt")"
done
meldet "mailbox send Konto nach Optionen" "mailbox akquise-direkt nachhalten" "" "$(bash_ein 'mailbox.py send --to x@strainovic-it.ch kmu-plugins --body-file t.txt')"
meldet "mailbox list"        "nachhalten" "mailbox" "$(bash_ein 'mailbox list --unread')"
meldet "mailbox read"        "nachhalten" "" "$(bash_ein 'mailbox read strainovic 42')"
meldet "mailbox search"      "nachhalten" "" "$(bash_ein 'mailbox search gmail --from x')"
meldet "svn ci"              "wp-plugin-ch" "" "$(bash_ein 'cd svn/trunk && svn ci -m "Version 1.2"')"
meldet "svn-ci.sh"           "wp-plugin-ch" "" "$(bash_ein './svn-ci.sh 1.2.0')"
meldet "wp plugin check"     "wp-plugin-ch" "" "$(bash_ein 'docker compose exec wp wp plugin check uid-check')"
meldet "suche/jobs.py"       "stellenboersen-api" "" "$(bash_ein 'uv run suche/jobs.py --tage 1')"
meldet "karriereseiten.py"   "stellenboersen-api" "" "$(bash_ein 'cd suche && uv run karriereseiten.py')"
meldet "exa_inserate.py"     "stellenboersen-api" "" "$(bash_ein 'uv run suche/exa_inserate.py')"
meldet "suche/foren.py"      "foren" "" "$(bash_ein 'uv run suche/foren.py --ki')"
meldet "forum_antwort.py"    "foren" "" "$(bash_ein 'uv run suche/forum_antwort.py 12')"
meldet "zustellbarkeit.py"   "mail-versand" "" "$(bash_ein 'uv run akquise/zustellbarkeit.py')"
meldet "versandlimit.py"     "mail-versand" "" "$(bash_ein 'python3 akquise/versandlimit.py')"
meldet "postmaster.py"       "mail-versand" "" "$(bash_ein 'uv run postmaster.py')"
meldet "yt.py"               "produktvideos" "" "$(bash_ein 'uv run videos/yt.py upload a.mp4')"
meldet "heimarbeit.py"       "heimarbeit" "" "$(bash_ein 'uv run suche/heimarbeit.py')"
meldet "pgrep -f"            "arbeitsweise" "" "$(bash_ein 'pgrep -f jobs')"

# B) Edit|Write
for f in TODO.md todo.md AGENTS.md CLAUDE.md README.md SKILL.md; do
  meldet "Datei $f" "doku-pflege" "entwicklung" "$(datei_ein "/home/g/projects/x/$f")"
done
for e in py php ts tsx js mjs rs vue sh; do
  meldet "Endung .$e" "entwicklung" "doku-pflege" "$(datei_ein "/home/g/projects/x/src/datei.$e")"
done
meldet "languages/*.po"      "wp-plugin-ch" "entwicklung" "$(datei_ein /home/g/projects/zefix-uid-check/plugin/languages/uid-check-de_CH.po)"
meldet "find-jobs/akquise/"  "akquise-direkt" "" "$(datei_ein /home/g/projects/find-jobs/akquise/agenturen/liste.md)"
meldet "versand.md"          "akquise-direkt" "" "$(datei_ein /home/g/projects/wartungsplan/versand.md)"
meldet "Write wie Edit" "entwicklung" "" "$(jq -n --arg t "$leer" '{hook_event_name:"PreToolUse",tool_name:"Write",tool_input:{file_path:"/home/g/a.py",content:"x"},transcript_path:$t}')"

# C) Chrome
meldet "Chrome ohne URL"     "browser-wahl" "linkedin" "$(chrome_ein computer '')"
meldet "linkedin.com"        "browser-wahl linkedin" "" "$(chrome_ein navigate 'https://www.linkedin.com/jobs/search/?keywords=x')"
meldet "upwork.com"          "upwork" "" "$(chrome_ein navigate 'https://www.upwork.com/nx/find-work/')"
meldet "freelancermap.de"    "freelancermap" "freelance-de" "$(chrome_ein navigate 'https://www.freelancermap.de/projektboerse.html')"
meldet "freelance.de"        "freelance-de" "freelancermap" "$(chrome_ein navigate 'https://www.freelance.de/projekte')"
for u in https://www.gulp.de/ https://www.freelancer.com/jobs https://himalayas.app/jobs https://www.malt.ch/profile https://wellfound.com/jobs; do
  meldet "Portal $u" "portale-gulp-freelancer-himalayas" "" "$(chrome_ein navigate "$u")"
done
for u in https://job-boards.eu.greenhouse.io/firma/jobs/1 https://jobs.ashbyhq.com/firma https://jobs.lever.co/firma \
         https://firma.jobs.personio.de/job/1 https://join.com/companies/firma https://firma.teamtailor.com/jobs https://firma.recruitee.com/o/x; do
  meldet "ATS $u" "ats-formulare" "" "$(chrome_ein navigate "$u")"
done
meldet "myfactory"           "myfactory" "" "$(chrome_ein navigate 'https://kunde.myfactory-cloud.ch/')"
meldet "wordpress.org"       "wp-plugin-ch" "" "$(chrome_ein navigate 'https://wordpress.org/plugins/developers/')"

# D) UserPromptSubmit
for w in Mail mails E-Mail Eingänge antworten Postfach; do
  meldet "Prompt $w" "nachhalten" "" "$(prompt_ein "Prüf bitte die $w von heute")" UserPromptSubmit
done
meldet "Prompt Lauf"         "laptop-lauf" "" "$(prompt_ein 'Mach den Lauf')" UserPromptSubmit
meldet "Prompt such Jobs"    "laptop-lauf" "" "$(prompt_ein 'such Jobs')" UserPromptSubmit
meldet "Prompt Screenshot"   "screenshots" "" "$(prompt_ein 'Schau dir den Screenshot an')" UserPromptSubmit
for w in Steuer MWST Bank Preis Vertrag Recht; do
  meldet "Prompt $w" "schweiz" "" "$(prompt_ein "Frage zu $w und so")" UserPromptSubmit
done
meldet "Prompt mehrere Skills" "nachhalten schweiz screenshots" "" "$(prompt_ein 'Screenshot der Mail zum Vertrag')" UserPromptSubmit

# Transkript: geladen, fehlt, unlesbar
t=$(transkript mailbox)
meldet "nur fehlende Skills" "akquise-direkt nachhalten" "mailbox" "$(bash_ein 'mailbox send strainovic --body-file t.txt' "$t")"
meldet "Transkript fehlt" "mailbox" "" "$(bash_ein 'mailbox send gmail' "$tmp/gibt-es-nicht.jsonl")"
unlesbar=$(transkript mailbox); chmod 000 "$unlesbar"
meldet "Transkript unlesbar" "mailbox" "" "$(bash_ein 'mailbox send gmail' "$unlesbar")"
meldet "ohne transcript_path" "mailbox" "" "$(jq -n '{hook_event_name:"PreToolUse",tool_name:"Bash",tool_input:{command:"mailbox send gmail"}}')"

still "mailbox schon geladen" "$(bash_ein 'mailbox send gmail --body-file t.txt' "$(transkript mailbox)")"
still "alle drei schon geladen" "$(bash_ein 'mailbox reply strainovic 4' "$(transkript mailbox akquise-direkt nachhalten)")"
still "nur im Text erwähnt zählt nicht als geladen, aber Skill geladen" "$(prompt_ein 'mail' "$(transkript nachhalten)")"
still "doku-pflege geladen" "$(datei_ein /home/g/projects/x/AGENTS.md "$(transkript doku-pflege)")"
still "browser-wahl und linkedin geladen" "$(chrome_ein navigate https://www.linkedin.com/feed/ "$(transkript browser-wahl linkedin)")"
still "unpassender Befehl" "$(bash_ein 'git status --short')"
still "Commit-Nachricht mit mailbox send" "$(bash_ein 'git commit -q -m "mailbox send strainovic und pgrep -f erklärt"')"
still "Heredoc mit mailbox send" "$(bash_ein "git commit -F - <<'EOF'
mailbox send strainovic
EOF")"
still "Skript unter /tmp" "$(datei_ein /tmp/claude-1000/x/scratchpad/probe.py)"
still "gewöhnliche Datei" "$(datei_ein /home/g/projects/x/notizen.txt)"
still "browser-wahl geladen, fremde Domain" "$(chrome_ein navigate https://example.com/ "$(transkript browser-wahl)")"
still "Prompt ohne Anlass" "$(prompt_ein 'Bau den Hook fertig')"
still "Teilwort zählt nicht" "$(prompt_ein 'Rechtschreibung und Bankett, Mailand')"
still "unbekanntes Werkzeug" "$(jq -n '{hook_event_name:"PreToolUse",tool_name:"Read",tool_input:{file_path:"/home/g/AGENTS.md"}}')"

exit $fehler
