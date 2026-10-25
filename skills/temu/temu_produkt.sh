#!/usr/bin/env bash
# Temu-Artikel ohne Captcha öffnen und URL, Titel und Preis ausgeben.
# Aufruf: temu_produkt.sh "<Produktname oder Suchbegriff>" [weitere …]
# Voraussetzung: Gorans Chrome läuft, Session gchrome angehängt (chrome-anhaengen), eigener Tab ist aktiv.
# Läufe nacheinander, nie parallel: Tastatureingaben kommen nur im sichtbaren Tab an.
set -u
hier=$(dirname "$(readlink -f "$0")")
code=$(cat "$hier/temu_produkt.js")
for q in "$@"; do
  q=${q//\'/}
  echo "=== $q"
  # Fehler (### Error) werden mit ausgegeben, damit ein Abbruch sichtbar bleibt.
  playwright-cli -s=gchrome run-code "${code//__Q__/$q}" 2>&1 \
    | awk '/^### Result/{f=1;next} /^### Error/{f=1} /^### Ran/{f=0} f' \
    | sed 's/\\n/\n/g; s/^"//; s/"$//' \
    | cut -c1-600
  sleep 4
done
