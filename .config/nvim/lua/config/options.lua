-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

vim.opt.ttimeoutlen = 5 -- Escape sofort (Default: 50ms)
vim.opt.updatetime = 100 -- CursorHold schneller (Default: 200ms)
vim.opt.redrawtime = 500 -- Max Syntax-Redraw (Default: 2000ms — bricht bei großen Files schneller ab)
vim.opt.synmaxcol = 300 -- Syntax-Highlighting max Spalten pro Zeile (Default: 3000)
