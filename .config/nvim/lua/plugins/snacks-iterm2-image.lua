return {
  {
    "snacks-iterm2-image",
    dir = vim.fn.expand("~/projects/tools/snacks-iterm2-image"),
    dependencies = { "snacks.nvim" },
    config = function()
      require("snacks-iterm2-image").setup()
    end,
  },
}
