# Offene Aufgaben

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

- [ ] **(134) WebFetch ebenfalls sperren?** `WebSearch` steht seit 18.10.2026 in `permissions.deny` von
      `~/.claude/settings.json` (nackter Werkzeugname entfernt das Werkzeug ganz aus dem Kontext, Doku
      code.claude.com/docs/en/permissions). `WebFetch` bleibt vorerst, weil `~/.claude/CLAUDE.md` («WebFetch –
      immer über Jina Reader») es noch vorsieht; der Skill recherche holt Einzelseiten aber per `curl` an Jina.
      Entscheid Goran: sperren und den CLAUDE.md-Abschnitt auf curl umschreiben, oder behalten.
