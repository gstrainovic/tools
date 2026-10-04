---
name: arbeitsweise
description: Allgemeine Arbeitsregeln für alle Repos - Hintergrundprozesse und Warte-Schleifen (nie pgrep -f auf den eigenen Befehl), Status «nichts läuft mehr», Tests ohne Zuschauen, Geheimnisse aus Dateien per Skript nutzen, Abläufe nach Skill automatisieren, Rückmeldungen auf alle gleichartigen Stellen anwenden, keine Cloud-Runner. Laden, bevor Hintergrundprozesse, Agenten mit Warte-Schleifen, Tests am Gerät, Automatisierungen, Builds oder CI aufgesetzt werden, wenn ein Passwort gebraucht wird, und wenn Goran etwas korrigiert.
---

# Arbeitsweise (alle Repos)

## Hintergrundprozesse und Warte-Schleifen

- Auf einen gestarteten Prozess per PID warten (`wait $pid`, `while kill -0 $pid; do sleep 5; done`) oder
  `run_in_background` nutzen. Nie `until ! pgrep -f "<befehl>"`: Die Schleife trägt den Suchtext selbst in
  ihrer Befehlszeile, findet sich und endet nie. Wenn `pgrep -f` unvermeidbar ist, das Muster mit Klammer
  brechen (`pgrep -f "[r]endern.sh de"`).
- Dieselbe Vorgabe gehört in jeden Agenten-Auftrag mit Hintergrundprozessen.
- Vor der Meldung «nichts läuft mehr»: laufende Agenten, hängende Shells (`ps` nach `sleep` mit bash-Eltern)
  und Test-Container (`docker ps`) prüfen und Verwaistes beenden, weil hängende Shells sonst der Meldung
  widersprechen.

## Tests ohne Zuschauen

Tests so bauen, dass niemand davor warten muss: unbeaufsichtigt laufen lassen und danach per Log, Journal
oder Zähler auswerten (etwa `/proc/interrupts`, `journalctl -k`). Vorher Dauer und sichtbares Verhalten
nennen, höchstens ein Wartetest pro Sitzung; wer zusieht oder eingreift, verfälscht das Ergebnis.

## Geheimnisse aus Dateien

Liegt ein Passwort oder Schlüssel schon in einer Datei (`.env`, `.secrets/`, `~/.config/mail/*.pass`), baut
Claude ein Skript, das den Wert direkt ans Werkzeug reicht (stdin, `--password-from-stdin`, Umgebungsvariable),
und führt es selbst aus, statt Goran Befehle zum Abtippen zu geben. Nur Variablennamen ansehen
(`cut -d= -f1 .env`), nie Werte ausgeben. Passwörter in Browser-Formulare tippt Claude nie, dafür gibt es
Autofill (Skill `browser-wahl`).

## Automatisieren nach Skill

Wird ein Ablauf automatisiert oder auf eine andere Maschine verlagert (Server, Cron, Skript), zuerst den
zuständigen Skill und den AGENTS.md-Abschnitt lesen, die Regeln als Liste notieren und jede im neuen Skript
umsetzen; die kritischen als Test festschreiben. Abweichungen nur, wenn die Maschine sie erzwingt (etwa kein
Browser), und dann ausdrücklich nennen, weil eine stille Abkürzung den Ablauf bricht.

## Rückmeldungen überall anwenden

Eine Korrektur von Goran zu einer Seite, Datei oder Mail gilt für alle gleichartigen Stellen (alle
Produktseiten, alle Sprachen, alle Vorlagen): sofort überall umsetzen und per Test absichern, nicht nur dort,
wo sie genannt wurde.

## Builds und CI

Keine GitHub Actions oder andere Cloud-Runner ohne ausdrückliche Erlaubnis, weil sie langsam und teuer sind
(Windows-Runner zählen doppelt). Builds laufen lokal, auf dem HP Elite Mini (Windows) oder der eigenen
Infomaniak-Instanz. Keine Workflow-Dateien anlegen, die von selbst auf Push oder Tag starten. Ist ein
Cloud-Runner der einzige Weg (macOS), vorher fragen und die Kosten nennen.
