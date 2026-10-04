---
name: mistral-api
description: Mistral-API (OCR, Vision, Embedding): Modellnamen, Grenzen für Dateien und Bilder, Tarife und Ratenlimits, bewährte Pipeline. Laden bei Arbeit mit Mistral in dms, rag-pgvector-beispiel, ai-proxy oder einem neuen Projekt.
---

# Mistral-API

Grenzen und Preise vor Entscheidungen in der offiziellen Doku (docs.mistral.ai) gegenprüfen, sie ändern sich.

## Modelle

- OCR: `mistral-ocr-latest`, Dokument zu Markdown
- Vision und Chat: `mistral-small-latest`, Text und Bilder
- Embedding: `mistral-embed` (1024 Dimensionen)

## OCR

- Höchstens 50 MB und 1000 Seiten je Anfrage, intern 200 DPI
- Bilder PNG, JPEG, AVIF; Dokumente PDF, PPTX, DOCX (URL, Base64 oder Upload)
- Seitenauswahl 0-basiert (einzeln, Bereich, Liste); `table_format`: null, markdown oder html
- Keine Zeichenformatierung (fett, kursiv), aber Fussnoten
- Rund 1 USD je 1000 Seiten

## Vision

- Höchstens 8 Bilder je Anfrage, 10 MB und 10 000 × 10 000 px je Bild
- Intern auf 1540 × 1540 skaliert: clientseitig auf 1540 px verkleinern spart Bandbreite
- Tokens je Bild etwa (Breite × Höhe) / 784, höchstens rund 3025
- JPEG, PNG, WEBP, GIF (nur ein Frame)

## Tarife

- Experiment (gratis): 50 000 Tokens je Minute, 4 Mio. je Monat, 1 Anfrage je Sekunde, dazu ein verstecktes Vision-Limit; Daten werden standardmässig fürs Training genutzt (abschaltbar).
- Scale (bezahlt): 2 Mio. Tokens und 360 Anfragen je Minute, kein eigenes Vision-Limit; für Produktion.
- Das Dashboard zeigt auch im Experiment-Tarif die Scale-Limits an. Ein Ausgabenlimit ist kein Tarifwechsel, auf Scale muss ausdrücklich gewechselt werden.

## Bewährt

- Zwei Stufen (OCR, dann Chat) statt Document Annotation in einem Schritt; die einstufige Variante halluziniert.
- Im AI SDK `maxRetries: 0` setzen, sonst brauchen interne Wiederholungen das Ratenlimit auf.
