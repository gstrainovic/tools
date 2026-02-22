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
    local reveal_result = vim.fn.system({ "ya", "emit-to", YAZI_IDE_ID, "reveal", "--", filepath })
    local reveal_ok = vim.v.shell_error == 0

    -- If reveal succeeded, trigger fullscreen preview in yazi
    if reveal_ok then
      vim.defer_fn(function()
        local plugin_result = vim.fn.system({ "ya", "emit-to", YAZI_IDE_ID, "plugin", "preview-fullscreen" })
        local plugin_ok = vim.v.shell_error == 0
        if not plugin_ok then
          vim.notify("⚠️ Plugin fullscreen failed: " .. tostring(plugin_result), vim.log.levels.WARN)
        end
      end, 200)  -- Increased delay to 200ms
    end

    vim.schedule(function()
      -- Clean up the buffer — don't open binary in nvim
      if vim.api.nvim_buf_is_valid(buf) then
        vim.api.nvim_buf_delete(buf, { force = true })
      end

      if reveal_ok then
        vim.notify("🖼️  Preview: " .. vim.fn.fnamemodify(filepath, ":t") .. " (layout toggle in 200ms)", vim.log.levels.INFO)
      else
        vim.notify("❌ yazi nicht erreichbar (YAZI_IDE_ID=" .. YAZI_IDE_ID .. ")", vim.log.levels.WARN)
      end
    end)
  end,
})

return {}
