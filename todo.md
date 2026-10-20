# Offene Aufgaben

- [ ] **Entscheid Goran: Sitzungsübernahme der Videoaufnahmen** (`hubspot-bexio-connector/video/aufnahme/sitzung.py`,
      `bexio-formular-connector/video-firmenanfragen/aufnahme/bexio_sitzung.py`, zwei Kopien desselben Codes): Der
      frühere Plan, beide durch `chrome-sitzung` zu ersetzen, widerspricht der Regel «keine frischen oder kopierten
      Profile» (Skill `browser-wahl`, Hook `hooks/browser-profil.sh` sperrt `chrome-sitzung`). Beide Skripte kopieren
      selbst Gorans Sitzung und fallen unter dieselbe Regel. Offen, wie Aufnahmen künftig angemeldet laufen (etwa an
      Gorans Chrome angehängt per CDP); erst nach dem Entscheid umbauen.
- [ ] **Prüfen: bleibt `~/.claude/settings.json` eine Verknüpfung?** `link.sh` verknüpft sie nach
      `skills-privat/claude/settings.json`. Ungeprüft ist, ob Claude Code beim eigenen Schreiben (etwa `/permissions`,
      `/config`) die Verknüpfung behält oder durch eine echte Datei ersetzt. Prüfen mit `ls -la ~/.claude/settings.json`
      nach so einer Änderung; ist sie ersetzt, die neue Datei nach `skills-privat/claude/settings.json` übernehmen,
      bevor `link.sh` wieder läuft (es würde sie sonst nur als `.vor-link-<Zeit>` beiseitelegen).
- [ ] **Entscheid Goran: MCP-Server context7 ungepinnt** (`skills-privat/claude/settings.json`): läuft per
      `npx -y @upstash/context7-mcp` ohne Version, jede neue Paketversion startet ungeprüft mit dem
      `CONTEXT7_API_KEY`. Version pinnen oder den Server entfernen, falls er nicht mehr gebraucht wird.
