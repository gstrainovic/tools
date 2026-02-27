local protocol = require("snacks-iterm2-image.protocol")

describe("protocol", function()
  describe("build_image_sequence", function()
    it("returns valid OSC 1337 escape sequence", function()
      local result = protocol.build_image_sequence("AQID", {})
      starts_with(result, "\x1b]1337;File=", "should start with OSC 1337")
      -- ends with ST (BEL \x07)
      eq("\x07", result:sub(-1), "should end with BEL")
    end)

    it("includes inline=1", function()
      local result = protocol.build_image_sequence("AQID", {})
      contains(result, "inline=1")
    end)

    it("includes preserveAspectRatio=1", function()
      local result = protocol.build_image_sequence("AQID", {})
      contains(result, "preserveAspectRatio=1")
    end)

    it("includes base64 data after colon", function()
      local result = protocol.build_image_sequence("AQID", {})
      contains(result, ":AQID\x07")
    end)

    it("uses width in cells format", function()
      local result = protocol.build_image_sequence("AQID", { width = 40 })
      contains(result, "width=40")
    end)

    it("uses height in cells format", function()
      local result = protocol.build_image_sequence("AQID", { height = 20 })
      contains(result, "height=20")
    end)

    it("defaults to auto for width and height", function()
      local result = protocol.build_image_sequence("AQID", {})
      contains(result, "width=auto")
      contains(result, "height=auto")
    end)

    it("includes size when provided", function()
      local result = protocol.build_image_sequence("AQID", { size = 1024 })
      contains(result, "size=1024")
    end)

    it("includes base64-encoded name when provided", function()
      local result = protocol.build_image_sequence("AQID", { name = "test.png" })
      local encoded_name = vim.base64.encode("test.png")
      contains(result, "name=" .. encoded_name)
    end)

    it("handles empty data", function()
      local result = protocol.build_image_sequence("", {})
      contains(result, ":\x07", "empty data between colon and BEL")
    end)

    it("handles large data without chunking", function()
      local large_data = string.rep("A", 10000)
      local result = protocol.build_image_sequence(large_data, {})
      contains(result, ":" .. large_data .. "\x07")
    end)
  end)

  describe("build_clear_sequence", function()
    it("returns empty string (iTerm2 has no explicit clear)", function()
      eq("", protocol.build_clear_sequence())
    end)
  end)

  describe("build_file_sequence", function()
    it("reads file and builds sequence", function()
      -- Create a temp file
      local tmpfile = vim.fn.tempname() .. ".txt"
      local f = io.open(tmpfile, "wb")
      f:write("hello")
      f:close()

      local result = protocol.build_file_sequence(tmpfile, { width = 10, height = 5 })
      starts_with(result, "\x1b]1337;File=", "should start with OSC 1337")
      contains(result, "width=10")
      contains(result, "height=5")
      -- "hello" base64 = "aGVsbG8="
      contains(result, ":aGVsbG8=\x07")

      os.remove(tmpfile)
    end)

    it("returns nil for non-existent file", function()
      local result = protocol.build_file_sequence("/tmp/nonexistent_" .. os.time(), {})
      eq(nil, result, "should return nil for missing file")
    end)
  end)
end)
