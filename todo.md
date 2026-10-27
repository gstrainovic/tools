# Offene Punkte

- Modell für serbische Sprachnachrichten wählen: Im ersten Test (eine Nachricht, 7 Sekunden) erkannten
  `Systran/faster-whisper-large-v3` und `Sagicc/faster-whisper-large-v3-sr` (nachtrainiert, laut Modellkarte etwa
  4 % Wortfehler, Apache-2.0) dieselben Wörter; das allgemeine schreibt lateinisch, das serbische kyrillisch.
  Offen: ob das letzte Wort («Zapuni») stimmt, welche Schrift Goran will, und ein Test mit längerer
  Alltagssprache von Vesna.
- Transkriptionsskript fest ablegen, mit `faster-whisper` und `av<19`: `faster-whisper` 1.2.1 übergibt
  `metadata_errors`, das `av` 19 nicht mehr kennt. Upstream behoben (Issues #1589, #1492), aber noch nicht
  veröffentlicht; die Grenze fällt mit der nächsten Version von `faster-whisper`. Das Skript liegt bisher nur im
  Scratchpad.
