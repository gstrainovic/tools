# Offene Punkte

- Sprachnachrichten auf Telegram lokal transkribieren: Für Serbisch `Sagicc/faster-whisper-large-v3-sr`
  (Whisper large-v3, nachtrainiert mit Common Voice 13, Fleurs und JuzneVesti-SR, laut Modellkarte etwa 4 %
  Wortfehler, Apache-2.0) gegen das allgemeine `Systran/faster-whisper-large-v3` testen, sobald Goran eine
  serbische Sprachnachricht schickt. Ungeprüft: Schrift (kyrillisch oder lateinisch) und Treffsicherheit bei
  Alltagssprache. Danach das bessere Modell fest einrichten und den Vergleich hier ablegen.
- Transkriptionsskript fest ablegen: `faster-whisper` scheitert beim Öffnen der Datei mit
  `TypeError: open() got an unexpected keyword argument 'metadata_errors'`, weil die Version von `av` nicht passt.
  Umgehung: Ton zuerst mit `ffmpeg` umwandeln (`f32le`, 16 kHz, mono) und als Zahlenreihe übergeben. Das Skript
  liegt bisher nur im Scratchpad.
