-- Binary file preview: Sends images/PDFs to the running yazi instance
-- Yazi (in WezTerm split) navigates to the file and shows native preview
-- Uses ya emit-to with fixed client-id "nvim-ide" (set by ide script)

local binary_extensions = {
  "png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff", "tif", "avif",
  "pdf",
}

local YAZI_IDE_ID = vim.env.YAZI_IDE_ID or "1313"

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

    -- Tell yazi to reveal/preview this file via DDS
    local result = vim.fn.system({ "ya", "emit-to", YAZI_IDE_ID, "reveal", "--", filepath })
    local ok = vim.v.shell_error == 0

    vim.schedule(function()
      -- Clean up the buffer — don't open binary in nvim
      if vim.api.nvim_buf_is_valid(buf) then
        vim.api.nvim_buf_delete(buf, { force = true })
      end

      if ok then
        vim.notify("Preview: " .. vim.fn.fnamemodify(filepath, ":t"), vim.log.levels.INFO)
      else
        vim.notify("yazi nicht erreichbar (ide Layout aktiv?)", vim.log.levels.WARN)
      end
    end)
  end,
})

return {}
