-- preview-fullscreen.yazi — Toggle preview fullscreen for images/PDFs
-- Manual toggle with Ctrl+P. Yazi doesn't support auto-trigger on reveal events.

return {
  entry = function(self, job)
    -- Get current manager state synchronously
    local hovered = ya.sync(function()
      return cx.manager.hovered
    end)

    ya.notify({ title = "preview-fullscreen", content = "entry called, hovered=" .. tostring(hovered and "yes" or "no"), timeout = 2, level = "info" })

    if not hovered then
      ya.notify({ title = "preview-fullscreen", content = "❌ no hovered file", timeout = 2, level = "warn" })
      return
    end

    -- Check if hovered file is a preview type
    local path = tostring(hovered.url)
    local ext = path:match("%.([^%.]+)$")

    ya.notify({ title = "preview-fullscreen", content = "path=" .. path, timeout = 2, level = "info" })

    if not ext then
      ya.notify({ title = "preview-fullscreen", content = "❌ no extension", timeout = 2, level = "warn" })
      return
    end

    ext = ext:lower()
    ya.notify({ title = "preview-fullscreen", content = "ext=" .. ext, timeout = 2, level = "info" })

    local is_preview = ext == "png" or ext == "jpg" or ext == "jpeg" or
                       ext == "gif" or ext == "webp" or ext == "bmp" or
                       ext == "tiff" or ext == "tif" or ext == "avif" or
                       ext == "pdf"

    if is_preview then
      ya.notify({ title = "preview-fullscreen", content = "✅ resizing to [0,0,1] fullscreen", timeout = 2, level = "info" })
      ya.manager_emit("resize", { 0, 0, 1 })
    else
      ya.notify({ title = "preview-fullscreen", content = "restoring [0,3,4] normal", timeout = 2, level = "info" })
      ya.manager_emit("resize", { 0, 3, 4 })
    end
  end,
}
