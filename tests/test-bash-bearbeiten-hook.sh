#!/usr/bin/env bash
# Prüft hooks/bash-bearbeiten.sh: Bash-Befehle, die Dateien per sed -i, perl -i, Python-Heredoc oder cat/tee
# schreiben, bekommen einen Hinweis «Edit/Write statt Bash»; Lesen, Scratchpad (/tmp) und /dev/null bleiben still.
set -euo pipefail
cd "$(dirname "$0")/.."
hook=hooks/bash-bearbeiten.sh
fehler=0

lauf() { jq -n --arg c "$1" '{tool_name:"Bash",tool_input:{command:$c}}' | "$hook"; }
meldet() {
  local aus; aus=$(lauf "$2")
  if [ -n "$aus" ] && echo "$aus" | jq -e '.hookSpecificOutput.additionalContext | test("Edit")' >/dev/null \
     && [ "$(echo "$aus" | jq -r '.hookSpecificOutput.permissionDecision // "keine"')" = keine ]; then
    echo "ok   meldet: $1"; else echo "FAIL meldet: $1"; fehler=1; fi
}
still() {
  if [ -z "$(lauf "$2")" ]; then echo "ok   still: $1"; else echo "FAIL still: $1"; fehler=1; fi
}

meldet "sed -i"            "sed -i 's/a/b/' TODO.md"
meldet "perl -pi"          "perl -pi -e 's/a/b/' src/x.php"
meldet "python3 heredoc"   "python3 - datei.po <<'EOF'
open(p,'w').write(t)
EOF"
meldet "cat heredoc"       "cat > notiz.md <<'EOF'
text
EOF"
meldet "tee in Repo-Datei" "echo x | tee AGENTS.md"

still "sed -n lesen"       "sed -n 1,20p TODO.md"
still "Scratchpad"         "cat > /tmp/claude-1000/x/scratchpad/a.txt <<'EOF'
a
EOF"
still "dev null"           "git log > /dev/null"
still "gewöhnlicher Befehl" "git status --short"
still "Text in Anführungszeichen" "git commit -q -m \"Hinweis statt sed -i, python3 - und > AGENTS.md\" && echo 'a > b'"

exit $fehler
