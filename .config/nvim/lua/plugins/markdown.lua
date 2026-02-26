return {
  -- render-markdown.nvim und markdown-preview.nvim deaktivieren
  { "MeanderingProgrammer/render-markdown.nvim", enabled = false },
  { "iamcco/markdown-preview.nvim", enabled = false },

  -- markview.nvim: Markdown-Rendering mit Split-Preview
  {
    "OXY2DEV/markview.nvim",
    ft = { "markdown" },
    dependencies = {
      "nvim-treesitter/nvim-treesitter",
      "nvim-tree/nvim-web-devicons",
    },
    keys = {
      { "<leader>mp", "<cmd>Markview splitToggle<cr>", desc = "Markdown Preview Split" },
    },
  },

  -- Markdown LSP (marksman) deaktivieren
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        marksman = { enabled = false },
      },
    },
  },
  -- markdownlint (none-ls / nvim-lint) deaktivieren
  {
    "mfussenegger/nvim-lint",
    optional = true,
    opts = {
      linters_by_ft = {
        markdown = {},
      },
    },
  },
}
