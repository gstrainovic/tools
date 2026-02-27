--- iTerm2 OSC 1337 Image Protocol implementation
--- Spec: https://iterm2.com/documentation-images.html
local M = {}

--- Build an iTerm2 OSC 1337 image escape sequence from pre-encoded base64 data.
---@param base64_data string Base64-encoded image data
---@param opts {width?: number|string, height?: number|string, size?: number, name?: string}
---@return string
function M.build_image_sequence(base64_data, opts)
  local params = {
    "inline=1",
    "preserveAspectRatio=1",
    "doNotMoveCursor=1",
  }
  if opts.size then
    params[#params + 1] = string.format("size=%d", opts.size)
  end
  params[#params + 1] = string.format("width=%s", opts.width or "auto")
  params[#params + 1] = string.format("height=%s", opts.height or "auto")
  if opts.name then
    params[#params + 1] = "name=" .. vim.base64.encode(opts.name)
  end
  return string.format("\x1b]1337;File=%s:%s\x07", table.concat(params, ";"), base64_data)
end

--- iTerm2 has no explicit image clear command.
---@return string
function M.build_clear_sequence()
  return ""
end

--- Read a file and build an iTerm2 image sequence.
---@param filepath string Path to the image file
---@param opts {width?: number|string, height?: number|string, name?: string}
---@return string|nil sequence, string|nil error
function M.build_file_sequence(filepath, opts)
  local fd = io.open(filepath, "rb")
  if not fd then
    return nil
  end
  local data = fd:read("*a")
  fd:close()

  local base64_data = vim.base64.encode(data)
  opts.size = #data
  if not opts.name then
    opts.name = vim.fn.fnamemodify(filepath, ":t")
  end
  return M.build_image_sequence(base64_data, opts)
end

return M
