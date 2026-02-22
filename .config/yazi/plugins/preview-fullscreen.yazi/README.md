# preview-fullscreen.yazi

Automatically maximize preview panel for images and PDFs.

When yazi reveals a binary file (image/PDF), the preview panel expands to fullscreen.
Navigate away to restore normal layout.

## Usage

Add to `~/.config/yazi/init.lua`:

```lua
require("preview-fullscreen"):entry()
```

Or bind to a key in `keymap.toml`:

```toml
{ on = "<C-f>", run = "plugin preview-fullscreen", desc = "Toggle preview fullscreen" }
```
