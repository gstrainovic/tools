-- preview-fullscreen.yazi — Auto-fullscreen preview for images/PDFs
-- When yazi reveals a binary file, preview panel expands to fullscreen
-- Navigate away to restore normal layout, or press 'Esc' to toggle

local NORMAL_RATIO = { 0, 3, 4 }
local PREVIEW_RATIO = { 0, 0, 1 }
local is_fullscreen = false

--- Check if file is a preview binary type
local function is_preview_file(url)
  if not url then return false end

  local path = tostring(url)
  local ext = path:match("%.([^%.]+)$")
  if not ext then return false end

  ext = ext:lower()
  local preview_types = {
    png = true, jpg = true, jpeg = true, gif = true, webp = true,
    bmp = true, tiff = true, tif = true, avif = true,
    pdf = true,
  }
  return preview_types[ext] or false
end

--- Toggle preview fullscreen
function M:toggle()
  if is_fullscreen then
    ya.manager_emit("resize", { NORMAL_RATIO[1], NORMAL_RATIO[2], NORMAL_RATIO[3] })
    is_fullscreen = false
  else
    ya.manager_emit("resize", { PREVIEW_RATIO[1], PREVIEW_RATIO[2], PREVIEW_RATIO[3] })
    is_fullscreen = true
  end
end

--- Check hovered file and auto-fullscreen if preview type
function M:check_and_fullscreen()
  ya.emit("escape", { visual = true })

  local hovered = ya.sync(function()
    return cx.manager.hovered
  end)

  if hovered and is_preview_file(hovered.url) then
    if not is_fullscreen then
      ya.manager_emit("resize", { PREVIEW_RATIO[1], PREVIEW_RATIO[2], PREVIEW_RATIO[3] })
      is_fullscreen = true
    end
  elseif is_fullscreen then
    -- Auto-restore if moved to non-preview file
    ya.manager_emit("resize", { NORMAL_RATIO[1], NORMAL_RATIO[2], NORMAL_RATIO[3] })
    is_fullscreen = false
  end
end

return M
