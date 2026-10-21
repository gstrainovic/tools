---
name: arbeitsweise
description: Allgemeine Arbeitsregeln für alle Repos - Hintergrundprozesse und Warte-Schleifen (nie pgrep -f auf den eigenen Befehl), Status «nichts läuft mehr», Tests ohne Zuschauen, Geheimnisse aus Dateien per Skript nutzen, Abläufe nach Skill automatisieren, Rückmeldungen auf alle gleichartigen Stellen anwenden, keine Cloud-Runner, Modellwahl beim Delegieren (Skript vor Haiku vor Sonnet vor Opus, Entscheide im Hauptmodell). Laden, bevor Hintergrundprozesse, Agenten oder Subagenten gestartet, Tests am Gerät, Automatisierungen, Builds oder CI aufgesetzt werden, wenn ein Passwort gebraucht wird, und wenn Goran etwas korrigiert.
---

# Arbeitsweise (alle Repos)

## Hintergrundprozesse und Warte-Schleifen

- Auf einen gestarteten Prozess per PID warten (`wait $pid`, `while kill -0 $pid; do sleep 5; done`) oder
  `run_in_background` nutzen. Nie `until ! pgrep -f "<befehl>"`: Die Schleife trägt den Suchtext selbst in
  ihrer Befehlszeile, findet sich und endet nie. Wenn `pgrep -f` unvermeidbar ist, das Muster mit Klammer
  brechen (`pgrep -f "[r]endern.sh de"`).
- Dieselbe Vorgabe gehört in jeden Agenten-Auftrag mit Hintergrundprozessen.
- In jeden Agenten-Auftrag: kein `rm` mit Platzhaltern und kein `cd …;` vor Befehlen, Zwischendateien je
  Durchgang in einen neuen Ordner mit absolutem Pfad im Scratchpad, nichts löschen. Grund: Die Rechteprüfung
  kann `cd x; rm -f q/*` nicht auflösen und fragt Goran bei jedem Aufruf.
- Vor der Meldung «nichts läuft mehr»: laufende Agenten, hängende Shells (`ps` nach `sleep` mit bash-Eltern)
  und Test-Container (`docker ps`) prüfen und Verwaistes beenden, weil hängende Shells sonst der Meldung
  widersprechen.

## Vor jedem Agentenauftrag

Der Tokenverbrauch eines Agenten hängt vor allem am Auftrag. Vor dem Start vier Punkte prüfen:

1. **Eine Aufgabe je Agent:** Recherche, Text und Ausfüllen getrennt (Sonnet sammelt, Fable schreibt, Sonnet füllt aus).
2. **Werkzeuge passend zur Aufgabe:** Formulare und JavaScript-Seiten mit playwright-cli; nur Claude in Chrome
   verbieten, nie den Browser an sich.
3. **Eingabe vollständig:** genug Text je Eintrag, Fakten und Feste Werte im Auftrag, damit der Agent nicht selbst
   im Repo sucht.
4. **Erst klein testen:** bei Listen ein Probepaket, Ergebnis selbst prüfen, dann der Rest.

## Modellwahl beim Delegieren

Das Hauptmodell (Fable oder Opus in der Sitzung) ist das teuerste; sein Wochenlimit teilen sich Server und Laptop.
Vor jeder grösseren Lese- oder Fleissarbeit die Stufen von unten nach oben durchgehen und die erste nehmen, die
reicht:

1. **Skript statt Modell:** Was ein Skript ohne Sprachmodell erledigt (Websites und Impressen lesen, Listen
   abgleichen, Logs filtern, Tabellen bauen), kostet keine Tokens. Vorhandene Skripte zuerst (`firmensuche.py`,
   `jobs.py`, `foren.py`), fehlende kurz schreiben.
2. **Haiku 4.5, Denkstufe low:** mechanische Ausführung mit vorgegebenem Text und Befehlen (Mail aus Datei senden,
   Dateien kopieren, Formular nach Anleitung ausfüllen) und Lesearbeit mit festem Rückgabeformat (Impressen,
   Kontaktdaten, Tabellenwerte aus vielen Seiten).
3. **Sonnet 5.5, Denkstufe medium:** Lesen und Vorsortieren nach klaren Kriterien (Stellenanzeigen, Forenbeiträge,
   Suchtreffer, Doku-Recherche mit WebSearch und Jina), Übersetzungen, Tests nach Plan schreiben, Zusammenfassungen
   langer Fäden. Sortieraufträge zuerst als Probepaket (rund 25 Einträge, darunter einige mit bekannter richtiger
   Einordnung), Ergebnis selbst prüfen und Auftrag oder Eingabe anpassen, erst dann den Rest; Eingabe mit genug
   Text je Eintrag (ganzer Seitenauszug statt Regex-Schnipsel). Danach höchstens rund 50 Einträge je Agent (mehr
   auf parallele Agenten verteilen), keine Standardklasse erlauben, je Zeile eine eigene Begründung verlangen, das Ergebnis danach per
   Skript prüfen (gleiche Begründung in vielen Zeilen, Anteil «nicht geprüft») und auffällige Teile nachprüfen
   lassen. Grund: Bei 529 Partnerseiten in einem Auftrag legte Sonnet 270 ohne Einzelprüfung mit derselben
   Pauschalbegründung ab.
