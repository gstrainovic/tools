# Offene Aufgaben

- [ ] **Stop-Hook: sporadischen Exit-Code 1 klären.** `befunde-eingetragen.sh` ist als Stop-Hook in Codex und Claude konfiguriert; die vorhandenen Tests laufen durch. Der konkrete Lauf mit Meldung «Hook failed — hook exited with code 1» liess sich nicht reproduzieren. Beim nächsten Auftreten Eingabe des Hooks, Standardfehler und Aufrufkontext sichern und damit den Fehler isolieren; die erwartete Blockierentscheidung gibt JSON aus und sollte regulär mit Exit-Code 0 enden.
