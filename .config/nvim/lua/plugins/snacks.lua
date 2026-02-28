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
            preview = true, -- Bild-Preview standardmäßig an
            actions = {
              -- Alt+P als Toggle (zusätzlich zu P)
              toggle_preview_alt = {
                action = function(picker)
                  picker:action("toggle_preview")
                end,
              },
            },
            win = {
              list = {
                keys = {
                  ["<A-p>"] = "toggle_preview",
                },
              },
            },
          },
        },
      },
    },
  },
}
