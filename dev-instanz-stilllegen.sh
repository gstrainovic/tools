#!/bin/bash
# dev-instanz-stilllegen.sh [--dry-run] <name> — legt eine Dev-Instanz im OpenStack-Projekt PCP-CTPZLR8 still,
# sodass sie nichts mehr kostet ausser dem Image (Abgelegte, also shelved Instanzen zahlen bei Infomaniak weiter
# ihre IPv4, und Netz abhängen lehnt Nova bei SHELVED_OFFLOADED ab):
#   1. ausschalten, falls nötig (abgelegte erst zurückholen, Nova erstellt von ihnen kein Image)
#   2. Image <name>-sicherung-<JJJJMMTT> erstellen und warten, bis es active ist
#   3. Image schützen, erst dann die Instanz löschen
#   4. ältere Sicherungen desselben Namens entschützen und löschen, sodass eine bleibt
# Zurück holt sie dev-instanz-wecken.sh <name> (neue IPv4). Bricht ein Schritt ab, bleibt die Instanz bestehen.
# --dry-run führt nur lesende openstack-Befehle aus und zeigt die ändernden an.
set -euo pipefail
TROCKEN=0; [[ "${1:-}" == --dry-run ]] && { TROCKEN=1; shift; }
NAME=${1:?Aufruf: dev-instanz-stilllegen.sh [--dry-run] <name>}
C=(--os-cloud "${OS_CLOUD_NAME:-PCP-CTPZLR8-dc3-a}")
WARTE=${WARTE:-10}

os() { openstack "${C[@]}" "$@"; }
aendern() {  # ändernder openstack-Befehl, im Trockenlauf nur angezeigt
    if (( TROCKEN )); then echo "TROCKEN: openstack ${C[*]} $*"; else os "$@"; fi
}
status() { os server list --name "^$NAME\$" -f value -c Status; }
warte_status() {  # warte_status <ziel> <versuche>
    (( TROCKEN )) && return 0
    for _ in $(seq 1 "$2"); do [[ "$(status)" == "$1" ]] && return 0; sleep "$WARTE"; done
    echo "$NAME erreicht $1 nicht (Status $(status))" >&2; exit 1
}

# Nie zwei Läufe für dieselbe Instanz (der Kostenwächter startet das Skript im Hintergrund)
SPERRE="${TMPDIR:-/tmp}/dev-instanz-stilllegen-$NAME.sperre"
if (( ! TROCKEN )); then
    mkdir "$SPERRE" 2>/dev/null || { echo "$NAME wird schon stillgelegt ($SPERRE)"; exit 0; }
    trap 'rmdir "$SPERRE"' EXIT
fi

s=$(status)
case "$s" in
    "") echo "$NAME gibt es nicht (schon stillgelegt?)" >&2; exit 1 ;;
    SHUTOFF) ;;
    ACTIVE)
        # Leerlauf-Stempel entfernen, sonst schaltet leerlauf-aus die neu angelegte Instanz gleich wieder ab
        (( TROCKEN )) || ${SSH:-ssh} -o BatchMode=yes -o ConnectTimeout=10 "debian@$(os server show "$NAME" -f json -c addresses \
            | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)" sudo rm -f /var/lib/leerlauf-aus/aktiv || true
        aendern server stop "$NAME"; warte_status SHUTOFF 60 ;;
    SHELVED|SHELVED_OFFLOADED)
        aendern server unshelve "$NAME"; warte_status ACTIVE 90
        aendern server stop "$NAME"; warte_status SHUTOFF 60 ;;
    *) echo "$NAME hat Status $s, stilllegen nur aus ACTIVE, SHUTOFF oder SHELVED" >&2; exit 1 ;;
esac

alle=$(os image list --private -f value -c ID -c Name)
img="$NAME-sicherung-$(date +%Y%m%d)"
awk -v n="$img" '$2 == n {f=1} END {exit !f}' <<< "$alle" && img="$img-$(date +%H%M)"
echo "Erstelle Image $img (bei 50 GB rund 10 bis 30 Minuten)"
if (( TROCKEN )); then
    aendern server image create --name "$img" "$NAME" -f value -c id; id="<id-von-$img>"
else
    id=$(os server image create --name "$img" "$NAME" -f value -c id)
    for _ in $(seq 1 360); do
        st=$(os image show "$id" -f value -c status)
        case "$st" in active) break ;; queued|saving|uploading|importing) sleep "$WARTE" ;;
            *) echo "Image $img hat Status $st, Instanz $NAME bleibt bestehen" >&2; exit 1 ;; esac
    done
    [[ "$st" == active ]] || { echo "Image $img nach Wartezeit nicht active ($st), Instanz $NAME bleibt bestehen" >&2; exit 1; }
fi
aendern image set --protected "$id"
if (( ! TROCKEN )) && [[ "$(os image show "$id" -f value -c protected)" != True ]]; then
    echo "Image $img ist nicht geschützt, Instanz $NAME bleibt bestehen" >&2; exit 1
fi
aendern server delete --wait "$NAME"
(( TROCKEN )) || echo "$NAME gelöscht, Sicherung $img"

# Ältere Sicherungen derselben Instanz weg; «dms-sicherung-» trifft «dms-dev-sicherung-» nicht
while read -r altid altname; do
    [[ -z "$altid" || "$altid" == "$id" ]] && continue
    aendern image set --unprotected "$altid"
    aendern image delete "$altid"
    (( TROCKEN )) || echo "ältere Sicherung $altname gelöscht"
done < <(awk -v p="$NAME-sicherung-" 'index($2, p) == 1' <<< "$alle")
