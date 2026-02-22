# yazi/nvim Cleanup & Bild-Viewer — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Alle buggy yazi↔nvim Hacks entfernen und durch ein einfaches, isoliert testbares img-preview Script ersetzen.

**Architecture:** Nvim BufReadCmd erkennt Bild/PDF → spawnt `wezterm cli split-pane --left` mit `img-preview` Script → imgcat zeigt Bild → any key schließt Pane. Kein yazi involviert, kein State.

**Tech Stack:** Bash (img-preview), Lua (nvim-Plugin), WezTerm CLI, pdftoppm

**Design-Doc:** `docs/plans/2026-02-22-yazi-nvim-cleanup-design.md`

---

## Task 1: Cleanup — Alte Plugins und Scripts entfernen

**Files:**
- Delete: `.config/yazi/plugins/preview-force-max.yazi/`
- Delete: `.config/yazi/plugins/toggle-pane.yazi/`
- Modify: `.config/yazi/keymap.toml` (ESC-Binding entfernen)
- Modify: `.config/yazi/yazi.toml` (opener ändern)
- Delete: `ide`
- Delete: `nvim-ide-open`

**Step 1: Entfernen**

```bash
rm -rf .config/yazi/plugins/preview-force-max.yazi
rm -rf .config/yazi/plugins/toggle-pane.yazi
rm ide nvim-ide-open
```

**Step 2: keymap.toml — ESC-Binding entfernen**

In `.config/yazi/keymap.toml`, diese Zeile entfernen:
```toml
    { on = "<Esc>", run = ["plugin preview-force-max -- reset", "escape"], desc = "Reset to 2-panel / Escape" },
```

**Step 3: yazi.toml — opener auf nvim ändern**

In `.config/yazi/yazi.toml`, den opener ändern:
```toml
# Vorher:
edit = [
    { run = "nvim-ide-open %s", block = true, for = "unix" },
]

# Nachher:
edit = [
    { run = "nvim %s", block = true, for = "unix" },
]
```

**Step 4: Verifizieren dass yazi noch startet**

```bash
# yazi kurz starten und prüfen dass keine Fehler kommen
timeout 2 yazi --client-id 9999 /tmp 2>&1 || true
# Keine Lua-Errors = OK
```

**Step 5: Commit**

```bash
git add -A
git commit -m "cleanup: entferne alle yazi↔nvim Hacks (preview-force-max, toggle-pane, ide, nvim-ide-open)"
```

---

## Task 2: img-preview Script — Test schreiben

**Files:**
- Create: `tests/test-img-preview.sh`

**Step 1: Test-Script schreiben**

```bash
#!/bin/bash
# tests/test-img-preview.sh — Tests für img-preview
# Ausführung: bash tests/test-img-preview.sh
set -euo pipefail

PASS=0
FAIL=0
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/img-preview"

fail() { echo "FAIL: $1"; ((FAIL++)); }
pass() { echo "PASS: $1"; ((PASS++)); }

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

# Test 4: Unterstützte Extensions erkennen (Unit-Test der Extension-Logik)
# Wir testen das mit --dry-run Flag (zeigt was es tun würde, ohne imgcat)
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

# Test 5: Unbekannte Extension → Fallback zu imgcat (nicht crashen)
touch /tmp/test-img-preview.xyz
OUTPUT=$("$SCRIPT" --dry-run /tmp/test-img-preview.xyz 2>&1 || true)
if echo "$OUTPUT" | grep -q "imgcat"; then
    pass "unknown ext falls back to imgcat"
else
    fail "unknown ext should fall back to imgcat, got: $OUTPUT"
fi
rm -f /tmp/test-img-preview.xyz

# Test 6: PDF braucht pdftoppm
OUTPUT=$("$SCRIPT" --dry-run /tmp/test-img-preview-dummy.pdf 2>&1 || true)
if echo "$OUTPUT" | grep -q "pdftoppm"; then
    pass "pdf uses pdftoppm"
else
    fail "pdf should use pdftoppm, got: $OUTPUT"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
```

**Step 2: Test ausführen — muss fehlschlagen (RED)**

```bash
bash tests/test-img-preview.sh
```

Expected: FAIL — `script is not executable` (img-preview existiert noch nicht)

