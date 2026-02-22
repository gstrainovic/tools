local wezterm = require 'wezterm'
local config = wezterm.config_builder()

-- ── user-var-changed: Screenshot-Trigger von außen ──────────────────────────
-- Claude kann via Shell triggern:
--   printf '\033]1337;SetUserVar=WEZTERM_SCREENSHOT=%s\007' \
--     "$(echo -n '/tmp/out.png' | base64 -w0)" | \
--     wezterm cli send-text --pane-id PANE_ID --no-paste
--
-- Das feuert diesen Event ohne Tastendruck des Users.

wezterm.on('user-var-changed', function(window, pane, name, value)
  if name ~= 'WEZTERM_SCREENSHOT' then return end

  -- value ist der gewünschte Output-Pfad (base64-decoded ist bereits der Pfad)
  local output_path = value
  if output_path == '' then
    output_path = '/tmp/wezterm-screenshot-' .. os.time() .. '.png'
  end

  -- Finde das Script-Verzeichnis
  local scripts_dir = wezterm.home_dir .. '/wezterm-screenshot/scripts'

  -- Kurz den Screenshot-Pane aktivieren (bringt ihn in den Vordergrund)
  -- Damit der XDG-Portal-Screenshot den richtigen Tab zeigt
  pane:activate()

  -- XDG Portal Screenshot (WezTerm ist aktives Fenster → funktioniert)
  local ok, stdout, stderr = wezterm.run_child_process({
    'python3', scripts_dir .. '/screenshot-linux-wayland.py', output_path
  })

  -- Ergebnis loggen
  if ok and stdout and stdout ~= '' then
    local path = stdout:gsub('%s+$', '')
    wezterm.log_info('Screenshot saved: ' .. path)
    window:toast_notification('Screenshot', path, nil, 3000)
  else
    wezterm.log_error('Screenshot failed: ' .. (stderr or 'unknown'))
    window:toast_notification('Screenshot FAILED', stderr or 'unknown', nil, 3000)
  end
end)

-- ── Keybinding: Ctrl+Shift+Z → Pane Zoom (yazi-Split minimieren/maximieren) ──
-- ── Keybinding: Ctrl+Shift+S → Screenshot ────────────────────────────────────
config.keys = {
  {
    key = 'Z',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.TogglePaneZoomState,
  },
}
table.insert(config.keys, { -- Screenshot

  key = 'S',
  mods = 'CTRL|SHIFT',
  action = wezterm.action_callback(function(window, pane)
    local scripts_dir = wezterm.home_dir .. '/wezterm-screenshot/scripts'
    local output_path = '/tmp/wezterm-screenshot-' .. os.time() .. '.png'
    local ok, stdout, stderr = wezterm.run_child_process({
      'python3', scripts_dir .. '/screenshot-linux-wayland.py', output_path
    })
    if ok and stdout and stdout ~= '' then
      local path = stdout:gsub('%s+$', '')
      window:toast_notification('Screenshot', path, nil, 3000)
    else
      window:toast_notification('Screenshot failed', stderr or '?', nil, 3000)
    end
  end),
})

return config
