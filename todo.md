# Offene Aufgaben

- [ ] **Recherche-Skript `recherche.py` bauen, bei der nächsten Recherche mit Preisvergleich:** Die Regel «Zuerst
      per Skript» im Skill `recherche` (ddgs und Exa suchen, Seiten per curl holen, nur Ort, Preise und
      Stichwortstellen ausgeben) läuft bisher als Einzelbefehle. Das Skript nimmt Suchbegriffe und ein Muster und
      gibt eine kurze Tabelle aus; an dieser Recherche entwickeln und gleich dort einsetzen (Gorans Entscheid).
      Grundlage `skills/recherche/vergleich-2026-10.md`.

- [ ] **Codex-Hooks freigeben:** Die geänderten Definitionen in `~/.codex/hooks.json` unter `/hooks`
      prüfen und freigeben: Agenten-/Browser-Matcher, Transkriptsicherung vor der Kontextkürzung,
      `apply_patch`-Adapter für security-guidance und SessionStart-Einrichtung des Ausgabeadapters für
      Claude-Plugins nach Aktualisierungen. Der Ausgabeadapter ist für die installierten Pluginversionen
      bereits eingerichtet; seine automatische Einrichtung bei Sitzungsbeginn braucht diese Freigabe.
      Neue oder geänderte Definitionen werden bis zur Freigabe übersprungen; Vertrauenshashes nicht von
      Hand ändern.
