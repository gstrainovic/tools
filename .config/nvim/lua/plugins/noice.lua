return {
  {
    "folke/noice.nvim",
    opts = {
      presets = {
        bottom_search = true, -- Suche unten statt floating
        lsp_doc_border = true,
      },
      lsp = {
        progress = { enabled = false }, -- LSP Progress-Spinner aus (spart Redraws)
      },
    },
  },
}
