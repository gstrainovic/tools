# Yazi Preview-Fullscreen Debug Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix automatic preview fullscreen trigger when nvim sends `ya emit-to reveal` for images

**Architecture:** The plugin needs to hook into yazi's event system to watch for file hover changes, not just respond to key presses. Current implementation only has `entry` (keymap-triggered), needs persistent watcher or event hook.

**Tech Stack:** Yazi Lua plugins, yazi DDS (ya emit-to), WezTerm, tmux2png for visual verification

**Verification Method:** Take WezTerm screenshots before/after each layout change to visually confirm the 2-column → fullscreen toggle works.

---

### Task 1: Add debug logging to preview-fullscreen plugin

**Files:**
- Modify: `~/tools/.config/yazi/plugins/preview-fullscreen.yazi/main.lua`

**Step 1: Add debug output to entry function**

Replace current plugin with version that logs:

```lua
-- preview-fullscreen.yazi — Toggle preview fullscreen for images/PDFs

return {
  entry = function(self, job)
    ya.dbg("preview-fullscreen: entry called")

    -- Get current manager state synchronously
    local hovered = ya.sync(function()
      return cx.manager.hovered
    end)

    if not hovered then
      ya.dbg("preview-fullscreen: no hovered file")
      return
    end

    ya.dbg("preview-fullscreen: hovered=" .. tostring(hovered.url))

    -- Check if hovered file is a preview type
    local path = tostring(hovered.url)
    local ext = path:match("%.([^%.]+)$")
    if ext then
      ext = ext:lower()
      ya.dbg("preview-fullscreen: ext=" .. ext)

      local is_preview = ext == "png" or ext == "jpg" or ext == "jpeg" or
                         ext == "gif" or ext == "webp" or ext == "bmp" or
                         ext == "tiff" or ext == "tif" or ext == "avif" or
                         ext == "pdf"

      if is_preview then
        ya.dbg("preview-fullscreen: toggling to fullscreen")
        ya.manager_emit("resize", { 0, 0, 1 })
      else
        ya.dbg("preview-fullscreen: not a preview type, restoring layout")
        ya.manager_emit("resize", { 0, 3, 4 })
      end
    else
      ya.dbg("preview-fullscreen: no extension found")
    end
  end,
}
```

**Step 2: Commit changes**

```bash
cd ~/tools
git add .config/yazi/plugins/preview-fullscreen.yazi/main.lua
git commit -m "debug: add logging to preview-fullscreen plugin"
```

Expected: Commit succeeds.

---

### Task 2: Manual Ctrl+P test with screenshot verification

**Files:**
- Test in terminal (no files to modify)

**Step 1: Start ide layout in new WezTerm window**

```bash
wezterm start --cwd ~/Pictures -- bash -c "ide ~/Pictures"
```

Wait ~3 seconds for nvim + yazi to load.

**Step 2: Screenshot BEFORE (normal 2-column layout)**

```bash
tmux2png > /tmp/before-normal.png
```

Verify output:
```bash
file /tmp/before-normal.png
# Expected: PNG image data
```

**Step 3: Visually inspect screenshot**

```bash
# In Claude Code:
Read /tmp/before-normal.png
```

Expected: See yazi on left (~30%), preview on right (~70%), both visible side-by-side.

**Step 4: In yazi, navigate to an image file**

In the running yazi (left pane):
- Press `j` or `↓` to move down
- Find a `.png` or `.jpg` file

Screenshot the current state:
```bash
tmux2png > /tmp/before-image-selected.png
```

**Step 5: Press Ctrl+P to toggle fullscreen**

In yazi pane, press `Ctrl+P`.

Wait 0.5 seconds.

**Step 6: Screenshot AFTER (should be fullscreen preview)**

```bash
tmux2png > /tmp/after-fullscreen.png
```

Verify:
```bash
file /tmp/after-fullscreen.png
```

**Step 7: Visually inspect fullscreen screenshot**

```bash
# In Claude Code:
Read /tmp/after-fullscreen.png
```

