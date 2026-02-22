require("yafg"):setup({
  editor = "nvim",
  args = {},
  file_arg_format = "+{row} {file}",
})

-- Preview fullscreen plugin — auto-expand preview for binary files
require("preview-fullscreen")
