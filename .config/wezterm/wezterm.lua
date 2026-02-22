local wezterm = require 'wezterm'
local config = wezterm.config_builder()

-- ── Keybinding: Ctrl+Shift+Z → Pane Zoom ──────────────────────────────────
config.keys = {
  {
    key = 'Z',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.TogglePaneZoomState,
  },
}

return config
