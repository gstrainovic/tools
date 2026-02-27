--- Override module for snacks.nvim image pipeline
--- Monkey-patches terminal.request, Image:send, and Placement:render_fallback
--- to use iTerm2 OSC 1337 protocol instead of Kitty Graphics Protocol.
local M = {}

local protocol = require("snacks-iterm2-image.protocol")

--- @class snacks_iterm2_image.Config
--- @field force_iterm2? boolean Force iTerm2 protocol regardless of terminal
--- @field auto_detect? boolean Auto-detect compatible terminals (default: true)
M._config = {
  force_iterm2 = false,
  auto_detect = true,
}

-- Saved original functions
M._orig_send = nil
M._orig_render_fallback = nil
M._orig_del = nil

-- Debug logging
M._debug_entries = {}
function M._debug_log(msg)
  table.insert(M._debug_entries, msg)
  local f = io.open("/tmp/iterm2-debug.log", "a")
  if f then f:write(msg .. "\n"); f:close() end
end

-- Cached PTY file descriptor for direct terminal writes.
-- nvim's io.stdout goes to the TUI process via RPC, which filters OSC 1337.
-- We bypass this by writing directly to the parent process's PTY.
M._pty_path = nil

--- Get the PTY path of the terminal (parent process's stdout)
---@return string|nil
function M._get_pty_path()
  if M._pty_path then return M._pty_path end
  local ppid = vim.fn.system("ps -o ppid= -p " .. vim.fn.getpid()):gsub("%s+", "")
  local path = vim.fn.system("readlink /proc/" .. ppid .. "/fd/1 2>/dev/null"):gsub("%s+", "")
  if path:find("pts/") or path:find("tty") then
    M._pty_path = path
    M._debug_log("PTY path: " .. path)
    return path
  end
  M._debug_log("WARNING: no PTY found, parent stdout=" .. path)
  return nil
end

--- Write data directly to the terminal PTY, bypassing nvim's TUI filter.
---@param data string
function M._pty_write(data)
  local path = M._get_pty_path()
  if not path then return false end
  local tty = io.open(path, "wb")
  if not tty then return false end
  tty:write(data)
  tty:flush()
  tty:close()
  return true
end

--- Detect if current terminal supports iTerm2 image protocol
---@return boolean
function M.detect_terminal()
  local term_program = vim.env.TERM_PROGRAM or ""
  local tp_lower = term_program:lower()
  return tp_lower:find("wezterm") ~= nil
    or tp_lower:find("iterm") ~= nil
end

--- Check if we should use iTerm2 protocol
---@return boolean
function M.should_use_iterm2()
  if M._config.force_iterm2 then
    return true
  end
  if vim.env.SNACKS_ITERM2 == "1" then
    return true
  end
  if M._config.auto_detect then
    return M.detect_terminal()
  end
  return false
end

--- Override for Image:send()
--- Instead of sending KGP upload, just mark image as sent.
--- The actual image data will be sent during placement via iTerm2 OSC 1337.
---@param image table The Image instance (self)
function M.iterm2_send(image)
  image.sent = true
  M._debug_log("iterm2_send: id=" .. tostring(image.id) .. " file=" .. tostring(image.file))
  image:on_send()
end

-- Active placements registry for decoration_provider repainting.
-- key = unique placement id (string), value = { wins, seq, buf }
M._active = {}

-- Namespace for the decoration provider
M._dec_ns = nil

--- Paint the iTerm2 image for given wins/seq
--- Writes directly to the PTY, bypassing nvim's TUI which filters OSC 1337.
---@param wins number[]
---@param seq string pre-built iTerm2 OSC sequence
local function paint_wins(wins, seq)
  for _, win in ipairs(wins) do
    if vim.api.nvim_win_is_valid(win) then
      local pos = vim.api.nvim_win_get_position(win)
      local has_tabline = vim.o.showtabline == 2
        or (vim.o.showtabline == 1 and vim.fn.tabpagenr("$") > 1)
      local row = pos[1] + 1 + (has_tabline and 1 or 0)
      local col = pos[2] + 1
      local cursor_seq = "\27[" .. row .. ";" .. col .. "H"
      local full_seq = cursor_seq .. seq
      -- Apply tmux passthrough if needed
      local terminal = Snacks.image.terminal
      if terminal.transform then
        full_seq = terminal.transform(full_seq)
      end
      M._debug_log("  paint_wins win=" .. win .. " row=" .. row .. " col=" .. col)
      M._pty_write(full_seq)
    end
  end
end

--- Repaint all active placements. Called from decoration_provider on_end.
local function repaint_all()
  for _, entry in pairs(M._active) do
    if vim.api.nvim_buf_is_valid(entry.buf) then
      paint_wins(entry.wins, entry.seq)
    end
  end
end

--- Set up decoration_provider so images survive nvim redraws.
--- on_end fires AFTER nvim has drawn all windows for this redraw cycle.
local function ensure_decoration_provider()
  if M._dec_ns then return end
  M._dec_ns = vim.api.nvim_create_namespace("snacks_iterm2_image")
  vim.api.nvim_set_decoration_provider(M._dec_ns, {
    on_end = function()
      if next(M._active) ~= nil then
        -- vim.schedule defers until AFTER nvim has flushed its cell data to the PTY.
        -- Without this, our io.stdout:write arrives before nvim's cells and gets overwritten.
        vim.schedule(repaint_all)
      end
    end,
  })
  M._debug_log("decoration_provider installed")
end

--- Override for Placement:render_fallback()
--- Sends iTerm2 OSC 1337 sequence and registers for post-redraw repainting.
---@param placement table The Placement instance (self)
---@param state snacks.image.State
function M.iterm2_render_fallback(placement, state)
  M._debug_log("iterm2_render_fallback: wins=" .. #state.wins
    .. " width=" .. state.loc.width .. " height=" .. state.loc.height
    .. " file=" .. tostring(placement.img.file))

  if not placement.opts.inline then
    vim.api.nvim_buf_clear_namespace(placement.buf, placement.ns, 0, -1)
  end

  -- Build OSC 1337 sequence (reads file once; expensive, so cache via registry)
  local pid = tostring(placement.buf) .. ":" .. tostring(placement.id or "")
  local seq = (M._active[pid] or {}).seq

  -- Rebuild if file or dimensions changed
  local needs_rebuild = not seq
  if not needs_rebuild then
    local prev = M._active[pid]
    if prev.width ~= state.loc.width or prev.height ~= state.loc.height then
      needs_rebuild = true
    end
  end

  if needs_rebuild then
    seq = protocol.build_file_sequence(placement.img.file, {
      width = state.loc.width,
      height = state.loc.height,
    })
    if not seq then
      M._debug_log("  ERROR: seq is nil!")
      return
    end
  end

  local wins = vim.deepcopy(state.wins)

  -- Register for persistent repainting via decoration_provider
  M._active[pid] = {
    buf = placement.buf,
    wins = wins,
    seq = seq,
    width = state.loc.width,
    height = state.loc.height,
  }

  -- Ensure decoration_provider is installed for persistent repainting
  ensure_decoration_provider()

  -- Paint immediately via direct PTY write
  paint_wins(wins, seq)
end

--- Unregister a placement from the active registry (called on del)
---@param pid string placement id key
local function unregister(pid)
  M._active[pid] = nil
  M._debug_log("unregister: " .. pid)
end

--- Override for Image:del()
--- iTerm2 has no explicit delete command; unregister from repaint registry.
---@param image table The Image instance (self)
---@param pid? number Placement ID
function M.iterm2_del(image, pid)
  for _, p in ipairs(pid and { pid } or vim.tbl_keys(image.placements)) do
    if image.placements[p] then
      local key = tostring(image.placements[p].buf) .. ":" .. tostring(p)
      unregister(key)
      image.placements[p] = nil
    end
  end
end

--- Apply all overrides to snacks.nvim
function M.setup(config)
  M._config = vim.tbl_deep_extend("force", M._config, config or {})

  if not M.should_use_iterm2() then
    return false
  end

  local terminal = Snacks.image.terminal
  local Image = Snacks.image.image
  local Placement = Snacks.image.placement

  -- Ensure env() reports no placeholders (iTerm2 doesn't support them)
  local orig_env = terminal.env
  terminal.env = function()
    local env = orig_env()
    if M.should_use_iterm2() then
      env.placeholders = false
      env.supported = true
    end
    return env
  end

  -- Override Image:send()
  M._orig_send = Image.send
  Image.send = function(self)
    if M.should_use_iterm2() then
      return M.iterm2_send(self)
    end
    return M._orig_send(self)
  end

  -- Override Placement:render_fallback()
  M._orig_render_fallback = Placement.render_fallback
  Placement.render_fallback = function(self, state)
    if M.should_use_iterm2() then
      return M.iterm2_render_fallback(self, state)
    end
    return M._orig_render_fallback(self, state)
  end

  -- Override Image:del()
  M._orig_del = Image.del
  Image.del = function(self, pid)
    if M.should_use_iterm2() then
      return M.iterm2_del(self, pid)
    end
    return M._orig_del(self, pid)
  end

  return true
end

--- Remove all overrides (restore originals)
function M.teardown()
  M._active = {}
  if M._orig_send then
    Snacks.image.image.send = M._orig_send
    M._orig_send = nil
  end
  if M._orig_render_fallback then
    Snacks.image.placement.render_fallback = M._orig_render_fallback
    M._orig_render_fallback = nil
  end
  if M._orig_del then
    Snacks.image.image.del = M._orig_del
    M._orig_del = nil
  end
end

return M
