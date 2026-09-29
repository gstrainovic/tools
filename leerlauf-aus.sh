#!/bin/bash
# leerlauf-aus.sh — schaltet eine Dev-Instanz ab, wenn LEERLAUF_MINUTEN lang keine SSH-Verbindung
# (Shell oder Tunnel) bestand. Läuft auf der Instanz per systemd-Timer alle 10 Minuten
# (Einrichtung: leerlauf-aus-installieren.sh). Ausgeschaltet zahlt Infomaniak keine CPU/RAM mehr;
# den Rest (Disk) spart das Zurückstellen durch den Kostenwächter auf dem Laptop.
# Aufwecken: dev-instanz-wecken.sh <name>.
set -euo pipefail
STAMP=${STAMP:-/var/lib/leerlauf-aus/aktiv}
SS_CMD=${SS_CMD:-ss}
AUS_CMD=${AUS_CMD:-/usr/sbin/poweroff}
LEERLAUF_MINUTEN=${LEERLAUF_MINUTEN:-120}

mkdir -p "$(dirname "$STAMP")"
if [[ ! -f "$STAMP" ]] || "$SS_CMD" -Htn state established '( sport = :22 )' | grep -q .; then
    touch "$STAMP"
    exit 0
fi
if [[ -n "$(find "$STAMP" -mmin +"$LEERLAUF_MINUTEN")" ]]; then
    echo "Seit $LEERLAUF_MINUTEN Minuten keine SSH-Verbindung, schalte ab"
    rm -f "$STAMP"  # nach dem Start zählt der Leerlauf neu
    "$AUS_CMD"
fi
