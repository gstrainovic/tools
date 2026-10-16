# Offene Aufgaben

- [ ] **Recherche-Skript `recherche.py` bauen, beim Punkt Spray-Tanning in `vesna/todo.md`:** Die Regel «Recherche
      zuerst per Skript» im Skill `browser-wahl` (ddgs und Exa suchen, Seiten per curl holen, nur Ort, Preise und
      Stichwortstellen ausgeben) läuft bisher als Einzelbefehle. Das Skript nimmt Suchbegriffe und ein Muster und
      gibt eine kurze Tabelle aus; an der Spray-Tanning-Recherche entwickeln und gleich dort einsetzen (Gorans
      Entscheid). Grundlage `vesna/research_notes/recherche-werkzeuge.md`.

- [ ] **Codex-Hooks freigeben:** Die geänderten Definitionen in `~/.codex/hooks.json` unter `/hooks`
      prüfen und freigeben: Agenten-/Browser-Matcher, Transkriptsicherung vor der Kontextkürzung,
      `apply_patch`-Adapter für security-guidance und SessionStart-Einrichtung des Ausgabeadapters für
      Claude-Plugins nach Aktualisierungen. Der Ausgabeadapter ist für die installierten Pluginversionen
      bereits eingerichtet; seine automatische Einrichtung bei Sitzungsbeginn braucht diese Freigabe.
      Neue oder geänderte Definitionen werden bis zur Freigabe übersprungen; Vertrauenshashes nicht von
      Hand ändern.
