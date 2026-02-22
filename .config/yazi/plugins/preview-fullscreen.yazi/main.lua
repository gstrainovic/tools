-- preview-fullscreen.yazi — Toggle preview fullscreen for images/PDFs

return {
  entry = function(self, job)
    ya.notify({ title = "preview-fullscreen", content = "entry called", timeout = 1, level = "info" })
  end,
}
