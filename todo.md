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

- [ ] **mailbox: Gmail-Entwürfe und Ordner mit Umlauten:** `mailbox send gmail … --draft` legt den Entwurf im
      Label `Drafts` ab statt in `[Gmail]/Entwürfe` (Ordner mit Flag `\Drafts`), Thunderbird und Gmail zeigen ihn
      dort nicht als Entwurf. Den Entwurfsordner wie beim Gesendet-Ordner am Flag erkennen. Dazu scheitern
      `move` und `--folder` an Ordnernamen mit Umlaut (`UnicodeEncodeError`, kein Modified-UTF-7), und
      `[Gmail]/Entw&APw-rfe` wird als «nicht gefunden» abgewiesen. Test zuerst (TDD).
