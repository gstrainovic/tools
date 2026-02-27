return {
  {
    "snacks-iterm2-image",
    dir = vim.fn.expand("~/projects/tools/snacks-iterm2-image"),
    dependencies = { "snacks.nvim" },
    enabled = false,
    config = function()
      require("snacks-iterm2-image").setup()
    end,
  },
}
