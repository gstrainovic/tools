return {
  {
    "3rd/image.nvim",
    enabled = false,
    build = false,
    opts = {
      backend = "sixel",
      processor = "magick_cli",
      integrations = {
        markdown = {
          enabled = true,
          only_render_image_at_cursor = false,
          filetypes = { "markdown", "vimwiki" },
        },
      },
      max_width_window_percentage = 50,
      max_height_window_percentage = 50,
      hijack_file_patterns = { "*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.avif" },
    },
  },
}
