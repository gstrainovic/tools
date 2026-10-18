# Offene Aufgaben

- [ ] **Entscheid Goran: Sitzungsübernahme der Videoaufnahmen** (`hubspot-bexio-connector/video/aufnahme/sitzung.py`,
      `bexio-formular-connector/video-firmenanfragen/aufnahme/bexio_sitzung.py`, zwei Kopien desselben Codes): Der
      frühere Plan, beide durch `chrome-sitzung` zu ersetzen, widerspricht der Regel «keine frischen oder kopierten
      Profile» (Skill `browser-wahl`, Hook `hooks/browser-profil.sh` sperrt `chrome-sitzung`). Beide Skripte kopieren
      selbst Gorans Sitzung und fallen unter dieselbe Regel. Offen, wie Aufnahmen künftig angemeldet laufen (etwa an
      Gorans Chrome angehängt per CDP); erst nach dem Entscheid umbauen.

- [ ] **Codex-Hooks freigeben:** Die geänderten Definitionen in `~/.codex/hooks.json` unter `/hooks`
      prüfen und freigeben: Agenten-/Browser-Matcher, Transkriptsicherung vor der Kontextkürzung,
      `apply_patch`-Adapter für security-guidance und SessionStart-Einrichtung des Ausgabeadapters für
      Claude-Plugins nach Aktualisierungen. Der Ausgabeadapter ist für die installierten Pluginversionen
      bereits eingerichtet; seine automatische Einrichtung bei Sitzungsbeginn braucht diese Freigabe.
      Neue oder geänderte Definitionen werden bis zur Freigabe übersprungen; Vertrauenshashes nicht von
      Hand ändern.
