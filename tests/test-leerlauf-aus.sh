#!/bin/bash
# tests/test-leerlauf-aus.sh — Dev-Instanz schaltet sich nach Leerlauf ab, nie während einer SSH-Verbindung
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }

# Attrappen: ss liefert Verbindungen aus $TMP/ss, «ausschalten» schreibt nur eine Datei
cat > "$TMP/ss" <<'EOF'
#!/bin/bash
cat "$(dirname "$0")/verbindungen" 2>/dev/null
EOF
cat > "$TMP/aus" <<'EOF'
#!/bin/bash
touch "$(dirname "$0")/ausgeschaltet"
EOF
chmod +x "$TMP/ss" "$TMP/aus"
lauf() { STAMP="$TMP/aktiv" SS_CMD="$TMP/ss" AUS_CMD="$TMP/aus" LEERLAUF_MINUTEN=120 "$ROOT/leerlauf-aus.sh" >/dev/null; }

# 1: erster Lauf ohne Stempel legt ihn an und schaltet nicht ab
lauf
[[ -f "$TMP/aktiv" && ! -f "$TMP/ausgeschaltet" ]] && pass "erster Lauf legt Stempel an" || fail "erster Lauf"

# 2: Stempel alt, aber SSH-Verbindung offen: Stempel erneuert, nicht abgeschaltet
touch -d '-3 hours' "$TMP/aktiv"
echo "ESTAB 0 0 195.15.207.253:22 1.2.3.4:5555" > "$TMP/verbindungen"
lauf
[[ ! -f "$TMP/ausgeschaltet" && -z "$(find "$TMP/aktiv" -mmin +5)" ]] && pass "offene Verbindung hält wach" || fail "offene Verbindung"

# 3: keine Verbindung, Stempel jünger als 120 Minuten: bleibt an
rm -f "$TMP/verbindungen"; touch -d '-60 minutes' "$TMP/aktiv"
lauf
[[ ! -f "$TMP/ausgeschaltet" ]] && pass "kurzer Leerlauf bleibt an" || fail "kurzer Leerlauf"

# 4: keine Verbindung, Stempel älter als 120 Minuten: abschalten
touch -d '-121 minutes' "$TMP/aktiv"
lauf
[[ -f "$TMP/ausgeschaltet" ]] && pass "langer Leerlauf schaltet ab" || fail "langer Leerlauf"

echo "$PASS bestanden, $FAIL fehlgeschlagen"
[[ $FAIL -eq 0 ]]
