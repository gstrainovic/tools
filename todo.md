# Offene Punkte

- `sprachnachricht.py`: die Grenze `av<19` aufheben, sobald faster-whisper nach 1.2.1 erscheint (Fix in
  SYSTRAN/faster-whisper#1589).
- Chrome: Goran will die «Playwright-Gruppen» in den Favoriten löschen. In den Sync-Daten stehen aber nur 31
  gespeicherte Tab-Gruppen, alle namens «Claude» (von Claude in Chrome); Goran will alle 31 weg. Kein Knopf für
  alle auf einmal. Offene Frage 3: (a) Kästchen «Tab-Gruppen» in «Browserdaten löschen» → Erweitert (laut
  browserhow.com, ungeprüft), (b) Goran löscht per Rechtsklick, (c) Klicks per ydotool nur, wenn Goran Bildschirm
  und Tastatur nicht benutzt. Zählen: Sync-Datenbank kopieren und `saved_tab_group-dt-*` mit plyvel auslesen.
- `recherche.py` läuft auf dem Windows-PC nicht: `python -I recherche.py` findet `ddgs` nicht (Skill sagt «direkt
  aufrufen, nur so lädt uv die Pakete»; auf Windows gibt es keinen Shebang-Start), und mit `--ohne-ddgs` scheitert
  die Ausgabe an cp1252 (`UnicodeEncodeError` in `tabellenzeile`, trotz `PYTHONUTF8=1`-Vorgabe laut
  find-jobs/AGENTS.md ist die Variable in der Sitzung nicht gesetzt). Aufruf für Windows (`uv run` oder
  `py -m`) im Skill `recherche` ergänzen und die Ausgabe mit `errors="replace"` absichern.
- ydotool tippt in das Fenster, das gerade vorne ist, nicht in ein bestimmtes: Tastatureingaben sind in eine
  Terminal-Sitzung von Goran geraten. Bevor ydotool tippt, mit `gui-screenshot` prüfen, welches Fenster vorne ist,
  und nur arbeiten, wenn Goran nicht am Rechner ist; gehört in den Skill screenshots.- `mithoeren.py`: kurze Einwürfe unter rund 2 s nicht einzeln an Voxtral schicken, sondern an den nächsten Satz
  anhängen oder verwerfen. Beleg Meeting comza 29.10. (find-jobs `akquise/bexio-hubspot/comza-gespraech-2026-10-29-
  transkript*.txt`): live erfand Voxtral bei Gorans kurzen Einwürfen fremde Sprachen (11 von 276 Zeilen, beim
  Gegenüber 3 von 204); dieselbe Aufnahme je Kanal am Stück mit `timestamp_granularities=segment`: 3 bzw. 0,
  zusammenhängende Sätze fehlerfrei. Nach dem Meeting lohnt sich die Umschrift am Stück immer; Vorlage
  `find-jobs/akquise/bexio-hubspot/umschrift_am_stueck.py` als Option `--nachher` in mithoeren übernehmen.
