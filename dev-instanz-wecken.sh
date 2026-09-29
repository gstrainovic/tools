#!/bin/bash
# dev-instanz-wecken.sh <name> — startet eine abgeschaltete (SHUTOFF) oder zurückgestellte (SHELVED)
# Dev-Instanz im OpenStack-Projekt PCP-CTPZLR8 und wartet, bis SSH antwortet. Läuft sie schon, tut es nichts.
# Braucht ~/.config/openstack/clouds.yaml und das openstack-CLI.
set -euo pipefail
NAME=${1:?Aufruf: dev-instanz-wecken.sh <name>}
C=(--os-cloud "${OS_CLOUD_NAME:-PCP-CTPZLR8-dc3-a}")
status() { openstack "${C[@]}" server show "$NAME" -f value -c status; }
s=$(status)
case "$s" in
    ACTIVE) ;;
    SHUTOFF) echo "$NAME ist aus, starte"; openstack "${C[@]}" server start "$NAME" ;;
    SHELVED|SHELVED_OFFLOADED) echo "$NAME ist zurückgestellt, hole zurück (einige Minuten)"; openstack "${C[@]}" server unshelve "$NAME" ;;
    *) echo "$NAME hat Status $s, warte" ;;
esac
for _ in $(seq 1 90); do [[ "$(status)" == ACTIVE ]] && break; sleep 10; done
[[ "$(status)" == ACTIVE ]] || { echo "$NAME nicht ACTIVE: $(status)"; exit 1; }
ip=$(openstack "${C[@]}" server show "$NAME" -f json -c addresses | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)
for _ in $(seq 1 60); do (echo > "/dev/tcp/$ip/22") 2>/dev/null && break; sleep 5; done
(echo > "/dev/tcp/$ip/22") 2>/dev/null || { echo "$NAME ACTIVE, aber SSH auf $ip antwortet nicht"; exit 1; }
# Fehlt die Leerlauf-Abschaltung (neu aufgesetzte Instanz), gleich einrichten
if ! ssh -o BatchMode=yes "debian@$ip" test -x /usr/local/sbin/leerlauf-aus; then
    "$(dirname "$0")/leerlauf-aus-installieren.sh" "debian@$ip" >/dev/null && echo "Leerlauf-Abschaltung auf $NAME eingerichtet"
fi
echo "$NAME bereit: $ip"
