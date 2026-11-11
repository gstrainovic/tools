# Offene Punkte

- `sprachnachricht.py`: die Grenze `av<19` aufheben, sobald faster-whisper nach 1.2.1 erscheint (Fix in
  SYSTRAN/faster-whisper#1589).
- Chrome: Goran will die «Playwright-Gruppen» in den Favoriten löschen. In den Sync-Daten stehen aber nur 31
  gespeicherte Tab-Gruppen, alle namens «Claude» (von Claude in Chrome); Goran will alle 31 weg. Kein Knopf für
  alle auf einmal. Offene Frage 3: (a) Kästchen «Tab-Gruppen» in «Browserdaten löschen» → Erweitert (laut
  browserhow.com, ungeprüft), (b) Goran löscht per Rechtsklick, (c) Klicks per ydotool nur, wenn Goran Bildschirm
  und Tastatur nicht benutzt. Zählen: Sync-Datenbank kopieren und `saved_tab_group-dt-*` mit plyvel auslesen.
- ydotool tippt in das Fenster, das gerade vorne ist, nicht in ein bestimmtes: Tastatureingaben sind in eine
  Terminal-Sitzung von Goran geraten. Bevor ydotool tippt, mit `gui-screenshot` prüfen, welches Fenster vorne ist,
  und nur arbeiten, wenn Goran nicht am Rechner ist; gehört in den Skill screenshots.
- Linux-Laptop: Der Link `~/.local/bin/umschrift-am-stueck` zeigt ins Leere, seit `umschrift_am_stueck.py` in
  `mithoeren --nachher` aufgegangen ist (`link.sh` entfernt alte Links nicht); dort einmal löschen.
- `mithoeren`: kurze Einwürfe (unter `KURZ_S`) und `--nachher` sind nur mit Attrappen getestet. Beim nächsten echten
  Meeting prüfen, ob Voxtral live weniger fremde Sprachen erfindet und ob `--nachher` an der Tondatei durchläuft.
- `fragen pruefen` meldet «VERALTET Frage 312» für `skills-privat/claude/gemeinsam.md:36`: Dort steht «Frage 312» nur als
  Beispiel für die Form einer Frage. Entweder das Beispiel ohne echte Nummer schreiben (etwa «Frage N») oder
  `fragen.py` die Regeldateien unter `skills-privat/claude/` überspringen lassen, mit Test.
