-- image-viewer.lua — Bild/PDF im WezTerm-Split anzeigen via img-preview
-- Standalone: kein yazi, kein State, rein WezTerm-basiert

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
