# Offene Punkte

- Browser-Session auf eigenem virtuellen Desktop (Goran, Skill `browser-wahl`, «Ziel: eigener virtueller
  Desktop»). Windows: `chrome_anhaengen.py` um einen Windows-Weg ergänzen: eigenes Fenster per
  `chrome.exe --new-window about:blank`, `playwright-cli detach`/`attach` (der Session-Tab landet im zuletzt
  geöffneten Fenster), Fenster per MScholtes/VirtualDesktop auf Desktop 2 verschieben (Goran, Entscheid 1a). Von
  Hand erprobt auf Build 26200: Quelle `VirtualDesktop11-24H2.cs` vom Tag V1.21 (MIT) mit
  `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe` kompiliert, `vd.exe /GetDesktop:1
  /MoveWindowHandle:<hwnd>` verschiebt das Fenster, `/IsWindowHandleOnDesktop` prüft; Handles der Chrome-Fenster
  per `EnumWindows` (Klasse `Chrome_WidgetWin_1`). Neue Tabs der Session landen dort und laden normal; die Seite
  ist `hidden` wie ein Hintergrund-Tab (setTimeout 100 ms dauert rund 1 s, `requestAnimationFrame` steht), also
  nicht schlechter als bisher. Ein neues Fenster entsteht immer auf dem sichtbaren Desktop (Goran will das nie
  sehen): Chromium verschiebt Fenster nur beim Wiederherstellen der Sitzung auf ihren alten Desktop und öffnet
  Links nie in einem Fenster auf einem anderen Desktop (chromium `docs/windows_virtual_desktop_handling.md`);
  einen Startparameter für einen anderen Desktop nennt keine der gefundenen Quellen (Recherche 03.11.2026: ddgs,
  Exa, Chromium-Doku). Darum das bestehende Fenster auf Desktop 2 wiederverwenden statt neu öffnen. Offen: als Windows-Zweig von `chrome_anhaengen.py` mit Tests bauen (Quelle in
  `tools/vendor/` samt Lizenz, `--zeigen` holt das Fenster auf Desktop 1, `--verstecken` schickt es zurück,
  Desktop 2 anlegen, falls er fehlt). Linux: `MoveToWorkspace` über Window Calls und das GNOME-Kürzel
  per ydotool blieben ohne Wirkung; anderen Weg suchen, bis dahin bleibt das Minimieren.

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