4. **Opus 5.5, Denkstufe high:** Code-Änderungen mit TDD in Produkt-Repos, Fehleranalyse, Umsetzungspläne,
   Prüfung fremden Codes; so läuft auch der Code-Lauf auf find-jobs-lauf.
5. **Hauptmodell:** alles mit Entscheid oder Folgen: Einordnung von Kandidaten, Antworten an Kunden und
   Interessenten, Preise, Freigaben, Deutung von Rückmeldungen. Keine Kundenantworten durch Haiku oder Sonnet
   (Sonnet antwortete Interessenten zu oft falsch).
6. **Fable für jeden Text, den eine Person ausserhalb liest:** Mails und Antworten an Kunden, Interessenten,
   Partner und Arbeitgeber, Bewerbungen, Anschreiben, Freitextfelder in Formularen, Upwork-Proposals,
   Forenbeiträge, Ratgeber und Blogartikel, Produkt- und Landingpages, Marktplatz-, Verzeichnis- und Profiltexte,
   readme-Beschreibungen von Plugins, Sprechertexte von Videos, auch deren Übersetzungen in andere Sprachen. Fable (`model: fable`) schreibt sie immer, auch wenn
   das Hauptmodell Opus ist (Server-Lauf, Sitzung auf Opus). Fable bekommt Anlass (Inserat, Mail, Thema), Belege und
   Regeln aus AGENTS.md und dem Fach-Skill im Wortlaut und gibt nur den Text zurück. Der Auftrag nennt Ziel, Fakten
   und Regeln, nie einen eigenen Aufbau, vorformulierte Fragen oder einen eigenen Entwurf: Fable übernimmt sonst die
   schwächere Vorgabe (wynwood, 21.10.2026). Formularfelder, Bedingungen, Belege aus
   dem Repo und von der Anbieterseite sammelt vorher Sonnet oder ein Skript in einer kurzen Vorlage je Empfänger;
   Fable liest nur diese Vorlage und schreibt. Grund: Fable-Agenten, die selbst Formulare und Repo durchsuchten,
   brauchten je fünf Partnerbewerbungen rund 180'000 Tokens. Ausfüllen, Hochladen, Einbauen und Senden
   mit dem fertigen Text übernimmt das Hauptmodell oder Sonnet; Grund: diese Texte entscheiden über Auftrag und Ruf,
   die Mechanik nicht. Ist das Fable-Limit aufgebraucht (Agent bricht mit «You've reached your Fable limit» ab,
   HTTP 429), schreibt Opus (`model: opus`) den Text ohne Rückfrage und ohne Vermerk im Bericht an Goran (er kennt die
   Regel). Nennt Goran sonst für einen solchen Text ein anderes Modell («Text soll
   Opus schreiben»), zuerst zurückfragen, ob er Fable meint, statt es umzusetzen. Französisch und Italienisch beurteilt Goran nicht: Fragen
   zu Wortlaut, Aussprache oder Hörfehlern in diesen Sprachen klärt Claude selbst (Regeln, Whisper, zweites
   Modell) und meldet nur das Ergebnis. Zur Freigabe Goran nur die deutsche Fassung zeigen; die anderen Sprachen prüft Claude
   (Anrede wie die jeweilige Oberfläche, Inhalt gleich wie Deutsch) und nennt nur Abweichungen.
7. **Fable sonst sparen:** Die Sitzung selbst läuft auf Opus (`"model": "opus"` in `~/.claude/settings.json`,
   Gorans Entscheid), Fable nur über Agenten nach Punkt 6. Recherche auf Sonnet (Sammeln) bzw. Opus (Urteil), Code und Tests auf Opus, interne
   Doku (AGENTS.md, TODO.md, Skills, Commit-Nachrichten), Berichte und Rückfragen an Goran im Hauptmodell, auch wenn
   das Opus ist. Fable bleibt damit für die Texte nach Punkt 6 frei.
8. **Geschäftskritisches doppelt prüfen:** Bei Recherchen zu Strafen, Haftung, Risiko, Gesetzen, Steuern, Geld,
   Verträgen und Schulden, und immer bei Zweifel am Ergebnis, nach der Erstrecherche (Opus) Goran eine
   Zweitrecherche mit dem anderen Modell (Fable) vorschlagen, als nummerierte Frage mit Kostenhinweis. Sagt er ja,
   beide Ergebnisse vergleichen und Übereinstimmung, Abweichungen und offene Punkte getrennt nennen; bei
   Abweichungen gilt keines als belegt, bis die Primärquelle (Gesetzestext, Urteil) gelesen ist.

