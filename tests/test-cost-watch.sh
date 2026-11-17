#!/bin/bash
# tests/test-cost-watch.sh — Alarm-Mail des Kostenwächters, auch wo Git-Bash sein curl nicht ausführen darf
# (Windows-Firmen-PC: «Permission denied», Exit 126). Dann nimmt das Skript curl.exe von Windows (WINDOWS_CURL).
# Läuft gegen Attrappen für openstack und curl.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
pruefe() { if eval "$2"; then pass "$1"; else fail "$1"; fi; }

mkdir -p "$TMP/bin" "$TMP/home/.config/resend"
echo geheim > "$TMP/home/.config/resend/token"
printf '#!/bin/bash\n[[ "$*" == *"-f value"* ]] && exit 0\necho "[]"\n' > "$TMP/bin/openstack"
printf '#!/bin/bash\necho "windows $*" >> "%s/log"\n' "$TMP" > "$TMP/windows-curl"
chmod +x "$TMP/bin/openstack" "$TMP/windows-curl"

lauf() {
  HOME="$TMP/home" PATH="$TMP/bin:$PATH" WINDOWS_CURL="$TMP/windows-curl" \
    bash "$ROOT/wartungsheft-cost-watch.sh" --force > "$TMP/aus" 2>&1
}

# Fall 1: curl gesperrt wie in Git-Bash auf dem Firmen-PC
printf '#!/bin/bash\necho "bash: curl: Permission denied" >&2\nexit 126\n' > "$TMP/bin/curl"; chmod +x "$TMP/bin/curl"
rm -f "$TMP/log"; lauf; rc=$?
pruefe "gesperrtes curl: Lauf endet mit 0 ($rc)" '[ "$rc" -eq 0 ]'
pruefe "gesperrtes curl: Mail über curl.exe von Windows" 'grep -q "windows .*api.resend.com/emails" "$TMP/log" 2>/dev/null'
pruefe "gesperrtes curl: meldet gesendet" 'grep -q "Alarm-Mail gesendet" "$TMP/aus"'

# Fall 2: curl läuft (Linux): Windows-curl bleibt unberührt
printf '#!/bin/bash\n[ "$1" = --version ] && exit 0\necho "linux $*" >> "%s/log"\n' "$TMP" > "$TMP/bin/curl"
rm -f "$TMP/log"; lauf; rc=$?
pruefe "curl erlaubt: Mail über curl" 'grep -q "linux .*api.resend.com/emails" "$TMP/log"'
pruefe "curl erlaubt: Windows-curl nicht benutzt" '! grep -q "^windows" "$TMP/log"'

echo "$PASS bestanden, $FAIL fehlgeschlagen"
[ "$FAIL" -eq 0 ]
