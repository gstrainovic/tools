return {
  {
    "mikavilpas/yazi.nvim",
    version = "*",
    event = "VeryLazy",
    dependencies = {
      { "nvim-lua/plenary.nvim", lazy = true },
    },
    keys = {
      { "<leader>y", "<cmd>Yazi<cr>", desc = "Yazi (current file)", mode = { "n", "v" } },
      { "<leader>Y", "<cmd>Yazi cwd<cr>", desc = "Yazi (cwd)" },
      { "<c-up>", "<cmd>Yazi toggle<cr>", desc = "Resume last yazi session" },
    },
    opts = {
      open_for_directories = false,
      floating_window_scaling_factor = 0.9,
      yazi_floating_window_border = "rounded",
      integrations = {
        grep_in_directory = "snacks.picker",
      },
      keymaps = {
        show_help = "<f1>",
      },
    },
  },
}
