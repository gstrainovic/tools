#!/usr/bin/env bash
# Temu-Artikel ohne Captcha öffnen und URL, Titel und Preis ausgeben.
# Aufruf: temu_produkt.sh "<Produktname oder Suchbegriff>" [weitere …]
#   oder: temu_produkt.sh "<Suchbegriff>=g-<ID>"  (ID aus einem Temu-Link; dann zählt die ID, nicht der Name)
# Voraussetzung: Gorans Chrome läuft, Session gchrome angehängt (chrome-anhaengen), eigener Tab ist aktiv.
# Läufe nacheinander, nie parallel: Tastatureingaben kommen nur im sichtbaren Tab an.
set -u
hier=$(dirname "$(readlink -f "$0")")
code=$(cat "$hier/temu_produkt.js")
for q in "$@"; do
  q=${q//\'/}
  id=""
  case "$q" in *=g-*) id=${q##*=g-}; q=${q%=g-*};; esac
  echo "=== $q${id:+ (g-$id)}"
  # Fehler (### Error) werden mit ausgegeben, damit ein Abbruch sichtbar bleibt.
  js=${code//__Q__/$q}
  playwright-cli -s=gchrome run-code "${js//__ID__/$id}" 2>&1 \
    | awk '/^### Result/{f=1;next} /^### Error/{f=1} /^### Ran/{f=0} f' \
    | sed 's/\\n/\n/g; s/^"//; s/"$//' \
    | cut -c1-1100
  sleep 4
done
