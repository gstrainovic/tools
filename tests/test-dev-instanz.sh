#!/bin/bash
# tests/test-dev-instanz.sh — Dev-Instanz stilllegen (Image, schützen, erst dann löschen) und aus dem Image wecken.
# Läuft gegen eine openstack-Attrappe, die Zustand in Dateien hält und jede Änderung protokolliert.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
pruefe() { if eval "$2"; then pass "$1"; else fail "$1"; fi; }

# Attrappe: Server unter $W/server/<name> (Inhalt = Status), Images unter $W/images/<id>/{name,status,protected},
# Änderungen nach $W/log. $W/neues-image-status bestimmt, welchen Status ein neues Image bekommt.
cat > "$TMP/openstack" <<'EOF'
#!/bin/bash
W="$ATTRAPPE"
[[ "$1" == --os-cloud ]] && shift 2
log() { echo "$*" >> "$W/log"; }
case "$1 $2" in
  "server list")
    n="${4#^}"; n="${n%\$}"; [[ -f "$W/server/$n" ]] && cat "$W/server/$n"; exit 0 ;;
  "server show")
    echo '{"addresses": {"ext-net1": ["2001:1600::1", "195.15.1.2"]}}' ;;
  "server start"|"server unshelve")
    log "$1 $2 $3"; echo ACTIVE > "$W/server/$3" ;;
  "server stop")
    log "$1 $2 $3"; echo SHUTOFF > "$W/server/$3" ;;
  "server delete")
    n="${*: -1}"; log "server delete $n"; rm -f "$W/server/$n" ;;
  "server create")
    n="${*: -1}"; log "server create $*"; echo ACTIVE > "$W/server/$n" ;;
  "server image")
    # server image create --name <img> <server> -f value -c id
    id="img$(( $(ls "$W/images" | wc -l) + 1 ))"; mkdir -p "$W/images/$id"
    echo "$5" > "$W/images/$id/name"; cat "$W/neues-image-status" > "$W/images/$id/status"
    echo False > "$W/images/$id/protected"; log "image create $5 von $6"; echo "$id" ;;
  "image show")
    f="${*: -1}"; cat "$W/images/$3/$f" ;;
  "image list")
    for d in "$W"/images/*/; do [[ -d "$d" ]] && echo "$(basename "$d") $(cat "$d/name")"; done; exit 0 ;;
  "image set")
    log "image set $3 $4"; [[ "$3" == --protected ]] && echo True > "$W/images/$4/protected"
    [[ "$3" == --unprotected ]] && echo False > "$W/images/$4/protected"; exit 0 ;;
  "image delete")
    [[ "$(cat "$W/images/$3/protected")" == True ]] && { echo "geschützt" >&2; exit 1; }
    log "image delete $3"; rm -rf "$W/images/$3" ;;
  *) echo "Attrappe kennt $* nicht" >&2; exit 2 ;;
esac
EOF
chmod +x "$TMP/openstack"
printf '#!/bin/bash\necho "ssh $*" >> "$ATTRAPPE/log"\n' > "$TMP/ssh"; chmod +x "$TMP/ssh"

neu() {  # frische Welt
  W="$TMP/welt$((++WELT))"; mkdir -p "$W/server" "$W/images"; : > "$W/log"; echo active > "$W/neues-image-status"
}
WELT=0
image() {  # image <id> <name> <protected>
  mkdir -p "$W/images/$1"; echo "$2" > "$W/images/$1/name"; echo active > "$W/images/$1/status"; echo "$3" > "$W/images/$1/protected"
}
lauf() { ATTRAPPE="$W" PATH="$TMP:$PATH" WARTE=0 "$ROOT/$@" > "$W/aus" 2>&1; }

# 1: stilllegen einer abgeschalteten Instanz: Image, schützen, löschen, ältere Sicherung weg, fremde bleiben
neu; echo SHUTOFF > "$W/server/dms-dev"
image alt1 dms-dev-sicherung-20261001 True; image fremd dms-sicherung-20261001 True; image wh wartungsheft-dev-sicherung-20261104 True
lauf dev-instanz-stilllegen.sh dms-dev; rc=$?
pruefe "stilllegen endet ohne Fehler" '[[ $rc -eq 0 ]]'
pruefe "Image vor dem Löschen erstellt und geschützt" \
  '[[ "$(grep -n "image create dms-dev-sicherung-" "$W/log" | cut -d: -f1)" -lt "$(grep -n "server delete dms-dev" "$W/log" | cut -d: -f1)" && "$(grep -n "image set --protected img" "$W/log" | cut -d: -f1)" -lt "$(grep -n "server delete dms-dev" "$W/log" | cut -d: -f1)" ]]'
pruefe "Instanz gelöscht" '[[ ! -f "$W/server/dms-dev" ]]'
pruefe "neue Sicherung bleibt geschützt" '[[ "$(cat "$W"/images/img*/protected)" == True ]]'
pruefe "ältere Sicherung desselben Namens gelöscht" '[[ ! -d "$W/images/alt1" ]]'
pruefe "Sicherungen anderer Instanzen bleiben" '[[ -d "$W/images/fremd" && -d "$W/images/wh" ]]'

