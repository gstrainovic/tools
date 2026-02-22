require("yafg"):setup({
  editor = "nvim",
  args = {},
  file_arg_format = "+{row} {file}",
})

-- Preview fullscreen plugin — auto-expand preview for binary files
require("preview-fullscreen")

-- Test if ya.on_hover event API exists
if ya.on_hover then
  ya.notify({ title = "init.lua", content = "ya.on_hover: AVAILABLE", timeout = 3, level = "info" })
else
  ya.notify({ title = "init.lua", content = "ya.on_hover: NOT available", timeout = 3, level = "info" })
end
