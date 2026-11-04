#!/bin/bash
# dev-instanz-wecken.sh [--dry-run] <name> — macht eine Dev-Instanz im OpenStack-Projekt PCP-CTPZLR8 bereit und
# wartet, bis SSH antwortet; die letzte Zeile nennt die IP («<name> bereit: <ip>»).
#   - gibt es sie nicht (stillgelegt per dev-instanz-stilllegen.sh): aus der neuesten Sicherung <name>-sicherung-*
#     neu anlegen (Flavor, Keypair, Security Group und Netz unten); die IPv4 ist danach eine neue
#   - SHUTOFF: starten; SHELVED/SHELVED_OFFLOADED (alter Stand): zurückholen; ACTIVE: nichts tun
# --dry-run führt nur lesende openstack-Befehle aus und zeigt die ändernden an.
# Braucht ~/.config/openstack/clouds.yaml und das openstack-CLI.
set -euo pipefail
TROCKEN=0; [[ "${1:-}" == --dry-run ]] && { TROCKEN=1; shift; }
NAME=${1:?Aufruf: dev-instanz-wecken.sh [--dry-run] <name>}
C=(--os-cloud "${OS_CLOUD_NAME:-PCP-CTPZLR8-dc3-a}")
FLAVOR=${DEV_FLAVOR:-a2-ram4-disk50-perf1}
KEY=${DEV_KEY:-claude-laptop}
SECGROUP=${DEV_SECGROUP:-default}
NETZ=${DEV_NETZ:-ext-net1}
WARTE=${WARTE:-10}

status() { openstack "${C[@]}" server list --name "^$NAME\$" -f value -c Status; }
aendern() {  # ändernder openstack-Befehl, im Trockenlauf nur angezeigt
    if (( TROCKEN )); then echo "TROCKEN: openstack ${C[*]} $*"; else openstack "${C[@]}" "$@" >/dev/null; fi
}

s=$(status)
case "$s" in
    "")
        img=$(openstack "${C[@]}" image list --private -f value -c ID -c Name \
            | awk -v p="$NAME-sicherung-" 'index($2, p) == 1 && $2 > m {m = $2} END {print m}')
        [[ -n "$img" ]] || { echo "$NAME gibt es nicht, und es gibt keine Sicherung $NAME-sicherung-*" >&2; exit 1; }
        echo "$NAME ist stillgelegt, lege neu an aus $img (einige Minuten)"
        aendern server create --image "$img" --flavor "$FLAVOR" --key-name "$KEY" --security-group "$SECGROUP" \
            --network "$NETZ" --wait "$NAME" ;;
    ACTIVE) ;;
    SHUTOFF) echo "$NAME ist aus, starte"; aendern server start "$NAME" ;;
    SHELVED|SHELVED_OFFLOADED) echo "$NAME ist abgelegt, hole zurück (einige Minuten)"; aendern server unshelve "$NAME" ;;
    *) echo "$NAME hat Status $s, warte" ;;
esac
if (( TROCKEN )); then echo "TROCKEN: danach warten bis ACTIVE und SSH, IP aus openstack server show $NAME"; exit 0; fi

for _ in $(seq 1 90); do [[ "$(status)" == ACTIVE ]] && break; sleep "$WARTE"; done
[[ "$(status)" == ACTIVE ]] || { echo "$NAME nicht ACTIVE: $(status)"; exit 1; }
ip=$(openstack "${C[@]}" server show "$NAME" -f json -c addresses | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)
for _ in $(seq 1 60); do (echo > "/dev/tcp/$ip/22") 2>/dev/null && break; sleep "$WARTE"; done
(echo > "/dev/tcp/$ip/22") 2>/dev/null || { echo "$NAME ACTIVE, aber SSH auf $ip antwortet nicht"; exit 1; }
# Neu angelegte Instanz: neue IP und neuer Host-Schlüssel, darum accept-new
SSH_OPT=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new)
# Fehlt die Leerlauf-Abschaltung (neu aufgesetzte Instanz), gleich einrichten
if ! ssh "${SSH_OPT[@]}" "debian@$ip" test -x /usr/local/sbin/leerlauf-aus; then
    "$(dirname "$0")/leerlauf-aus-installieren.sh" "debian@$ip" >/dev/null && echo "Leerlauf-Abschaltung auf $NAME eingerichtet"
fi
echo "$NAME bereit: $ip"