# 2: Image wird nicht active: Instanz bleibt, nichts gelöscht
neu; echo SHUTOFF > "$W/server/dms-dev"; echo killed > "$W/neues-image-status"; image alt1 dms-dev-sicherung-20261001 True
lauf dev-instanz-stilllegen.sh dms-dev; rc=$?
pruefe "fehlgeschlagenes Image bricht ab" '[[ $rc -ne 0 ]]'
pruefe "Instanz bleibt bei fehlgeschlagenem Image" '[[ -f "$W/server/dms-dev" ]] && ! grep -q "server delete" "$W/log"'
pruefe "alte Sicherung bleibt bei fehlgeschlagenem Image" '[[ -d "$W/images/alt1" ]]'

# 3: laufende Instanz wird erst ausgeschaltet
neu; echo ACTIVE > "$W/server/dms-dev"
lauf dev-instanz-stilllegen.sh dms-dev
pruefe "laufende Instanz: erst stop, dann Image" \
  '[[ "$(grep -n "server stop dms-dev" "$W/log" | cut -d: -f1)" -lt "$(grep -n "image create" "$W/log" | cut -d: -f1)" ]]'

# 4: Trockenlauf ändert nichts und zeigt die Befehle
neu; echo SHUTOFF > "$W/server/dms-dev"; image alt1 dms-dev-sicherung-20261001 True
lauf dev-instanz-stilllegen.sh --dry-run dms-dev
pruefe "Trockenlauf stilllegen ändert nichts" '[[ ! -s "$W/log" && -f "$W/server/dms-dev" ]]'
pruefe "Trockenlauf stilllegen zeigt Befehle" \
  'grep -q "server image create --name dms-dev-sicherung-" "$W/aus" && grep -q "image set --protected" "$W/aus" && grep -q "server delete --wait dms-dev" "$W/aus" && grep -q "image delete alt1" "$W/aus"'

# 5: Instanz fehlt: stilllegen meldet Fehler
neu; lauf dev-instanz-stilllegen.sh dms-dev; rc=$?
pruefe "stilllegen ohne Instanz bricht ab" '[[ $rc -ne 0 && ! -s "$W/log" ]]'

# 6: wecken ohne Instanz legt sie aus der neuesten Sicherung an (Trockenlauf)
neu; image a dms-dev-sicherung-20261001 True; image b dms-dev-sicherung-20261104 True; image c dms-sicherung-20261201 True
lauf dev-instanz-wecken.sh --dry-run dms-dev; rc=$?
pruefe "Trockenlauf wecken endet ohne Fehler" '[[ $rc -eq 0 && ! -s "$W/log" ]]'
pruefe "wecken nimmt neueste Sicherung mit den festen Einstellungen" \
  'grep -q "server create --image dms-dev-sicherung-20261104 --flavor a2-ram4-disk50-perf1 --key-name claude-laptop --security-group default --network ext-net1 --wait dms-dev" "$W/aus"'

# 7: wecken ohne Instanz und ohne Sicherung bricht ab
neu; lauf dev-instanz-wecken.sh --dry-run dms-dev; rc=$?
pruefe "wecken ohne Sicherung bricht ab" '[[ $rc -ne 0 ]] && grep -q "keine Sicherung" "$W/aus"'

# 8: wecken einer abgeschalteten Instanz startet sie wie bisher (Trockenlauf)
neu; echo SHUTOFF > "$W/server/dms-dev"
lauf dev-instanz-wecken.sh --dry-run dms-dev
pruefe "wecken SHUTOFF: server start" 'grep -q "server start dms-dev" "$W/aus" && [[ ! -s "$W/log" ]]'

echo "$PASS bestanden, $FAIL fehlgeschlagen"
[[ $FAIL -eq 0 ]]
