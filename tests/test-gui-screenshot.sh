#!/usr/bin/env bash
# gui-screenshot muss auch bei vielen vorhandenen Bildschirmfotos ein neues finden
# (ls | head unter pipefail brach sonst mit SIGPIPE, Exit 141, ab).
set -euo pipefail

TOOLS="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
mkdir -p "$HOME/Bilder/Bildschirmfotos" "$TMP/bin"
for i in $(seq 1 3000); do
    touch -d "2026-01-01" "$HOME/Bilder/Bildschirmfotos/alt-$i.png"
done

# Falsches ydotool: legt ein neues Bildschirmfoto an
cat > "$TMP/bin/ydotool" <<EOF
#!/usr/bin/env bash
touch "$HOME/Bilder/Bildschirmfotos/neu.png"
EOF
chmod +x "$TMP/bin/ydotool"

export YDOTOOL_SOCKET="$TMP/sock"
python3 -c "import socket,sys; socket.socket(socket.AF_UNIX).bind(sys.argv[1])" "$YDOTOOL_SOCKET"

AUSGABE="$(PATH="$TMP/bin:$PATH" bash "$TOOLS/gui-screenshot.sh" "$TMP/ziel.png")" || {
    echo "FEHLER: gui-screenshot endete mit Exit $?"; exit 1; }
[[ "$AUSGABE" == "$TMP/ziel.png" && -f "$TMP/ziel.png" ]] || {
    echo "FEHLER: erwartet $TMP/ziel.png, bekommen «$AUSGABE»"; exit 1; }
echo "OK: gui-screenshot findet das neue Bild"
