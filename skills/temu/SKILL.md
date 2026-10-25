---
name: temu
description: Auf temu.com/ch Artikel, Preise und Produktlinks ohne Captcha lesen (Hilfsskript temu_produkt.sh über das Suchfeld in Gorans Chrome), Grenzen der Plattform (Mindestbestellwert, Vorbestellung, keine Käufer-API), Belegpflicht je Preis. Laden, bevor auf Temu ein Preis gelesen, ein Artikel gesucht oder eine Einkaufsliste mit Temu-Preisen geschrieben wird.
---

# Temu

Erarbeitet beim Einkauf für Pink Deko (`~/projects/vesna/action-dupes/`, Preise in
`~/projects/vesna/research_notes/Preisvergleich China-Shops Oktober 2026.md`).

## Regeln

- **Jeder Preis mit Produktlink.** Ein Temu-Preis ohne URL ist wertlos: Er lässt sich weder prüfen noch bestellen,
  und die Suche nach dem Artikel kostet beim zweiten Mal gleich viel wie beim ersten. Form: Produktname, Packung,
  Preis, Datum, `https://www.temu.com/ch/…-g-<ID>.html`. Die ID allein (`g-601099611003882`) reicht als Beleg,
  die Seite findet sich über die Suche nach dem Produktnamen wieder.
- **Nie Produkt-URLs direkt aufrufen** (`goods.html?goods_id=…`, `/ch/…-g-….html`, `share.temu.com/…`) und nie
  `search_result.html` per `goto`: Temu zeigt dann ein Captcha, das Goran von Hand lösen muss. Erlaubt ist nur:
  Startseite `temu.com/ch`, Suchfeld, Enter, Treffer per Mausklick. Genau das macht `temu_produkt.sh`. Auch auf
  diesem Weg kommt ein Captcha vor (25.10.2026 auf der Produktseite, zweiter Lauf innert zwei Minuten); sicher
  verhindern lässt es sich nicht. Dann die Seite im Tab stehen lassen, Goran einmal ums Lösen bitten und danach
  dieselbe Seite per `run-code` lesen, nicht neu suchen.
- **Nur in Gorans angehängtem Chrome** (Skill `browser-wahl`, `chrome-anhaengen`, Session `gchrome`, eigener Tab
  per `tab-new`). Jina, curl und Exa liefern von Temu nur eine JavaScript-Hülle. Es gibt keine Käufer-API; die
  Partner-API (partner.temu.com) ist nur für Verkäufer (geprüft 14.10.2026, Notiz `research_notes/Startplan mit
  belegten Preisankern/globale-suche-und-apis.md` im Repo vesna).
- **Läufe nacheinander, nie parallel:** Tastatureingaben kommen nur im sichtbaren Tab an.
- **Preis ist der der vorausgewählten Variante.** Grösse, Menge und Farbe im Warenkorb prüfen, bevor bestellt wird;
  Preise und Bestände ändern sich innert Tagen (Hartschalen-Etui am 25.10. morgens CHF 3.15, nachmittags 6.49).

## Gorans Regel vom 25.10.2026: nichts blind skripten

- Ein Link von Goran ist der Auftrag, genau diesen Artikel zu lesen. Nie stillschweigend einen gleichartigen
  Treffer nehmen und dessen Preis ausweisen. Findet die Suche den Artikel nicht, Goran in einem Satz melden und
  um Preis oder Screenshot bitten.
- Mit playwright-cli Schritt für Schritt arbeiten und jeden Schritt ansehen: `snapshot` nach der Suche, Treffer
  im Snapshot prüfen, dann `click`, dann Seite lesen. Ein Suchlauf, der mehrere Artikel ohne Zwischenkontrolle
  abarbeitet, ist verboten; `temu_produkt.sh` nur noch für einzelne Artikel, deren Ergebnis danach gegen Gorans
  Link geprüft wird (ID in der URL).
- Keine Temu-Läufe im Hintergrund; sie liefern nichts und blockieren den Tab.

## Captcha: nie Goran bitten (Gorans Regel vom 25.10.2026)

Goran löst keine Temu-Captchas und will nicht darum gebeten werden. Kommt eines, die Produktseite aufgeben, den
Tab schliessen und den Preis aus der Trefferliste nehmen (die Suche selbst zeigt kein Captcha): Kachelpreis plus
Link mit ID, in der Liste als «Preis aus der Trefferliste, Variante nicht geprüft» kennzeichnen, wie bei
AliExpress. Ein Preis der vorausgewählten Variante braucht die Produktseite; ohne sie bleibt es beim Kachelpreis.

## Hilfsskript

`temu_produkt.sh "<Suchbegriff>"` (neben dieser Datei) sucht über Startseite und Suchfeld und gibt die
Trefferliste zurück, je Kachel `CHF <Preis> | g-<ID> | <Titel>`; es klickt nichts an. Suchbegriff kurz, zwei bis
vier Wörter wie auf Temu («Versandboxen Logo braun»), nie ein ganzer Kacheltext. Nur mit `"<Suchbegriff>=g-<ID>"`
(ID aus einem Link von Goran) öffnet es genau diesen Treffer und gibt `URL:`, `Titel:` und den Text ab `Preis:`
(Varianten, Menge, Lieferung) aus; `CAPTCHA Produktseite` heisst dann: Kachelpreis aus der Trefferliste nehmen,
siehe oben. Mehrere Suchbegriffe in einem Aufruf laufen nacheinander; jede Trefferliste vor der Verwendung
ansehen und den passenden Treffer selbst wählen. Innenleben in `temu_produkt.js`
(run-code für playwright-cli).

## Plattform

- Gratisversand, Lieferung 6 bis 16 Werktage; zur Kasse erst ab CHF 30 Warenwert (ausser Artikel lokaler
  Verkäufer). Kleine Einkaufslisten unter 30 mit anderem Bedarf auffüllen, nicht mit Zusatzmenge.
- Personalisierte Artikel (Logo, Text, Gravur) sind «Vorbestellung», die Gestaltung wird nach dem Kauf
  hochgeladen; Gravur gilt laut Angeboten für Text oder Logo, nicht für fortlaufende Nummern.
- Temu erlaubt in den Schweizer Nutzungsbedingungen keinen gewerblichen Weiterverkauf; Einkauf von Verbrauchs- und
  Verpackungsmaterial ist Gorans Entscheid (vesna `action-dupes/AGENTS.md`).