Expected: Yazi left pane should be gone or minimized (ratio [0,0,1] means only preview). Preview image takes ~100% of space.

**Step 8: Check yazi logs for debug output**

```bash
cat ~/.local/state/yazi/logs/yazi.log 2>/dev/null | grep preview-fullscreen | tail -10
```

Expected output (or similar):
```
preview-fullscreen: entry called
preview-fullscreen: hovered=/path/to/image.png
preview-fullscreen: ext=png
preview-fullscreen: toggling to fullscreen
```

**Verification Result:**
- ✅ Screenshots show layout change (2-col → fullscreen)
- ✅ Logs show "entry called" + "toggling to fullscreen"
- ✅ **PASS** — Manual Ctrl+P works

**OR:**

- ❌ Screenshots show NO layout change (still 2-col)
- ❌ Logs missing or empty
- ❌ **FAIL** — Investigate: `ya.manager_emit` not working?

**Step 9: Commit observation**

```bash
git add /tmp/before-*.png /tmp/after-*.png
git commit -m "test: verify Ctrl+P manual toggle works - add screenshots"
```

---

### Task 3: Test ya emit-to reveal with screenshot verification

**Files:**
- Test only (no code changes)

**Step 1: Keep ide running, screenshot current state**

In running WezTerm from Task 2:

```bash
tmux2png > /tmp/reveal-before.png
```

**Step 2: From separate terminal, send reveal command**

```bash
ya emit-to 1313 reveal --str /home/g/Bilder/Bildschirmfotos/test.png
```

(Replace with actual image path that exists in your system)

**Step 3: Wait 1 second and screenshot yazi**

```bash
sleep 1
tmux2png > /tmp/reveal-after.png
```

**Step 4: Inspect before/after screenshots**

```bash
# In Claude Code:
Read /tmp/reveal-before.png
Read /tmp/reveal-after.png
```

Compare:
- **Before:** Which file was selected? What was the layout?
- **After:** Did yazi navigate to the image? Did preview fullscreen?

**Expected outcomes:**

**Case A: Works perfectly**
- `before`: Yazi in 2-column, some file selected
- `after`: Yazi still in 2-column layout, BUT different file (the image) is now selected/previewed
- **Result:** ❌ **Plugin didn't auto-trigger** — `reveal` navigated, but layout didn't change to fullscreen
- **Conclusion:** Plugin hook is not being called on `reveal` event

**Case B: Layout changed but wrong file**
- `after`: Preview fullscreen, but showing wrong image
- **Result:** ❌ Plugin is responding, but to wrong event

