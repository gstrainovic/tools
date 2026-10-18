---
name: mistral-api
description: Mistral-API (OCR, Vision, Embedding): Modellnamen, Grenzen für Dateien und Bilder, Tarife und Ratenlimits, bewährte Pipeline. Laden bei Arbeit mit Mistral in dms, wartungsheft, rag-pgvector-beispiel, ai-proxy oder einem neuen Projekt.
---

# Mistral-API

Grenzen und Preise vor Entscheidungen in der offiziellen Doku (docs.mistral.ai) gegenprüfen, sie ändern sich.

## Modelle

- OCR: `mistral-ocr-latest`, Dokument zu Markdown
- Vision und Chat: `mistral-small-latest`, Text und Bilder
- Embedding: `mistral-embed` (1024 Dimensionen)
- Mistral Small 4: 0.15 USD je Mio. Tokens Eingabe, 0.60 USD Ausgabe (docs.mistral.ai/models/mistral-small-4-0-26-03)
- Welches Modell an welchen Endpunkt gehört, sagt `GET /v1/models`: das Feld `capabilities` unterscheidet
  `completion_chat`, `audio_transcription`, `audio_transcription_realtime` und `audio_speech`. Produktnamen aus der
  Dokumentation sind keine Modell-IDs.

## OCR

- Höchstens 50 MB und 1000 Seiten je Anfrage, intern 200 DPI
- Bilder PNG, JPEG, AVIF; Dokumente PDF, PPTX, DOCX (URL, Base64 oder Upload)
- Seitenauswahl 0-basiert (einzeln, Bereich, Liste); `table_format`: null, markdown oder html
- Keine Zeichenformatierung (fett, kursiv), aber Fussnoten
- OCR 4.1: 4 USD je 1000 Seiten, 5 USD mit Annotation (docs.mistral.ai/models/ocr-4-1)
- Scale-Tarif: 2000 Seiten je Minute; über Azure/Foundry höchstens 30 MB und 30 Seiten

## Vision

- Höchstens 8 Bilder je Anfrage, 10 MB und 10 000 × 10 000 px je Bild
- Intern auf 1540 × 1540 skaliert: clientseitig auf 1540 px verkleinern spart Bandbreite
- Tokens je Bild etwa (Breite × Höhe) / 784, höchstens rund 3025
- JPEG, PNG, WEBP, GIF (nur ein Frame)

## Tarife

- Experiment (gratis): 50 000 Tokens je Minute, 4 Mio. je Monat, 1 Anfrage je Sekunde, dazu ein verstecktes Vision-Limit; Daten werden standardmässig fürs Training genutzt (abschaltbar).
- Scale (bezahlt): 2 Mio. Tokens und 360 Anfragen je Minute, kein eigenes Vision-Limit; für Produktion.
- Das Dashboard zeigt auch im Experiment-Tarif die Scale-Limits an. Ein Ausgabenlimit ist kein Tarifwechsel, auf Scale muss ausdrücklich gewechselt werden.

## Konsole (admin.mistral.ai)

- Keine Verwaltungs-API ausser im Enterprise-Plan: Arbeitsbereiche, Limits und Schlüssel nur in der Konsole
  (playwright-cli angehängt an Gorans Chrome, Skill `browser-wahl`).
- **Arbeitsbereich je öffentlicher App:** Arbeitsbereiche → «Neuer Arbeitsbereich» (gratis); eigenes Monatslimit
  unter Limits, Mindestwert USD 10. Der Schalter neben «Monatliches Ausgabenlimit» reagiert nur auf einen echten
  Mausklick (`page.mouse.click` auf seine Mitte), danach Wert eintippen und «Limit aktualisieren».
- **Schlüssel** im Reiter API-Schlüssel des Arbeitsbereichs; der Wert erscheint nur einmal und nur über «Schlüssel
  kopieren» in der Zwischenablage des Playwright-Browsers (nicht im System). Ohne Anzeige in eine Datei bringen:
  Rechte `clipboard-read` gewähren, `navigator.clipboard.readText()`, in einer neuen Seite per Formular-POST an
  einen lokalen Einmal-Empfänger (127.0.0.1) schicken, der mit chmod 600 schreibt; `fetch` dorthin blockt Chrome.
- Der Minutenzähler `x-ratelimit-remaining-req-minute` gilt für die ganze Organisation, nicht je Arbeitsbereich;
  welchem Arbeitsbereich ein Schlüssel gehört, zeigt nur die Konsole.

## Bewährt

- Zwei Stufen (OCR, dann Chat) statt Document Annotation in einem Schritt; die einstufige Variante halluziniert.
- Im AI SDK `maxRetries: 0` setzen, sonst brauchen interne Wiederholungen das Ratenlimit auf.
