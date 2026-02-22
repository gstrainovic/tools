#!/bin/bash
# tests/test-img-preview.sh — Tests für img-preview
set -euo pipefail

PASS=0
FAIL=0
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/img-preview"

fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }

# Test 1: Script existiert und ist ausführbar
if [[ -x "$SCRIPT" ]]; then
    pass "script is executable"
else
    fail "script is not executable at $SCRIPT"
fi

# Test 2: Ohne Argument → Exit-Code != 0 + Usage
OUTPUT=$("$SCRIPT" 2>&1 || true)
if echo "$OUTPUT" | grep -qi "usage\|error\|missing"; then
    pass "no args shows usage/error"
else
    fail "no args should show usage/error, got: $OUTPUT"
fi

# Test 3: Nicht-existente Datei → Exit-Code != 0
if "$SCRIPT" /tmp/nonexistent-file-12345.png 2>/dev/null; then
    fail "nonexistent file should fail"
else
    pass "nonexistent file fails"
fi

# Test 4: Unterstützte Extensions erkennen (--dry-run)
for ext in png jpg jpeg gif webp bmp tiff avif pdf; do
    touch "/tmp/test-img-preview.$ext"
    OUTPUT=$("$SCRIPT" --dry-run "/tmp/test-img-preview.$ext" 2>&1 || true)
    if echo "$OUTPUT" | grep -q "imgcat\|pdftoppm"; then
        pass "recognizes .$ext"
    else
        fail "does not recognize .$ext, got: $OUTPUT"
    fi
    rm -f "/tmp/test-img-preview.$ext"
done

# Test 5: Unbekannte Extension → Fallback zu imgcat
touch /tmp/test-img-preview.xyz
OUTPUT=$("$SCRIPT" --dry-run /tmp/test-img-preview.xyz 2>&1 || true)
if echo "$OUTPUT" | grep -q "imgcat"; then
    pass "unknown ext falls back to imgcat"
else
    fail "unknown ext should fall back to imgcat, got: $OUTPUT"
fi
rm -f /tmp/test-img-preview.xyz

# Test 6: PDF braucht pdftoppm
touch /tmp/test-img-preview-dummy.pdf
OUTPUT=$("$SCRIPT" --dry-run /tmp/test-img-preview-dummy.pdf 2>&1 || true)
if echo "$OUTPUT" | grep -q "pdftoppm"; then
    pass "pdf uses pdftoppm"
else
    fail "pdf should use pdftoppm, got: $OUTPUT"
fi
rm -f /tmp/test-img-preview-dummy.pdf

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
