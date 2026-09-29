#!/bin/bash
# leerlauf-aus-installieren.sh <user@host> — richtet leerlauf-aus.sh als systemd-Timer (alle 10 Minuten)
# auf einer Dev-Instanz ein. Nie auf Produktion oder find-jobs-lauf (die laufen ohne SSH-Verbindung).
set -euo pipefail
HOST=${1:?Aufruf: leerlauf-aus-installieren.sh user@host}
DIR="$(cd "$(dirname "$0")" && pwd)"
scp -q "$DIR/leerlauf-aus.sh" "$HOST:/tmp/leerlauf-aus"
ssh "$HOST" 'sudo install -m 755 /tmp/leerlauf-aus /usr/local/sbin/leerlauf-aus && rm /tmp/leerlauf-aus
sudo tee /etc/systemd/system/leerlauf-aus.service >/dev/null <<EOF
[Unit]
Description=Dev-Instanz nach Leerlauf abschalten
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/leerlauf-aus
EOF
sudo tee /etc/systemd/system/leerlauf-aus.timer >/dev/null <<EOF
[Unit]
Description=Leerlauf alle 10 Minuten prüfen
[Timer]
OnBootSec=10min
OnUnitActiveSec=10min
[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now leerlauf-aus.timer
systemctl list-timers leerlauf-aus.timer --no-pager | head -3'