Faustregeln: Ab etwa zehn Seiten oder Dateien Lesearbeit delegieren, darunter selbst machen, weil der Auftragstext
und die Rückgabe sonst mehr kosten als die Arbeit. Jeder Auftrag nennt Ziel, Quellen, Rückgabeformat und Verbote
(keine Claude-in-Chrome-Werkzeuge, nichts senden, nichts committen, keine Dateien ausserhalb des genannten Ordners).
**Erst lokal, dann Web:** Vor jeder Web-Recherche und jedem Recherche-Auftrag selbst mit `rg` über alle Repos unter
`~/projects` suchen (AGENTS.md, todo.md, Recherche-Dateien, Skills), auch nach Stichworten zum Thema, nicht nur nach
einer bekannten Datei; die Fundstellen in den Auftrag schreiben und dort festhalten, dass eigene Erfahrungen (Anträge,
Absagen, Sperren) vor Websuchen gelten. Grund: Die Marktplatz-Recherche vom 08.10.2026 übersah, dass Shopware keine
neuen Partner aufnimmt und HubSpot drei Kunden verlangt, obwohl beides in den Produkt-Repos stand.
Das gilt auch vor jeder Aussage «offen», «unklar» oder «nicht geklärt» und vor jeder Empfehlung: zuerst `rg` lokal
(am 09.10.2026 standen WooCommerce-Partnerantrag, Händlervertrag und Shopify-Machbarkeit im Repo, wurden aber als
offen bezeichnet). Der Hook `hooks/erst-lokal.sh` lehnt WebSearch, WebFetch, Jina und Recherche-Aufträge ab, solange
seit der letzten Nutzernachricht keine lokale Suche lief; ein Auftrag mit «zuerst lokal» läuft durch.
Ergebnisse eines Subagenten vor der Verwendung stichprobenweise prüfen. Mehrere unabhängige Aufträge gleichzeitig
starten.

## Goran wartet nie

Antworten an Goran haben Vorrang vor laufender Arbeit. Was länger als etwa eine Minute dauert (Deploys, Testsuiten,
Logins, Uploads, Recherchen, Werkzeug-Umbauten), läuft im Hintergrund: als Agent (Modell nach «Modellwahl») oder
per `run_in_background`, von selbst und ohne seinen Hinweis. Danach sofort antworten, Ergebnis nachreichen, sobald
es da ist. Kommt mitten in einer Arbeit eine Frage von ihm, zuerst die Frage beantworten.

## Tokens sparen (Wochenlimit teilen sich Laptop und Server)

- **Kein Fork für Arbeitsaufträge.** Ein Fork erbt den ganzen Gesprächsverlauf und liest ihn als Erstes ein; bei
  langen Sitzungen kostet das je Agent 300'000 bis 600'000 Tokens (08.10.2026: acht Agenten, rund drei Millionen,
  70 % des Wochenlimits in einem Tag). Agenten starten mit leerem Gedächtnis (`general-purpose`) und bekommen einen
  kurzen Auftrag mit Dateipfaden, Regeln und Berichtsform.
- **Modell nach Aufgabe:** mechanische Arbeit (Listen bauen, Adressen suchen, Umbrechen, Trockenläufe, Deploys)
  auf Sonnet (`model: sonnet`); Fable nur für Entscheide, Texte an Kunden und Recherchen mit Urteil.
- **Bilder sparsam:** Vorschaubilder nur bei neuen oder geänderten Vorlagen, eine Firma je Vorlage; keine
  Kontaktbögen über alle Vorlagen ohne Anlass.
- **Keine Abfrageschleifen** mit kurzen Intervallen für Mails oder DNS; einmal prüfen, bei Bedarf später nochmals.
- **Lange Sitzungen sind der grösste Posten, nicht die Agenten.** Jeder Aufruf liest den ganzen Verlauf aus dem
  Cache (Sitzung vom 07./08.10.2026: 1'242 Aufrufe, 885 Millionen Cache-Tokens auf Fable, 428 $ von 520 $;
  Agenten nur 17 %, Chrome-Werkzeugausgaben 20 %). Wann eine neue Sitzung fällig ist und wie
  Claude sie empfiehlt: `~/.claude/CLAUDE.md`, Abschnitt «Knapp berichten».
- **Fable hat ein eigenes Wochenlimit** (72 % bei 40 % Gesamt): Routine (Nachhalten, Versand, Listen, Deploys)
  in Sitzungen mit Opus oder Sonnet (`/model`), Fable für Entscheide, Kundentexte und Recherchen mit Urteil.
- **Chrome-Werkzeuge** lassen Seiteninhalte im Verlauf; nach einer Browser-Aufgabe die Sitzung beenden oder
  verdichten, Browserarbeit in eigene kurze Sitzungen legen.

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
