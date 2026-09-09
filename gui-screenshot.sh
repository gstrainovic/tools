#!/usr/bin/env bash
# GUI Screenshot via ydotool (GNOME Wayland).
# Simulates Shift+Print to trigger GNOME's built-in screenshot.
# Prints the path of the new screenshot file.
#
# Usage:
#   gui-screenshot [output_path]
#
# Requires: ydotool, ydotoold (started automatically with sudo if needed)

set -euo pipefail

YDOTOOL_SOCKET="${YDOTOOL_SOCKET:-/tmp/.ydotool_socket}"
SCREENSHOT_DIR="$HOME/Bilder/Bildschirmfotos"
OUTPUT_PATH="${1:-}"

# Ensure ydotoold is running
if [[ ! -S "$YDOTOOL_SOCKET" ]]; then
    if ! command -v ydotoold &>/dev/null; then
        echo "ERROR: ydotoold not found. Install ydotool." >&2
        exit 1
    fi
    sudo ydotoold --socket-path "$YDOTOOL_SOCKET" --socket-perm 666 &
    sleep 1
    if [[ ! -S "$YDOTOOL_SOCKET" ]]; then
        echo "ERROR: Failed to start ydotoold" >&2
        exit 1
    fi
fi

export YDOTOOL_SOCKET

# Remember newest screenshot before taking one
BEFORE=$(ls -t "$SCREENSHOT_DIR"/*.png 2>/dev/null | head -1)

# Simulate Shift+Print (keycodes: 42=LShift, 99=SysRq/Print)
ydotool key 42:1 99:1 99:0 42:0

# Wait for new file to appear (max 5 seconds)
for i in $(seq 1 50); do
    sleep 0.1
    AFTER=$(ls -t "$SCREENSHOT_DIR"/*.png 2>/dev/null | head -1)
    if [[ -n "$AFTER" && "$AFTER" != "$BEFORE" ]]; then
        if [[ -n "$OUTPUT_PATH" ]]; then
            mkdir -p "$(dirname "$OUTPUT_PATH")"
            mv "$AFTER" "$OUTPUT_PATH"
            echo "$OUTPUT_PATH"
        else
            echo "$AFTER"
        fi
        exit 0
    fi
done

echo "ERROR: No new screenshot appeared within 5 seconds" >&2
exit 1
