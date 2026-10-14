# Offene Aufgaben

- [ ] **Stop-Hook: kompakte JSON-Ausgabe im laufenden Codex bestätigen.** Codex meldete «invalid stop hook JSON output», obwohl die Entscheidung gültig war. `jq -n` gab das JSON mehrzeilig aus; der Hook gibt es nun mit `jq -cn` kompakt in einer Zeile aus. Der Test prüft das Format. Beim nächsten echten Stop-Hook-Lauf bestätigen, dass Codex die Sperre akzeptiert und keine Fehlermeldung zeigt.
