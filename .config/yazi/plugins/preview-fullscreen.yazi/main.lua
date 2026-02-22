-- preview-fullscreen.yazi — Toggle preview fullscreen for images/PDFs

return {
  entry = function(self, job)
    -- Get current manager state synchronously
    local hovered = ya.sync(function()
      return cx.manager.hovered
    end)

    -- Check if hovered file is a preview type
    if hovered then
      local path = tostring(hovered.url)
      local ext = path:match("%.([^%.]+)$")
      if ext then
        ext = ext:lower()
        local is_preview = ext == "png" or ext == "jpg" or ext == "jpeg" or
                           ext == "gif" or ext == "webp" or ext == "bmp" or
                           ext == "tiff" or ext == "tif" or ext == "avif" or
                           ext == "pdf"

        if is_preview then
          -- Toggle to fullscreen preview: [parent, current, preview] = [0, 0, 1]
          ya.manager_emit("resize", { 0, 0, 1 })
        else
          -- Restore normal layout: [0, 3, 4]
          ya.manager_emit("resize", { 0, 3, 4 })
        end
      end
    end
  end,
}
