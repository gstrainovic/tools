return {
  {
    "dhruvasagar/vim-table-mode",
    ft = { "markdown" },
    cmd = { "TableModeRealign" },
    init = function()
      vim.g.table_mode_map_prefix = "<leader>m"
      vim.g.table_mode_toggle_map = ""
      vim.g.table_mode_tableize_map = ""
      vim.g.table_mode_tableize_d_map = ""
      vim.g.table_mode_auto_align = 1
      vim.g.table_mode_corner = "|"
      vim.g.table_mode_always_active = 1
      vim.g.table_mode_verbose = 0
    end,
  },
}
