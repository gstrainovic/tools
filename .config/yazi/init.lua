require("yafg"):setup({
  editor = "nvim",
  args = {},
  file_arg_format = "+{row} {file}",
})

-- Preview fullscreen plugin — toggle with Ctrl+P
require("preview-fullscreen")
