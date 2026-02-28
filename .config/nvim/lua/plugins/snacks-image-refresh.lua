-- snacks-image-refresh.lua
-- Erzwingt snacks Bild-Re-Render bei Tab-Wechsel zurück zu einem Bild-Buffer.
-- Ohne das: Bild verschwindet nach Tab-Wechsel in manchen Terminals.

local image_exts = { png=true, jpg=true, jpeg=true, gif=true, webp=true, bmp=true, tiff=true, avif=true }

local function is_image_buf(buf)
  if vim.bo[buf].filetype == "image" then return true end
  local ext = vim.api.nvim_buf_get_name(buf):match("%.(%w+)$")
  return ext and image_exts[ext:lower()] or false
end

vim.api.nvim_create_autocmd("BufEnter", {
  desc = "snacks-image-refresh: Bild neu rendern bei Tab-Wechsel",
  callback = function(ev)
    if is_image_buf(ev.buf) then
      vim.schedule(function()
        pcall(Snacks.image.buf.attach, ev.buf)
      end)
    end
  end,
})

return {}
