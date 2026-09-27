---
name: produktidee-validierung
description: Produktidee am Markt prüfen, bevor oder während gebaut wird (Landingpage, Direktmails aus zielfirmen.md, Abbruchkriterium, kein Werbebudget). Laden bei Arbeit an Validierung, Versand oder Stufen in bexio-formular-connector, zefix-uid-check, wartungsplan oder einem neuen Produktideen-Repo.
---

# Produktidee validieren

Produkt, Zielgruppe, Belege, Kanäle, Preis-Hypothese und der aktuelle Baustand stehen in der AGENTS.md des Repos.

## Ziel

Ein verkauftes Produkt, nicht ein fertiges Feature. Endziel: **10 zahlende Kunden**. Umsatzerwartung und Preismodell stehen im Repo.

## Belege

- Nachfrage per Google Keyword Planner, Suchen pro Monat CH/DE, mit Datum der Messung.
- Konkurrenz per Websuche und in den Verzeichnissen, in denen Kunden suchen (wordpress.org, Marketplaces, App Stores).
- Ganze Bedarfsanalyse: `~/projects/find-jobs/akquise/bedarf-plugins-saas.md`.

## Stufen

1. **Landingpage:** Text in `landingpage.md`, veröffentlicht als Unterseite (in der Regel `strainovic-it.ch/<slug>`, Repo `~/projects/strainovic-it.ch`). Formular «Vorbestellen» mit E-Mail und Freitext. Kein Fake-Kauf, sondern «Lieferung vier Wochen nach der ersten Bestellung, Zahlung erst bei Lieferung». Vorbestellungen kommen als Mail an, der Zähler steht in `todo.md`.
2. **Direkt fragen:** 30 bis 40 Kontakte aus `zielfirmen.md` per Mail mit `validierungs-mail.txt`, Absender info@strainovic-it.ch (oder die im Repo genannte Adresse) über `mailbox` (Skill mailbox). Gesendetes in `versand.md`, Antworten in `zielfirmen.md` in der Spalte Bemerkung. **Abbruchkriterium:** unter drei Ja nach 30 Mails und zwei Wochen, dann Projekt archivieren. Ab fünf Ja weiter mit Stufe 3.
3. **Bauen:** kleinster verkaufbarer Kern zuerst, TDD, dann Pro. Gebaut bzw. ausgebaut wird ab der ersten Vorbestellung oder ab fünf Ja aus Stufe 2, nicht erst ab zehn.

## Vertrieb ohne Werbebudget

Kostenlose Kanäle zuerst (Verzeichnisse, Marketplaces, Verbände, direkte Mails an `zielfirmen.md`). Keine bezahlte Werbung, bevor zehn Kunden zahlen. Die Kanäle je Produkt stehen im Repo.

## Arbeitsweise

- Diskretion: Das Produkt läuft unter Strainovic IT, keine Nennung des Arbeitgebers.
- Offene Punkte nur in `todo.md`, Validierungsstand in `zielfirmen.md` und `versand.md`, nicht in AGENTS.md.