**Step 3: Commit**

```bash
git add tests/test-img-preview.sh
git commit -m "test: add img-preview test suite (RED)"
```

---

## Task 3: img-preview Script — Implementierung (GREEN)

**Files:**
- Create: `img-preview`

**Step 1: Script schreiben**

```bash
#!/bin/bash
# img-preview — Bild/PDF im Terminal anzeigen via wezterm imgcat
# Usage: img-preview [--dry-run] FILE
set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    shift
fi

FILE="${1:-}"

if [[ -z "$FILE" ]]; then
    echo "Usage: img-preview [--dry-run] FILE" >&2
    exit 1
fi

if [[ ! -f "$FILE" ]] && [[ "$DRY_RUN" == false ]]; then
    echo "Error: file not found: $FILE" >&2
    exit 1
fi

EXT="${FILE##*.}"
EXT="${EXT,,}"

case "$EXT" in
    pdf)
        if [[ "$DRY_RUN" == true ]]; then
            echo "pdftoppm + imgcat: $FILE"
            exit 0
        fi
        TMP=$(mktemp /tmp/img-preview-XXXXX.png)
        trap 'rm -f "$TMP"' EXIT
        pdftoppm -png -f 1 -l 1 -singlefile "$FILE" "${TMP%.png}"
        wezterm imgcat "$TMP"
        ;;
    *)
        if [[ "$DRY_RUN" == true ]]; then
            echo "imgcat: $FILE"
            exit 0
        fi
        wezterm imgcat "$FILE"
        ;;
esac

read -n 1 -s -r
```

**Step 2: Ausführbar machen**

```bash
chmod +x img-preview
```

**Step 3: Tests ausführen — müssen alle passen (GREEN)**

```bash
bash tests/test-img-preview.sh
```

Expected: Alle PASS, 0 FAIL

**Step 4: Manueller Smoke-Test mit echtem Bild**

```bash
# Ein Test-Bild finden oder erzeugen
convert -size 100x100 xc:red /tmp/test-red.png 2>/dev/null || \
    printf '\x89PNG\r\n\x1a\n' > /tmp/test-red.png

# Dry-Run
./img-preview --dry-run /tmp/test-red.png
# Expected output: "imgcat: /tmp/test-red.png"
```

**Step 5: Commit**

```bash
git add img-preview
git commit -m "feat: add img-preview script for terminal image display"
```

---

## Task 4: image-viewer.lua — Test schreiben

**Files:**
- Create: `tests/test-image-viewer.lua`

Da nvim-Plugins schwer isoliert testbar sind, schreiben wir einen nvim-headless Test:

**Step 1: Test-Script schreiben**

```bash
#!/bin/bash
# tests/test-image-viewer.sh — Tests für image-viewer.lua nvim-Plugin
# Testet: BufReadCmd autocmd registriert, Binary-Buffer wird gelöscht
set -euo pipefail

PASS=0
FAIL=0

fail() { echo "FAIL: $1"; ((FAIL++)); }
pass() { echo "PASS: $1"; ((PASS++)); }

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
```

**Step 2: Test ausführen — muss fehlschlagen (RED)**

```bash
bash tests/test-image-viewer.sh
```

Expected: FAIL — entweder Plugin hat noch alte ya-emit-Referenzen oder ist noch das alte Plugin

**Step 3: Commit**

```bash
git add tests/test-image-viewer.sh
git commit -m "test: add image-viewer.lua test suite (RED)"
```

---

## Task 5: image-viewer.lua — Implementierung (GREEN)

**Files:**
- Modify: `~/.config/nvim/lua/plugins/image-viewer.lua`

**Step 1: Plugin neu schreiben**

```lua
-- image-viewer.lua — Bild/PDF im WezTerm-Split anzeigen via img-preview
-- Kein yazi, kein State, kein ya emit-to

local binary_extensions = {
  "png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff", "tif", "avif",
  "pdf",
}

local pattern = table.concat(
  vim.tbl_map(function(ext)
    return "*." .. ext
  end, binary_extensions),
  ","
)

vim.api.nvim_create_autocmd("BufReadCmd", {
  pattern = pattern,
  callback = function(ev)
    local filepath = vim.fn.fnamemodify(ev.file, ":p")
    local buf = ev.buf

    -- img-preview im linken WezTerm-Split öffnen
    local cmd = string.format(
      "wezterm cli split-pane --left --percent 50 -- img-preview %s",
      vim.fn.shellescape(filepath)
    )
    vim.fn.system(cmd)

    -- Binary-Buffer löschen
    vim.schedule(function()
      if vim.api.nvim_buf_is_valid(buf) then
        vim.api.nvim_buf_delete(buf, { force = true })
      end
    end)
  end,
})

return {}
```

