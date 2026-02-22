#!/bin/bash
# tests/test-image-viewer.sh — Tests für image-viewer.lua nvim-Plugin
set -euo pipefail

PASS=0
FAIL=0

fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }

PLUGIN="$HOME/.config/nvim/lua/plugins/image-viewer.lua"

# Test 1: Plugin-Datei existiert
if [[ -f "$PLUGIN" ]]; then
    pass "plugin file exists"
else
    fail "plugin file not found at $PLUGIN"
fi

# Test 2: Plugin hat BufReadCmd autocmd Pattern
if grep -q "BufReadCmd" "$PLUGIN"; then
    pass "has BufReadCmd autocmd"
else
    fail "missing BufReadCmd autocmd"
fi

# Test 3: Plugin referenziert img-preview
if grep -q "img-preview" "$PLUGIN"; then
    pass "references img-preview"
else
    fail "should reference img-preview"
fi

# Test 4: Plugin nutzt wezterm cli split-pane
if grep -q "split-pane" "$PLUGIN"; then
    pass "uses wezterm split-pane"
else
    fail "should use wezterm split-pane"
fi

# Test 5: Plugin hat KEINE ya emit-to Referenzen
if grep -q "ya.*emit" "$PLUGIN"; then
    fail "should not reference ya emit-to"
else
    pass "no ya emit-to references"
fi

# Test 6: Plugin hat KEINE preview-force-max Referenzen
if grep -q "preview-force-max" "$PLUGIN"; then
    fail "should not reference preview-force-max"
else
    pass "no preview-force-max references"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