**Case C: No change at all**
- `before` == `after` (yazi didn't even navigate)
- **Result:** ❌ `ya emit-to reveal` isn't working correctly

---

### Task 4: Check yazi logs for reveal event

**Files:**
- Research only

**Step 1: Check full yazi logs**

```bash
cat ~/.local/state/yazi/logs/yazi.log 2>/dev/null | tail -50
```

Look for:
- Any error messages from `ya emit-to`
- Any plugin-related errors
- Messages about "reveal"

**Step 2: Search for preview-fullscreen entries**

```bash
cat ~/.local/state/yazi/logs/yazi.log 2>/dev/null | grep preview-fullscreen
```

Expected: If plugin has watcher, should see continuous entries like "entry called" or "no hovered file" every time hover changes.

**If empty:** Plugin is not being called automatically at all → needs different hook mechanism.

**Step 3: Document findings**

Write findings in commit message:
```bash
git commit --allow-empty -m "test: document reveal behavior and log findings

Log shows:
- ya emit-to reveal DID navigate yazi to image
- preview-fullscreen plugin NOT auto-triggered
- Manual Ctrl+P toggle DOES work
- Conclusion: Plugin needs event hook, not just entry point"
```

---

### Task 5: Research yazi event hooks

**Files:**
- Research only

**Step 1: Check if yazi has built-in event hooks for plugins**

Search in yazi docs / examples:
- Does yazi call `on_hover()` in plugins?
- Does yazi call `on_reveal()` in plugins?
- Does yazi have `watcher()` lifecycle?

**Step 2: Look for examples in official yazi plugins**

```bash
# Check if any plugins in ~/.config/yazi/plugins/ use non-entry hooks
ls -la ~/.config/yazi/plugins/*/main.lua

# Example: Check yafg.yazi for pattern
head -30 ~/.config/yazi/plugins/yafg.yazi/main.lua
```

**Step 3: Document findings**

If hooks exist: which ones? Document exact API.
If no auto-hooks: Will need polling or workaround.

---

### Task 6: Implement watcher hook (if available)

**Files:**
- Modify: `~/tools/.config/yazi/plugins/preview-fullscreen.yazi/main.lua`

**Only proceed if Task 5 found `watcher()` or similar hook exists.**

**Step 1: Rewrite plugin with watcher**

```lua
-- preview-fullscreen.yazi — Auto-fullscreen preview for images/PDFs

local is_preview_file = function(path)
  if not path then return false end
  local ext = tostring(path):match("%.([^%.]+)$")
  if not ext then return false end
  ext = ext:lower()
  return ext == "png" or ext == "jpg" or ext == "jpeg" or ext == "gif" or
         ext == "webp" or ext == "bmp" or ext == "tiff" or ext == "tif" or
         ext == "avif" or ext == "pdf"
end

local last_hovered = nil

return {
  entry = function(self, job)
    ya.dbg("preview-fullscreen: entry (manual toggle)")
    local hovered = ya.sync(function()
      return cx.manager.hovered
    end)

    if hovered and is_preview_file(hovered.url) then
      ya.dbg("preview-fullscreen: manual fullscreen")
      ya.manager_emit("resize", { 0, 0, 1 })
    else
      ya.dbg("preview-fullscreen: manual restore")
      ya.manager_emit("resize", { 0, 3, 4 })
    end
  end,

  watcher = function(self)
    ya.dbg("preview-fullscreen: watcher tick")
    local hovered = ya.sync(function()
      return cx.manager.hovered
    end)

    local current = hovered and tostring(hovered.url) or nil

    if current ~= last_hovered then
      ya.dbg("preview-fullscreen: hovered changed to " .. (current or "nil"))
      last_hovered = current

      if current and is_preview_file(current) then
        ya.dbg("preview-fullscreen: auto-fullscreen on hover")
        ya.manager_emit("resize", { 0, 0, 1 })
      elseif current and not is_preview_file(current) then
        ya.dbg("preview-fullscreen: auto-restore on non-preview hover")
        ya.manager_emit("resize", { 0, 3, 4 })
      end
    end
  end,
}
```

**Step 2: Commit**

```bash
git add .config/yazi/plugins/preview-fullscreen.yazi/main.lua
git commit -m "feat: add watcher hook for auto-reveal preview fullscreen"
```

**Step 3: Restart yazi**

```bash
pkill yazi
sleep 1
ide ~/Pictures
sleep 2
```

**Step 4: Screenshot normal state**

```bash
tmux2png > /tmp/watcher-normal.png
```

**Step 5: Navigate to image with arrow keys**

Press `j` multiple times to reach an image file.

After each press, wait 0.5s and check:
```bash
tmux2png > /tmp/watcher-image-selected.png
```

**Step 6: Inspect screenshot**

```bash
# In Claude Code:
Read /tmp/watcher-image-selected.png
```

Expected: If watcher works, when cursor reaches image, preview should auto-fullscreen.

If still 2-column: Watcher hook not supported, move to Task 7.

**Step 7: Check logs**

```bash
cat ~/.local/state/yazi/logs/yazi.log | grep "preview-fullscreen: watcher" | tail -5
```

Expected: See "watcher tick" messages appearing continuously (or at least when hover changes).

---

### Task 7: Fallback — test init.lua event hook

**Files:**
- Modify: `~/tools/.config/yazi/init.lua`

**Only if Task 6 watcher didn't work.**

**Step 1: Check if ya has event API in init.lua**

Edit init.lua and try:

```lua
require("yafg"):setup({
  editor = "nvim",
  args = {},
  file_arg_format = "+{row} {file}",
})

require("preview-fullscreen")

-- Try event hook (if it exists)
if ya and ya.on_hover then
  ya.dbg("init.lua: ya.on_hover is available")
  ya.on_hover(function(hovered)
    ya.dbg("init.lua: on_hover called with " .. tostring(hovered.url))
  end)
else
  ya.dbg("init.lua: ya.on_hover NOT available")
end
```

**Step 2: Restart yazi and check logs**

```bash
pkill yazi
sleep 1
ide ~/Pictures
sleep 2
cat ~/.local/state/yazi/logs/yazi.log | grep "on_hover" | head -10
```

Expected: See "on_hover is available" or "on_hover NOT available".

**Step 3: If available, update plugin**

If "available", add callback handler to plugin:

```lua
function M:on_hover(hovered)
  local path = tostring(hovered.url)
  if is_preview_file(path) then
    ya.manager_emit("resize", { 0, 0, 1 })
  else
    ya.manager_emit("resize", { 0, 3, 4 })
  end
end

-- In init.lua, register it:
ya.on_hover(function(hovered)
  require("preview-fullscreen"):on_hover(hovered)
end)
```

**Step 4: Test and screenshot**

```bash
# Restart yazi
pkill yazi; sleep 1; ide ~/Pictures; sleep 2

# Navigate to image
# (press j multiple times)

# Screenshot should show auto-fullscreen
tmux2png > /tmp/fallback-fullscreen.png

# Read and verify in Claude Code
```

---

### Task 8: Final verification with ya emit-to

**Files:**
- Test only

**Step 1: Ensure yazi is running with latest plugin**

```bash
ps aux | grep yazi
# If not running: ide ~/Pictures
```

**Step 2: Screenshot initial state**

```bash
tmux2png > /tmp/final-before-reveal.png
```

**Step 3: Send reveal command from separate terminal**

```bash
ya emit-to 1313 reveal --str /home/g/Bilder/Bildschirmfotos/screenshot.png
```

(Replace path with actual image in your system)

**Step 4: Wait and screenshot**

```bash
sleep 1
tmux2png > /tmp/final-after-reveal.png
```

**Step 5: Compare screenshots**

```bash
# In Claude Code:
Read /tmp/final-before-reveal.png
Read /tmp/final-after-reveal.png
```

**Expected (SUCCESS):**
- Before: Normal 2-column layout
- After: Preview-only fullscreen layout (left pane gone/minimized, image fills right side)

**If PASS:** Plugin is working!
```bash
git add /tmp/final-*.png
git commit -m "test: verify ya emit-to reveal triggers auto-fullscreen - SUCCESS"
```

**If FAIL:** Document why and create new task to fix the remaining issue.

---

## Summary Checklist

After completing all tasks:

- [ ] Task 2: Ctrl+P manual toggle works (screenshots confirm)
- [ ] Task 3: `ya emit-to reveal` navigates yazi (but doesn't auto-fullscreen yet)
- [ ] Task 4: Logs show plugin NOT called on reveal
- [ ] Task 5: Research found watcher/event hooks OR confirmed they don't exist
- [ ] Task 6: Watcher hook implemented and tested OR confirmed unsupported
- [ ] Task 7: Fallback event hook attempted OR confirmed unsupported
- [ ] Task 8: Final reveal test shows fullscreen working OR identifies blocker

**If all pass:** Plugin is complete and working!
**If blocked at Task 6/7:** Document missing yazi API and propose alternative (e.g., polling timer, manual step).

---

## Next Steps

**Plan complete and ready for execution.**

Choose execution method:

**1. Subagent-Driven (this session)**
- I dispatch fresh subagent per task
- Visual review of screenshots between tasks
- Fast iteration with feedback loop

**2. Parallel Session (separate)**
- Open new Claude Code session with executing-plans skill
- Batch execution with checkpoints
- Better for isolated long-running work

Which approach?
