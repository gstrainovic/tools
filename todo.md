# Offene Punkte

- [ ] **Offengelegte Geheimnisse ersetzen.** Beim Holen der `clouds.yaml` auf dem Windows-PC hat ein fehlerhafter
  PowerShell-Filter alle Tresorwerte in eine Datei geschrieben, und die ersten 40 Zeilen davon standen im Klartext
  im Claude-Verlauf. Die Datei ist gelöscht. Neu ausstellen und im Tresor ersetzen (`geheimnisse hochladen`):
  SVN-Passwort wordpress.org (`gstrainovic`), Infomaniak-AI-Token (Produkt 111648), Mistral-API-Schlüssel
  (wartungsheft), WordPress-Admin-Passwort der lokalen Testseite. Vom SSH-Schlüssel standen nur Kopf und
  öffentlicher Teil im Verlauf; ersetzen trotzdem empfohlen. Supabase-Demo-Schlüssel und die Instant-Testwerte
  sind keine echten Geheimnisse.
