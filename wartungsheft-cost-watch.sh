#!/bin/bash
# Kostenwächter für das OpenStack-Projekt PCP-CTPZLR8 (Infomaniak Public Cloud bietet keine Budget-Alarme).
# Läuft bei jedem Akquise-Lauf auf dem Laptop über find-jobs/automation/wartungsheft-tagescheck, schätzt die
# Monatskosten aus den laufenden Ressourcen und mailt über Resend, wenn die Schätzung über dem Limit liegt,
# unbekannte Ressourcen auftauchen oder das Startguthaben ausläuft.
# Zugang: ~/.config/openstack/clouds.yaml (Application Credential), Mail: ~/.config/resend/token.
# Preise CHF/Stunde laut Infomaniak-Preisliste (September 2026); unbekannte Flavors lösen einen Alarm aus.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
CLOUD=PCP-CTPZLR8-dc3-a
LIMIT_CHF=${LIMIT_CHF:-60}  # Produktion und Dev-Instanzen wartungsheft-dev und dms-dev (je rund 13.5 CHF laufend) plus Suchlauf find-jobs-lauf (a2-ram4-disk20, rund 11 CHF mit IPv4); Reserve für Snapshots und IPv4
MAIL_TO=${MAIL_TO:-g.strainovic@gmail.com}
CREDIT_END=2026-12-31
HOURS=730
IPV4_H=0.00457
SNAPSHOT_GB_MONTH=0.011
FLAVORS="a1-ram2-disk20-perf1=0.0064 a2-ram4-disk20-perf1=0.01043 a2-ram4-disk50-perf1=0.01399 a4-ram8-disk50-perf1=0.02798"

# Dev-Instanzen schalten sich nach Leerlauf selbst ab (tools/leerlauf-aus.sh); abgeschaltet zahlen sie
# noch die Disk, zurückgestellt nur noch Snapshot und IPv4. Aufwecken: tools/dev-instanz-wecken.sh <name>.
DEV_INSTANZEN="wartungsheft-dev dms-dev"
for n in $DEV_INSTANZEN; do
  [ "$(openstack --os-cloud $CLOUD server show "$n" -f value -c status 2>/dev/null)" = SHUTOFF ] \
    && openstack --os-cloud $CLOUD server shelve "$n" && echo "$n abgeschaltet, zurückgestellt"
done
servers=$(openstack --os-cloud $CLOUD server list --long -f json)
images=$(openstack --os-cloud $CLOUD image list --private --long -f json)
volumes=$(openstack --os-cloud $CLOUD volume list -f json)
fips=$(openstack --os-cloud $CLOUD floating ip list -f json)

report=$(SERVERS="$servers" IMAGES="$images" VOLUMES="$volumes" FIPS="$fips" HOURS=$HOURS IPV4_H=$IPV4_H SNAP=$SNAPSHOT_GB_MONTH FLAVORS="$FLAVORS" python3 - <<'EOF'
import json, os, re
flavors = dict(kv.split("=") for kv in os.environ["FLAVORS"].split())
hours = float(os.environ["HOURS"]); ipv4 = float(os.environ["IPV4_H"]); snap = float(os.environ["SNAP"])
total = 0.0; lines = []; alerts = []
for s in json.loads(os.environ["SERVERS"]):
    name = s.get("Flavor Name") or s.get("Flavor") or "?"
    nets = s.get("Networks") or {}
    if isinstance(nets, str):
        ips = len(re.findall(r"\b\d+\.\d+\.\d+\.\d+\b", nets))
    else:
        ips = sum(1 for v in nets.values() for a in v if re.match(r"\d+\.\d+\.\d+\.\d+$", a))
    price = flavors.get(name)
    if price is None:
        alerts.append(f"Unbekannter Flavor {name} bei Instanz {s['Name']}")
        continue
    # Geshelvte Instanzen zahlen weder CPU/RAM noch Ceph-Disk, nur den Snapshot (taucht in der Image-Liste auf) und die IPv4
    compute = 0.0 if str(s.get("Status", "")).startswith("SHELVED") else float(price) * hours
    cost = compute + ips * ipv4 * hours
    total += cost
    lines.append(f"Instanz {s['Name']} ({name}, {s['Status']}, {ips} IPv4): {cost:.2f} CHF")
gb = sum((i.get("Size") or 0) for i in json.loads(os.environ["IMAGES"])) / 1e9
cost = gb * snap; total += cost
lines.append(f"Snapshots/Images {gb:.1f} GB: {cost:.2f} CHF")
vols = json.loads(os.environ["VOLUMES"])
if vols:
    alerts.append(f"{len(vols)} Volume(s) vorhanden, nicht eingeplant: " + ", ".join(v.get("Name") or v["ID"] for v in vols))
fips = json.loads(os.environ["FIPS"])
if fips:
    alerts.append(f"{len(fips)} Floating IP(s) vorhanden, nicht eingeplant")
lines.append(f"Geschätzt pro Monat: {total:.2f} CHF")
print(json.dumps({"total": round(total, 2), "lines": lines, "alerts": alerts}))
EOF
)
total=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['total'])" "$report")
alerts=$(python3 -c "import json,sys;print('\n'.join(json.loads(sys.argv[1])['alerts']))" "$report")
body=$(python3 -c "import json,sys;print('\n'.join(json.loads(sys.argv[1])['lines']))" "$report")

today=$(date +%F)
if [[ "$today" > "2026-12-01" && "$today" < "$CREDIT_END" ]]; then
  alerts+=$'\n'"Startguthaben 300 CHF läuft am $CREDIT_END aus, danach Kreditkarte."
fi
over=$(python3 -c "print(int(float('$total') > float('$LIMIT_CHF')))")
echo "$(date -Is) total=$total limit=$LIMIT_CHF"
echo "$body"
[ -n "$alerts" ] && echo "$alerts"
if [ "${1:-}" != "--force" ]; then
  [ "$over" = 1 ] || [ -n "$(echo -n "$alerts" | tr -d '[:space:]')" ] || exit 0
fi

subject="Wartungsheft Cloud: $( [ "$over" = 1 ] && echo "Kosten über Limit ($total > $LIMIT_CHF CHF)" || echo "Ressourcen-Hinweis" )"
text="Kostenwächter (OpenStack-Projekt PCP-CTPZLR8, Laptop-Timer)"$'\n\n'"$body"$'\n\n'"$alerts"
RESEND_TOKEN=$(tr -d '\n' < "$HOME/.config/resend/token")
curl -fsS -m 30 -X POST -H "Authorization: Bearer $RESEND_TOKEN" -H "Content-Type: application/json" https://api.resend.com/emails \
  -d "$(python3 -c "import json,sys;print(json.dumps({'from':'Wartungsheft <login@wartungsheft.ch>','to':[sys.argv[1]],'subject':sys.argv[2],'text':sys.argv[3]}))" "$MAIL_TO" "$subject" "$text")" >/dev/null
echo "Alarm-Mail gesendet an $MAIL_TO"
