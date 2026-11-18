# Offene Punkte

- **`chrome_anhaengen.py` scheitert auf dem Windows-PC:** Es meldet «FEHLER: Session-Tab lag nicht im
  Arbeitsfenster …, sondern in Gorans Fenster» und löst die Session. Laptop-Lauf ohne Browser (LinkedIn, Wellfound,
  Portal-Postfächer, 9am-Sitzung) bleibt offen. Ursache ungeprüft (Fokus beim Anhängen); nächster Versuch, nachdem
  Goran kurz in ein Chrome-Fenster geklickt hat.

- **`test_fragen.py::test_ausgabe_nennt_datei_zeile_und_text` ist auf Windows rot:** erwartet `a/todo.md:1`,
  `ausgabe()` liefert `a\todo.md:1`. Pfad in `ausgabe()` mit `as_posix()` ausgeben oder den Test anpassen.

- **Skripte an der Session `gchrome` öffnen neue Tabs in Gorans Fenster:** `newPage()` bzw. `tab-new` wird zu
  `chrome.tabs.create({ url })` ohne Fenster und ohne `active: false` (Skill `browser-wahl`, «Keine neuen Tabs»).
  Umstellen auf einen vorhandenen Session-Tab, je Skript mit Test: `find-jobs/linkedin/suche_cli.py` (jeder
  Laptop-Lauf), `find-jobs/automation/php_versionen.py`, `find-jobs/automation/kleinanzeigen_senden.py`
  (Windows-PC, alle 15 Minuten, nur ohne vorhandenen Kleinanzeigen-Tab), `tools/gsc_indexierung.js`,
  `myfactory-anbindung/myfactory/cli_login.sh`, `vesna/action-dupes/mallz/gshop_dz.js`,
  `vesna/action-dupes/konkurrenz_kanaele.sh`, `find-jobs/akquise/verzeichnisse/omr-nachfrage-*.js` und
  `provenexpert_login.sh`. Die Video-Aufnahmen starten einen eigenen Browser und sind nicht betroffen.

- Linux-Laptop: Die Historie dieses Repos wurde am 17.11. auf dem Windows-PC erneut neu geschrieben (nach Gorans
  Entscheid 1011a auch für Frage 1085: Repo-Name der Produktfotos und Shop-Domain entfernt). Dort `git fetch` und
  `git reset --hard origin/master` (vorher Uncommittetes sichern), dann `link.sh`.

- `mailbox send|reply --draft`: Die Sperre prüft nur den Entwurfsordner. Sie soll auch den Gesendet-Ordner
  prüfen (Mails von heute an denselben Empfänger, wie beim Senden) und dann «NICHT GESPEICHERT» melden. Sonst
  entsteht ein zweiter Entwurf, wenn Goran den ersten schon aus Thunderbird gesendet hat (so bei den
  Shop-Erstkontakten in find-jobs, CRM #1880 bis #1882).

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
