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
  Startseite `temu.com/ch`, Suchfeld, Enter, Treffer per Mausklick. Genau das macht `temu_produkt.sh`.
- **Nur in Gorans angehängtem Chrome** (Skill `browser-wahl`, `chrome-anhaengen`, Session `gchrome`, eigener Tab
  per `tab-new`). Jina, curl und Exa liefern von Temu nur eine JavaScript-Hülle. Es gibt keine Käufer-API; die
  Partner-API (partner.temu.com) ist nur für Verkäufer (geprüft 14.10.2026, Notiz `research_notes/Startplan mit
  belegten Preisankern/globale-suche-und-apis.md` im Repo vesna).
- **Läufe nacheinander, nie parallel:** Tastatureingaben kommen nur im sichtbaren Tab an.
- **Preis ist der der vorausgewählten Variante.** Grösse, Menge und Farbe im Warenkorb prüfen, bevor bestellt wird;
  Preise und Bestände ändern sich innert Tagen (Hartschalen-Etui am 25.10. morgens CHF 3.15, nachmittags 6.49).

## Hilfsskript

`temu_produkt.sh "<Produktname>" ["<weiterer>" …]` (neben dieser Datei) gibt je Artikel `URL:`, `Titel:` und den
Text ab `Preis:` (Varianten, Menge, Lieferung) aus, rund 25 Sekunden je Artikel. Bester Suchbegriff ist der
Produktname von Temu, auch gekürzt; das Skript öffnet den ersten Treffer, dessen Kacheltext mit den ersten 24
Zeichen des Begriffs beginnt, sonst gibt es `KEIN TREFFER` mit den zehn ersten Treffern (Text und Link) zurück,
aus denen sich der passende Name wählen lässt. `CAPTCHA …` heisst: Goran in einem Satz um das Lösen bitten, dann
denselben Aufruf wiederholen. Innenleben in `temu_produkt.js` (run-code für playwright-cli).

## Plattform

- Gratisversand, Lieferung 6 bis 16 Werktage; zur Kasse erst ab CHF 30 Warenwert (ausser Artikel lokaler
  Verkäufer). Kleine Einkaufslisten unter 30 mit anderem Bedarf auffüllen, nicht mit Zusatzmenge.
- Personalisierte Artikel (Logo, Text, Gravur) sind «Vorbestellung», die Gestaltung wird nach dem Kauf
  hochgeladen; Gravur gilt laut Angeboten für Text oder Logo, nicht für fortlaufende Nummern.
- Temu erlaubt in den Schweizer Nutzungsbedingungen keinen gewerblichen Weiterverkauf; Einkauf von Verbrauchs- und
  Verpackungsmaterial ist Gorans Entscheid (vesna `action-dupes/AGENTS.md`).
