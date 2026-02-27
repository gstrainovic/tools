--- snacks-iterm2-image: iTerm2 OSC 1337 image protocol for snacks.nvim
--- Patches snacks.nvim to render image previews via iTerm2 protocol
--- instead of Kitty Graphics Protocol. Works in WezTerm and iTerm2.
local M = {}

M._setup_done = false

--- @class snacks_iterm2_image.Config
local defaults = {
  --- Force iTerm2 protocol regardless of terminal detection
  force_iterm2 = false,
  --- Auto-detect compatible terminals (WezTerm, iTerm2)
  auto_detect = true,
}

--- Setup the plugin. Call after snacks.nvim is loaded.
---@param opts? snacks_iterm2_image.Config
function M.setup(opts)
  if M._setup_done then
    return
  end
  M._setup_done = true

  local config = vim.tbl_deep_extend("force", defaults, opts or {})

  -- Defer until snacks.nvim image module is available
  local ok = pcall(function()
    -- Trigger lazy-loading of snacks.image submodules
    local _ = Snacks.image.terminal
    local _ = Snacks.image.image
    local _ = Snacks.image.placement
  end)

  if not ok then
    vim.notify("[snacks-iterm2-image] snacks.nvim image module not available", vim.log.levels.WARN)
    return
  end

  local override = require("snacks-iterm2-image.override")
  local applied = override.setup(config)

  if applied then
    vim.notify("[snacks-iterm2-image] iTerm2 image protocol active", vim.log.levels.INFO)
  end
end

return M
