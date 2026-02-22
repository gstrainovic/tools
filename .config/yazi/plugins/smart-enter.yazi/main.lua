-- smart-enter: Ordner → yazi enter, Dateien → open (nvim via opener rules)
return {
  entry = function()
    local h = cx.active.current.hovered
    if h == nil then return end

    if h.cha.is_dir then
      ya.manager_emit("enter", {})
    else
      ya.manager_emit("open", { hovered = true })
    end
  end,
}
