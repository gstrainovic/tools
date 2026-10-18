# Offene Aufgaben

- [ ] **Stop-Hook `befunde-eingetragen.sh` in `codex exec` (Frage 4 vom 18.10.):** Er blockiert in
      Recherche-Läufen mit «nichts eintragen» die fertige Antwort, die `-o`-Datei enthält dann nur Codex'
      Meta-Antwort (zweimal am 18.10., Logs in find-jobs-Sitzung). Goran entscheidet: 4a Hook überspringt
      nicht-interaktive Codex-Läufe (Empfehlung, weil dort nie etwas committet werden darf; ungeprüft, woran
      der Hook einen `codex exec`-Lauf erkennt), 4b so lassen, nur
      Lesehinweis im Skill `recherche` (steht schon).

- [ ] **Sitzungsübernahme der Videoaufnahmen auf `chrome_sitzung.py` umstellen:** `hubspot-bexio-connector/video/aufnahme/sitzung.py`
      und `bexio-formular-connector/video-firmenanfragen/aufnahme/bexio_sitzung.py` sind Kopien desselben Codes; durch
      `chrome-sitzung <ziel> bexio.com hubspot.com` ersetzen (Prüfung auf KEYCLOAK_IDENTITY bzw. hubspotapi in die
      Aufnahme-Skripte), `test_sitzung.py` dort löschen, `drehbuch.md` anpassen.

- [ ] **Codex-Hooks freigeben:** Die geänderten Definitionen in `~/.codex/hooks.json` unter `/hooks`
      prüfen und freigeben: Agenten-/Browser-Matcher, Transkriptsicherung vor der Kontextkürzung,
      `apply_patch`-Adapter für security-guidance und SessionStart-Einrichtung des Ausgabeadapters für
      Claude-Plugins nach Aktualisierungen. Der Ausgabeadapter ist für die installierten Pluginversionen
      bereits eingerichtet; seine automatische Einrichtung bei Sitzungsbeginn braucht diese Freigabe.
      Neue oder geänderte Definitionen werden bis zur Freigabe übersprungen; Vertrauenshashes nicht von
      Hand ändern.
