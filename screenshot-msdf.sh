#!/bin/bash
# screenshot-msdf.sh - Headless Screenshot für msdf_test
# Verwendet ImageMagick import statt glReadPixels (funktioniert mit llvmpipe)

OUT_FILE="${1:-screenshots/msdf-test.png}"
WIDTH=1024
HEIGHT=768
DISPLAY_NUM=99

echo "=== MSDF Test Screenshot (Xvfb :$DISPLAY_NUM) ==="

EXE_PATH="./zig-out/bin/msdf_test"
if [ ! -f "$EXE_PATH" ]; then
    echo "Error: $EXE_PATH not found! Bitte zuerst bauen."
    exit 1
fi

mkdir -p "$(dirname "$OUT_FILE")"

# Xvfb cleanup bei Exit
cleanup() {
    [ -n "$XVFB_PID" ] && kill -9 $XVFB_PID 2>/dev/null
    wait $XVFB_PID 2>/dev/null
}
trap cleanup EXIT

# Xvfb starten
Xvfb :$DISPLAY_NUM -screen 0 "${WIDTH}x${HEIGHT}x24" -nolisten tcp -noreset -ac 2>/dev/null &
XVFB_PID=$!
sleep 1

if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "Error: Xvfb failed to start!"
    exit 1
fi

export DISPLAY=:$DISPLAY_NUM

# App im Hintergrund starten (ohne --headless damit sie weiterläuft)
echo "Starting msdf_test..."
$EXE_PATH 2>&1 &
APP_PID=$!

# Warten bis App fertig gerendert hat (mehrere Frames für korrektes Rendering)
sleep 2

# Screenshot mit ImageMagick import (liest vom X-Server, nicht glReadPixels!)
if command -v import &> /dev/null; then
    echo "Taking screenshot with ImageMagick import..."
    import -window root "$OUT_FILE"
    RESULT=$?
    if [ $RESULT -eq 0 ]; then
        echo "Screenshot saved: $OUT_FILE"
    else
        echo "Import failed with code $RESULT"
    fi
else
    echo "Error: ImageMagick 'import' not found"
    echo "Install: sudo dnf install ImageMagick"
    RESULT=1
fi

# App beenden
kill $APP_PID 2>/dev/null
wait $APP_PID 2>/dev/null

echo "Done."
ls -la "$OUT_FILE" 2>/dev/null

exit ${RESULT:-0}
