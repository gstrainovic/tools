# Offene Punkte

- Browser-Session auf eigenem virtuellen Desktop, Linux (Goran, Skill `browser-wahl`, «Ziel: eigener virtueller
  Desktop»; Windows ist umgesetzt): `MoveToWorkspace` über Window Calls und das GNOME-Kürzel per ydotool blieben
  ohne Wirkung; anderen Weg suchen, bis dahin bleibt das Minimieren. Nachgeprüft: `MoveToWorkspace <id> 1` auf das
  minimierte Arbeitsfenster liefert `()`, das Fenster bleibt auf Arbeitsfläche 0 (Monitor 0, Window Calls 21,
  `dynamic-workspaces` true, `workspaces-only-on-primary` true). Ebenso ohne Wirkung: Fenster vorher einblenden
  (`Unminimize`) und feste zwei Arbeitsflächen (`dynamic-workspaces` false, danach zurückgestellt). One Window
  Wonderland ist nicht die Ursache (abgeschaltet getestet, gleiches Ergebnis). Auch ein frisches
  zenity-Fenster bleibt auf 0, ebenso mit `workspaces-only-on-primary` false und mit allen Änderungen zusammen
  (GNOME Shell 49.10, ein Bildschirm eDP-1, primär). Laut Mutter 49 (`meta_window_change_workspace_by_index`) tut
  der Aufruf nur nichts, wenn es die Ziel-Arbeitsfläche nicht gibt oder das Fenster auf allen Arbeitsflächen klebt;
  Verdacht: Es gibt nur eine Arbeitsfläche, obwohl `num-workspaces` bzw. dynamische Arbeitsflächen eingestellt
  sind. Prüfen, ob `Super`+`Bild↓` überhaupt wechselt. Goran will Arbeitsfläche 2 (Entscheid 2a vom 03.11.2026). Headless-Chrome ist keine Alternative: Das Profil ist gesperrt, solange Gorans
  Chrome läuft, und kopierte Profile sind verboten (Skill `browser-wahl`).
- `chrome_anhaengen.py`, Linux-Zweig: der Umbau auf `cli_lauf()` (03.11.2026) ist auf dem Windows-PC nicht
  getestet (`test_chrome_anhaengen.py` braucht bash-Fakes); auf dem Laptop einmal laufen lassen.

- `sprachnachricht.py`: die Grenze `av<19` aufheben, sobald faster-whisper nach 1.2.1 erscheint (Fix in
  SYSTRAN/faster-whisper#1589).
- Chrome: Goran will die «Playwright-Gruppen» in den Favoriten löschen. In den Sync-Daten stehen aber nur 31
  gespeicherte Tab-Gruppen, alle namens «Claude» (von Claude in Chrome); Goran will alle 31 weg. Kein Knopf für
  alle auf einmal. Offene Frage 3: (a) Kästchen «Tab-Gruppen» in «Browserdaten löschen» → Erweitert (laut
  browserhow.com, ungeprüft), (b) Goran löscht per Rechtsklick, (c) Klicks per ydotool nur, wenn Goran Bildschirm
  und Tastatur nicht benutzt. Zählen: Sync-Datenbank kopieren und `saved_tab_group-dt-*` mit plyvel auslesen.
- ydotool tippt in das Fenster, das gerade vorne ist, nicht in ein bestimmtes: Tastatureingaben sind in eine
  Terminal-Sitzung von Goran geraten. Bevor ydotool tippt, mit `gui-screenshot` prüfen, welches Fenster vorne ist,
  und nur arbeiten, wenn Goran nicht am Rechner ist; gehört in den Skill screenshots.- `mithoeren.py`: kurze Einwürfe unter rund 2 s nicht einzeln an Voxtral schicken, sondern an den nächsten Satz
  anhängen oder verwerfen. Beleg Meeting 29.10.2026 (Transkripte in find-jobs, `akquise/bexio-hubspot/*-2026-10-29-
  transkript*.txt`): live erfand Voxtral bei Gorans kurzen Einwürfen fremde Sprachen (11 von 276 Zeilen, beim
  Gegenüber 3 von 204); dieselbe Aufnahme je Kanal am Stück mit `timestamp_granularities=segment`: 3 bzw. 0,
  zusammenhängende Sätze fehlerfrei (Skill meeting-hilfe). `umschrift_am_stueck.py` als Option `--nachher` in
  mithoeren übernehmen, samt Kanaltrennung per ffmpeg, mit Tests.
