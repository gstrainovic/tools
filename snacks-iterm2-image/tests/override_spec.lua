-- Mock snacks.nvim modules for testing
local written_data = {}
local request_log = {}

-- Mock Snacks global
_G.Snacks = {
  image = {
    config = { debug = { request = false } },
    terminal = {
      env = function()
        return { supported = true, placeholders = false, remote = false, name = "wezterm" }
      end,
      request = function(opts)
        table.insert(request_log, opts)
      end,
      write = function(data)
        table.insert(written_data, data)
      end,
      set_cursor = function(pos)
        table.insert(written_data, { cursor = pos })
      end,
      transform = nil,
    },
  },
  util = {
    base64 = function(s)
      return vim.base64.encode(s)
    end,
  },
}

local override = require("snacks-iterm2-image.override")
local protocol = require("snacks-iterm2-image.protocol")

describe("override", function()
  -- Reset state before each test group
  local function reset()
    written_data = {}
    request_log = {}
  end

  describe("should_use_iterm2", function()
    it("returns true when force_iterm2 is set", function()
      override._config = { force_iterm2 = true }
      eq(true, override.should_use_iterm2())
    end)

    it("returns false when force_iterm2 is false and no auto-detect", function()
      override._config = { force_iterm2 = false, auto_detect = false }
      eq(false, override.should_use_iterm2())
    end)

    it("returns true when SNACKS_ITERM2=1 env is set", function()
      override._config = { force_iterm2 = false }
      -- Simulate env var
      local orig = vim.env.SNACKS_ITERM2
      vim.env.SNACKS_ITERM2 = "1"
      eq(true, override.should_use_iterm2())
      vim.env.SNACKS_ITERM2 = orig
    end)

    it("auto-detects wezterm via TERM_PROGRAM", function()
      override._config = { force_iterm2 = false, auto_detect = true }
      local orig = vim.env.TERM_PROGRAM
      vim.env.TERM_PROGRAM = "WezTerm"
      eq(true, override.should_use_iterm2())
      vim.env.TERM_PROGRAM = orig
    end)

    it("auto-detects iTerm2 via TERM_PROGRAM", function()
      override._config = { force_iterm2 = false, auto_detect = true }
      local orig = vim.env.TERM_PROGRAM
      vim.env.TERM_PROGRAM = "iTerm.app"
      eq(true, override.should_use_iterm2())
      vim.env.TERM_PROGRAM = orig
    end)
  end)

  describe("iterm2_send", function()
    it("marks image as sent without sending KGP", function()
      reset()
      -- Create a temp image file
      local tmpfile = vim.fn.tempname() .. ".png"
      local f = io.open(tmpfile, "wb")
      f:write("PNG_DATA")
      f:close()

      local mock_image = {
        id = 42,
        file = tmpfile,
        sent = false,
        placements = {},
        on_send = function(self)
          -- no-op for test
        end,
      }

      override.iterm2_send(mock_image)
      eq(true, mock_image.sent, "image should be marked as sent")
      -- Should NOT have sent any KGP requests
      eq(0, #request_log, "should not send KGP requests")

      os.remove(tmpfile)
    end)
  end)

  describe("iterm2_render_fallback", function()
    it("sends iTerm2 sequence with cursor positioning", function()
      reset()
      local tmpfile = vim.fn.tempname() .. ".png"
      local f = io.open(tmpfile, "wb")
      f:write("IMG")
      f:close()

      local mock_placement = {
        img = { id = 1, file = tmpfile },
        id = 10,
        buf = 1,
        opts = { inline = false },
        ns = 0,
      }

      local state = {
        wins = { 1000 },
        loc = { 1, 0, width = 20, height = 10 },
      }

      -- Mock vim.api functions needed
      local orig_win_get_config = vim.api.nvim_win_get_config
      local orig_win_get_position = vim.api.nvim_win_get_position
      local orig_buf_clear_namespace = vim.api.nvim_buf_clear_namespace

      vim.api.nvim_win_get_config = function(win)
        return { border = "none" }
      end
      vim.api.nvim_win_get_position = function(win)
        return { 5, 10 }
      end
      vim.api.nvim_buf_clear_namespace = function() end

      override.iterm2_render_fallback(mock_placement, state)

      -- render_fallback registers in M._active and schedules a paint.
      -- Verify the sequence was registered correctly (decoration_provider handles repainting).
      local pid = tostring(mock_placement.buf) .. ":" .. tostring(mock_placement.id)
      local entry = override._active[pid]
      eq(true, entry ~= nil, "should have registered placement in _active")
      if entry then
        eq(true, entry.seq:find("\x1b]1337;File=") ~= nil, "seq should contain iTerm2 escape")
        contains(entry.seq, "width=20")
        contains(entry.seq, "height=10")
        eq(20, entry.width)
        eq(10, entry.height)
      end

      vim.api.nvim_win_get_config = orig_win_get_config
      vim.api.nvim_win_get_position = orig_win_get_position
      vim.api.nvim_buf_clear_namespace = orig_buf_clear_namespace

      os.remove(tmpfile)
    end)
  end)

  describe("detect_terminal", function()
    it("detects WezTerm from TERM_PROGRAM", function()
      local orig = vim.env.TERM_PROGRAM
      vim.env.TERM_PROGRAM = "WezTerm"
      eq(true, override.detect_terminal())
      vim.env.TERM_PROGRAM = orig
    end)

    it("detects iTerm2 from TERM_PROGRAM", function()
      local orig = vim.env.TERM_PROGRAM
      vim.env.TERM_PROGRAM = "iTerm.app"
      eq(true, override.detect_terminal())
      vim.env.TERM_PROGRAM = orig
    end)

    it("returns false for unknown terminal", function()
      local orig = vim.env.TERM_PROGRAM
      vim.env.TERM_PROGRAM = "xterm"
      eq(false, override.detect_terminal())
      vim.env.TERM_PROGRAM = orig
    end)
  end)
end)
