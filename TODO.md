# Offene Aufgaben

- [ ] **Stop-Hook im laufenden Codex bestätigen.** Codex meldete «invalid stop hook JSON output»; `jq -n` gab die gültige Entscheidung mehrzeilig aus. Ausgabe ist nun mit `jq -cn` kompakt einzeilig. Ausserdem erkennt der Parser Codex-Transkriptzeilen (`response_item` mit Nutzernachricht, Assistententext und TODO-bezogenen Werkzeugaufrufen), damit TODO-Änderungen seit dem letzten Prompt nicht fälschlich übersehen werden. Regressionstests prüfen beide Fälle; beim nächsten echten Stop-Hook-Lauf bestätigen, dass JSON-Fehler und falsche Blockierung ausbleiben.
