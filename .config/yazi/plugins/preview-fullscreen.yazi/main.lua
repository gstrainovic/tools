-- preview-fullscreen.yazi — Toggle preview fullscreen for images/PDFs
-- Manual toggle with Ctrl+P. Yazi doesn't support auto-trigger on reveal events.

return {
  entry = function(self, job)
    -- Get current manager state synchronously
    local hovered = ya.sync(function()
      return cx.manager.hovered
    end)

    if not hovered then
      return
    end

    -- Check if hovered file is a preview type
    local path = tostring(hovered.url)
    local ext = path:match("%.([^%.]+)$")
    if not ext then
      return
    end

    ext = ext:lower()
    local is_preview = ext == "png" or ext == "jpg" or ext == "jpeg" or
                       ext == "gif" or ext == "webp" or ext == "bmp" or
                       ext == "tiff" or ext == "tif" or ext == "avif" or
                       ext == "pdf"

    if is_preview then
      ya.manager_emit("resize", { 0, 0, 1 })
    else
      ya.manager_emit("resize", { 0, 3, 4 })
    end
  end,
}
