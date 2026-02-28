return {
  {
    "snacks.nvim",
    opts = {
      animate = { enabled = false },
      scroll = { enabled = false },
      indent = { animate = { enabled = false } },
      image = {
        enabled = true,
        env = { ghostty = true },
      },
      picker = {
        sources = {
          explorer = {
            layout = { preset = "sidebar", preview = true },
          },
        },
      },
    },
  },
}
