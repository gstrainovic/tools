# Offene Punkte

- Sprachnachrichten auf Telegram lokal transkribieren: Für Serbisch `Sagicc/faster-whisper-large-v3-sr`
  (Whisper large-v3, nachtrainiert mit Common Voice 13, Fleurs und JuzneVesti-SR, laut Modellkarte etwa 4 %
  Wortfehler, Apache-2.0) gegen das allgemeine `Systran/faster-whisper-large-v3` testen, sobald Goran eine
  serbische Sprachnachricht schickt. Ungeprüft: Schrift (kyrillisch oder lateinisch) und Treffsicherheit bei
  Alltagssprache. Danach das bessere Modell fest einrichten und den Vergleich hier ablegen.
- Transkriptionsskript fest ablegen, mit `faster-whisper` und `av<19`: `faster-whisper` 1.2.1 übergibt
  `metadata_errors`, das `av` 19 nicht mehr kennt. Upstream behoben (Issues #1589, #1492), aber noch nicht
  veröffentlicht; die Grenze fällt mit der nächsten Version von `faster-whisper`. Das Skript liegt bisher nur im
  Scratchpad.
