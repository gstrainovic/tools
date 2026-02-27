-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

-- Bild-Popup: Zeigt Bild unter Cursor in einem Floating-Fenster (Ghostty/KGP)
vim.keymap.set("n", "<leader>ip", function()
  Snacks.image.hover()
end, { desc = "Image Preview Popup" })

-- Bild unter Cursor in imv öffnen (Fallback für Nicht-Bild-Buffer)
vim.keymap.set("n", "<leader>iP", function()
  local file = vim.fn.expand("<cfile>")
  if file == "" then file = vim.fn.expand("%") end
  vim.fn.jobstart({ "imv", vim.fn.fnamemodify(file, ":p") }, { detach = true })
end, { desc = "Open image in imv" })
