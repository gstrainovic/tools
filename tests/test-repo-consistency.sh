#!/bin/bash
# tests/test-repo-consistency.sh — Doku und Setup gegen den echten Repo-Inhalt pruefen
# Verhindert, dass CLAUDE.md/README.md/setup.sh auf geloeschte Tools verweisen.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0

fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }

DOCS=(CLAUDE.md README.md setup.sh tui-screenshot-skill.md tmux2png img-proto-test)

# Test 1: Keine Referenzen auf abgeschaffte Tools
for term in wezterm WezTerm yazi Yazi nvim neovim Neovim lazyvim LazyVim zed Zed; do
    HITS=""
    for doc in "${DOCS[@]}"; do
        [[ -f "$ROOT/$doc" ]] || continue
        if grep -qF -- "$term" "$ROOT/$doc"; then
            HITS="$HITS $doc"
        fi
    done
    if [[ -z "$HITS" ]]; then
        pass "keine Referenz auf '$term'"
    else
        fail "'$term' noch referenziert in:$HITS"
    fi
done

# Test 2: Jede in setup.sh kopierte Datei existiert auch
while read -r script; do
    if [[ -f "$ROOT/$script" ]]; then
        pass "setup.sh kopiert vorhandenes '$script'"
    else
        fail "setup.sh kopiert nicht existierendes '$script'"
    fi
done < <(grep -oP '(?<=\$SCRIPT_DIR/)[A-Za-z0-9._-]+' "$ROOT/setup.sh" | sort -u)

# Test 3: Jede in der CLAUDE.md-Dateitabelle genannte Datei existiert
while read -r entry; do
    if [[ -e "$ROOT/$entry" ]]; then
        pass "CLAUDE.md nennt vorhandenes '$entry'"
    else
        fail "CLAUDE.md nennt nicht existierendes '$entry'"
    fi
done < <(grep -oP '^\| `\K[^`]+' "$ROOT/CLAUDE.md" | sort -u)

# Test 4: Alle Shell-Scripts sind syntaktisch valide und ausfuehrbar
for f in "$ROOT"/*.sh "$ROOT"/tmux2png "$ROOT"/img-proto-test "$ROOT"/tests/*.sh; do
    [[ -f "$f" ]] || continue
    name="$(basename "$f")"
    if bash -n "$f" 2>/dev/null; then
        pass "$name: Syntax ok"
    else
        fail "$name: Syntax-Fehler"
    fi
    if [[ -x "$f" ]]; then
        pass "$name: ausfuehrbar"
    else
        fail "$name: nicht ausfuehrbar"
    fi
done

echo ""
echo "$PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