**Step 2: Tests ausführen — müssen alle passen (GREEN)**

```bash
bash tests/test-image-viewer.sh
```

Expected: Alle PASS, 0 FAIL

**Step 3: Commit**

```bash
git add ~/.config/nvim/lua/plugins/image-viewer.lua
git commit -m "feat: rewrite image-viewer.lua — wezterm split-pane statt yazi-hack"
```

---

## Task 6: Integration Test — Manuell in WezTerm

**Dies ist ein manueller Test der nicht automatisiert werden kann (erfordert WezTerm GUI).**

**Step 1: Test-Bild erzeugen**

```bash
convert -size 200x200 xc:blue /tmp/test-blue.png
```

**Step 2: img-preview standalone testen**

```bash
# In WezTerm:
./img-preview /tmp/test-blue.png
# Expected: Blaues Bild wird angezeigt, wartet auf Tastendruck
# Drücke eine Taste → Terminal kehrt zurück
```

**Step 3: nvim → Bild öffnen**

```bash
nvim /tmp/test-blue.png
# Expected: Links 50% zeigt blaues Bild, rechts nvim
# Tastendruck im Bild-Pane → Pane schließt, nvim bleibt
```

**Step 4: PDF testen**

```bash
# PDF finden oder erzeugen
convert -size 200x200 xc:green /tmp/test.pdf 2>/dev/null || echo "skip pdf test"
nvim /tmp/test.pdf
# Expected: Links 50% zeigt PDF erste Seite, rechts nvim
```

**Step 5: yazi standalone testen**

```bash
yazi /tmp
# Expected: Startet normal, keine Lua-Errors
# Dateien öffnen mit Enter → nvim öffnet (nicht nvim-ide-open)
```

**Step 6: Ergebnis dokumentieren**

Jeden Test-Schritt mit Output dokumentieren bevor "fertig" gemeldet wird.

---

## Task 7: Cleanup — CLAUDE.md und Memory aktualisieren

**Files:**
- Modify: `~/tools/CLAUDE.md`
- Modify: `~/.claude/CLAUDE.md`

**Step 1: ~/tools/CLAUDE.md**

Entfernen/Aktualisieren:
- `ide` und `nvim-ide-open` aus der Datei-Tabelle entfernen
- IDE-Modus Sektion entfernen (kein yazi+nvim Split mehr)
- `img-preview` in die Datei-Tabelle aufnehmen

**Step 2: ~/.claude/CLAUDE.md**

Entfernen/Aktualisieren:
- Yazi Debugging Sektion: `nvim-ide-open` Referenzen entfernen
- Veraltete `--args=ARG` Referenzen bereinigen

**Step 3: Commit**

```bash
git add ~/tools/CLAUDE.md
git commit -m "docs: update CLAUDE.md — entferne ide/nvim-ide-open, füge img-preview hinzu"
```

---

## Task 8: Finale Verifikation

**PFLICHT: Vor jeder Fertigmeldung.**

Checkliste — jeder Punkt muss mit Output belegt sein:

- [ ] `bash tests/test-img-preview.sh` → alle PASS
- [ ] `bash tests/test-image-viewer.sh` → alle PASS
- [ ] `git status` → clean working tree
- [ ] `git log --oneline -10` → alle Commits vorhanden
- [ ] yazi startet ohne Errors
- [ ] Keine Referenzen mehr zu: preview-force-max, toggle-pane, nvim-ide-open, ide, ya emit-to
  ```bash
  grep -r "preview-force-max\|toggle-pane\|nvim-ide-open\|ya.*emit" \
    .config/yazi/ ~/.config/nvim/lua/plugins/image-viewer.lua 2>/dev/null
  ```
  Expected: keine Treffer
