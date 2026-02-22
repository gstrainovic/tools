return {
  {
    "saghen/blink.cmp",
    opts = {
      completion = {
        documentation = {
          auto_show_delay_ms = 150, -- Default: 500ms
        },
        accept = {
          auto_brackets = {
            semantic_token_resolution = {
              timeout_ms = 200, -- Default: 400ms
            },
          },
        },
      },
    },
  },
}
