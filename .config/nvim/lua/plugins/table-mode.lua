return {
  {
    "dhruvasagar/vim-table-mode",
    cmd = { "TableModeToggle", "TableModeRealign" },
    keys = {
      { "<leader>tm", ":TableModeToggle<CR>", desc = "Toggle table mode" },
    },
    init = function()
      vim.g.table_mode_auto_align = 1
      vim.g.table_mode_corner = "|"
      -- Table Mode automatisch für Markdown aktivieren
      vim.api.nvim_create_autocmd("FileType", {
        pattern = "markdown",
        callback = function()
          vim.cmd("TableModeEnable")
        end,
      })
    end,
  },
}
