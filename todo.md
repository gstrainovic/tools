# Offene Aufgaben

- [ ] **Entscheid Goran: Sitzungsübernahme der Videoaufnahmen** (`hubspot-bexio-connector/video/aufnahme/sitzung.py`,
      `bexio-formular-connector/video-firmenanfragen/aufnahme/bexio_sitzung.py`, zwei Kopien desselben Codes): Der
      frühere Plan, beide durch `chrome-sitzung` zu ersetzen, widerspricht der Regel «keine frischen oder kopierten
      Profile» (Skill `browser-wahl`, Hook `hooks/browser-profil.sh` sperrt `chrome-sitzung`). Beide Skripte kopieren
      selbst Gorans Sitzung und fallen unter dieselbe Regel. Offen, wie Aufnahmen künftig angemeldet laufen (etwa an
      Gorans Chrome angehängt per CDP); erst nach dem Entscheid umbauen.
