-- preview-fullscreen.yazi — Toggle preview fullscreen for images/PDFs

return {
  entry = function(self, job)
    ya.notify({ title = "preview-fullscreen", content = "entry called", timeout = 2, level = "info" })

    -- Get current manager state synchronously
    local hovered = ya.sync(function()
      return cx.manager.hovered
    end)

    if not hovered then
      ya.notify({ title = "preview-fullscreen", content = "no hovered file", timeout = 2, level = "info" })
      return
    end

    ya.notify({ title = "preview-fullscreen", content = "hovered=" .. tostring(hovered.url), timeout = 2, level = "info" })

    -- Check if hovered file is a preview type
    local path = tostring(hovered.url)
    local ext = path:match("%.([^%.]+)$")
    if ext then
      ext = ext:lower()
      ya.notify({ title = "preview-fullscreen", content = "ext=" .. ext, timeout = 2, level = "info" })

      local is_preview = ext == "png" or ext == "jpg" or ext == "jpeg" or
                         ext == "gif" or ext == "webp" or ext == "bmp" or
                         ext == "tiff" or ext == "tif" or ext == "avif" or
                         ext == "pdf"

      if is_preview then
        ya.notify({ title = "preview-fullscreen", content = "toggling to fullscreen", timeout = 2, level = "info" })
        ya.manager_emit("resize", { 0, 0, 1 })
      else
        ya.notify({ title = "preview-fullscreen", content = "restoring layout", timeout = 2, level = "info" })
        ya.manager_emit("resize", { 0, 3, 4 })
      end
    else
      ya.notify({ title = "preview-fullscreen", content = "no extension found", timeout = 2, level = "info" })
    end
  end,
}
