-- Minimal test runner for nvim headless
-- Usage: nvim --headless -u NONE -l tests/run.lua

local passed = 0
local failed = 0
local errors = {}

local function describe(name, fn)
  print("  " .. name)
  fn()
end

local function it(name, fn)
  local ok, err = pcall(fn)
  if ok then
    passed = passed + 1
    print("    ✓ " .. name)
  else
    failed = failed + 1
    table.insert(errors, { name = name, err = err })
    print("    ✗ " .. name)
    print("      " .. tostring(err))
  end
end

local function eq(expected, actual, msg)
  if expected ~= actual then
    error(string.format("%s\n  expected: %s\n  actual:   %s", msg or "assertion failed", tostring(expected), tostring(actual)), 2)
  end
end

local function contains(haystack, needle, msg)
  if not haystack:find(needle, 1, true) then
    error(string.format("%s\n  expected to contain: %s\n  in: %s", msg or "contains failed", needle, haystack), 2)
  end
end

local function starts_with(str, prefix, msg)
  if str:sub(1, #prefix) ~= prefix then
    error(string.format("%s\n  expected to start with: %q\n  got: %q", msg or "starts_with failed", prefix, str:sub(1, #prefix + 10)), 2)
  end
end

-- Export test helpers globally
_G.describe = describe
_G.it = it
_G.eq = eq
_G.contains = contains
_G.starts_with = starts_with

-- Add plugin to runtimepath
vim.opt.rtp:prepend(vim.fn.fnamemodify(".", ":p"))

-- Run test files
local test_files = vim.fn.glob("tests/*_spec.lua", false, true)
table.sort(test_files)

for _, file in ipairs(test_files) do
  print("\n" .. file .. ":")
  dofile(file)
end

-- Summary
print(string.format("\n%d passed, %d failed", passed, failed))
if failed > 0 then
  vim.cmd("cquit 1")
else
  vim.cmd("quit")
end
