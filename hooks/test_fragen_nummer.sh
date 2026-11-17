#!/usr/bin/env bash
# Tests für fragen-nummer.sh: bash hooks/test_fragen_nummer.sh
set -u
hier=$(cd "$(dirname "$0")" && pwd)
fehler=0

fall() { # name, erwartet (abgelehnt|frei), letzte Antwort [, stop_hook_active]
  local name=$1 erwartet=$2 text=$3 aktiv=${4:-false} aus ist=frei
  aus=$(jq -n --arg t "$text" --argjson a "$aktiv" \
    '{hook_event_name:"Stop", stop_hook_active:$a, last_assistant_message:$t}' | "$hier/fragen-nummer.sh")
  grep -q '"block"' <<<"$aus" && ist=abgelehnt
  if [ "$ist" = "$erwartet" ]; then echo "ok   $name"; else echo "FAIL $name: erwartet $erwartet, ist $ist"; fehler=1; fi
}

fall "Frage ohne Nummer wird abgelehnt" abgelehnt $'Befund.\n\n**Frage:** Wie beheben?\n- **a) Beides (Empfehlung)**: …\n- b) Nur Stopp'
fall "Optionen ohne Fragenummer werden abgelehnt" abgelehnt $'Wie weiter?\n- **a) Beides (Empfehlung)**: …\n- b) Nur Stopp'
fall "Frage mit Nummer läuft" frei $'**Frage 1108:** Wie beheben?\n- **a) Beides (Empfehlung)**: …\n- b) Nur Stopp'
fall "Zwei Fragen mit Nummern laufen" frei $'**Frage 1108:** A?\n- a) x\n- b) y\n\n**Frage 1109:** B?\n- a) x\n- b) y'
fall "Eine von zwei Fragen ohne Nummer wird abgelehnt" abgelehnt $'**Frage 1108:** A?\n- a) x\n- b) y\n\n**Frage:** B?\n- a) x'
fall "Bericht ohne Frage läuft" frei $'Erledigt.\n- Hook eingebaut\n- Tests grün'
fall "Verweis auf beantwortete Frage läuft" frei "Umgesetzt nach Gorans Entscheid 1107a."
fall "Zweiter Stopp blockiert nie" frei $'**Frage:** Wie?\n- a) x' true
exit $fehler
