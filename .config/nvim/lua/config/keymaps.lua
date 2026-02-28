-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

-- Bild-Popup: Zeigt Bild unter Cursor in einem Floating-Fenster (Ghostty/KGP)
vim.keymap.set("n", "<leader>ip", function()
  Snacks.image.hover()
end, { desc = "Image Preview Popup" })
