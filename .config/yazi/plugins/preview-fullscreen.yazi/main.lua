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
        ya.dbg("preview-fullscreen: restoring layout")
        ya.manager_emit("resize", { 0, 3, 4 })
      end
    else
      ya.dbg("preview-fullscreen: no extension found")
    end
  end,
}
