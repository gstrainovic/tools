---
name: ricardo
description: Auf ricardo.ch inserieren (Einzelformular, «Mehrere Angebote erstellen», Gruppen-Eigenschaften, Veröffentlichen), angehängt an Gorans Chrome per playwright-cli; Regeln der Plattform (keine URL, öffentliche Q&A, Provision, keine API mehr) und die Fallen des Formulars. Laden, bevor auf Ricardo etwas eingestellt, geändert oder geprüft wird.
---

# Ricardo

Stand 18.10.2026, erarbeitet beim Einstellen der Action-Dupes (`~/projects/vesna/action-dupes/`, Konto `pink-deko`).
Die Skripte liegen dort: `ricardo_einstellen.py` (Einzelformular), `ricardo_mehrfach.py` und `ricardo_gruppe.js`
(Mehrfach-Formular und Gruppen-Eigenschaften), `inserate.py`/`symbolbild.py` (Texte und Bilder).

## Plattformregeln (geprüft an Hilfe und AGB)

- **Keine API.** Die öffentliche Verkäufer-API ist seit 1.9.2026 abgeschaltet. Ersatz: Produkt-Feed nur für
  freigeschaltete Händler, «Ricardo Shops API» nur mit Handelsregistereintrag, UID und CH-Bankkonto. Die
  Importvorlage (.xlsx) unter «Mehrere Angebote erstellen» liefert Ricardo hinter einem Captcha (auch im
  eingeloggten Browser kommt HTML). Bleibt: Verkaufsformular, Mehrfach-Formular, App.
- **Keine URL und keine Web-Adresse** in Text und Bildern (AGB 3.6), sonst wird das Angebot entfernt.
- **«Fragen & Antworten» sind öffentlich** und gelten als Teil des Kaufvertrags.
- **Erfolgsprovision** je Produkttyp 8–12 % (Parfüm 12 %, max. CHF 290), Einstellen gratis. Versand innert 14
  Tagen nach Zahlung plus im Angebot deklarierte Verfügbarkeit; eine Verfügbarkeit lässt sich im Formular nicht
  eintragen, Lieferfrist also in den Text.
- **AGB 3.2** verbietet Skripte, die den Betrieb stören oder die Infrastruktur belasten; ein Formular nach dem
  anderen auszufüllen ist das nicht. Trotzdem langsam, mit Wartezeiten.
- Bilder und Texte müssen eigene sein (Ricardo lässt die Rechte bestätigen); Symbolbilder sind erlaubt, wenn der
  Text sie als solche nennt.

## Anhängen

Skill `browser-wahl`, «Gorans Chrome anhängen»: `playwright-cli attach --cdp="ws://127.0.0.1:9222$(sed -n 2p
~/.config/google-chrome/DevToolsActivePort)" --session=gchrome`. Port 9222 zu heisst: Chrome läuft nicht oder
Remote-Debugging ist nicht erlaubt (`chrome://inspect/#remote-debugging`). Nach einem Chrome-Neustart meldet
`tab-list` «not open», dann einmal neu anhängen. Login auf login.ricardo.ch macht Goran (Autofill lieferte nichts).
Konto-E-Mail ist info@pink-deko.ch (`mailbox`-Konto `pink-deko`, Werbefilter aus, Ricardo-Mails im INBOX). Konto-Seite `/de/profile/personal-info/`; E-Mail ändern verlangt erst einen Code an die alte,
dann an die neue Adresse und meldet danach ab.

## Fallen von playwright-cli auf Ricardo

- `snapshot` schreibt nach den ersten Aufrufen keine neue Datei mehr; `ls -t .playwright-cli/page-*.yml` zeigt
  dann alte Stände. Zustand darum per `run-code` abfragen (`isChecked`, `inputValue`, `innerText`) und
  Screenshots per `page.screenshot({ fullPage: true })` in den Scratchpad, dann mit Pillow zuschneiden und lesen.
- `run-code` nimmt den Code als Parameter, nicht als Dateipfad; längere Skripte in eine Datei schreiben und mit
  `"$(cat datei.js)"` übergeben. Variablen, die nach einem `try` gebraucht werden, mit `var` anlegen.
- Die Rückgabe eines `run-code` steht als JSON-Zeile vor «### Page»; mit `rg -o '\{"…".*'` herausfiltern. Fehlt
  die Zeile, war ein Fehler: Ausgabe mit `tail` lesen.
- `locator.click()` hängt oft («waiting for element to be visible, enabled and stable»): Knöpfe, Radios und
  Checkboxen per `evaluate(e => e.click())` setzen; MUI-Selects (Zustand, Dropdowns) brauchen aber einen echten
  `click()` auf `#<id>` und dann `getByRole('option')`.
- Textfelder: `fill` hängt bei Titel und Beschreibung; Titel per Setter + `input`/`change`-Event, die Beschreibung
  (`[contenteditable=true]`) per `execCommand('selectAll')` und `execCommand('insertText', false, text)`.
- Bild: `page.locator('input[type=file]').first().setInputFiles(pfad)`. Lösch-Knopf eines Bildes heisst
  `delete`; der erste `delete`-Knopf gehört keinem Bild und öffnet den Dateidialog (Session blockiert mit «does
  not handle the modal state», dann `playwright-cli upload <datei>` oder Tab schliessen). Darum immer den letzten
  `delete`-Knopf nehmen und nur per `hover()` + `click()`.
- Preisfelder haben kein Label: bei Fixpreis ist `spinbutton` 0 die Stückzahl, 1 der Preis.
- Viewport: Ist das Fenster schmal (< 900 px), zeigt «Mein Verkaufen» das Mobil-Layout ohne Auswahlkästchen.
  `page.setViewportSize({ width: 1500, height: 950 })` und `reload`.
- Direkte URLs nicht raten: `/de/sell/` und `/de/my-ricardo/selling/` geben Fehler. Bekannt: `/de/list/`
  (Verkaufsformular), `/de/bulk/landing/` (Mehrfach), `/de/my-ricardo/selling/drafts/` (Entwürfe),
  `/de/my-ricardo/selling/offers/` (am Verkaufen), `/de/my-ricardo/selling/offers/planned/`.
- Der Knopf **«Veröffentlichen (n)»** auf der Prüfseite des Mehrfach-Formulars reagiert auf keinen Skript-Klick
  (evaluate, click, mouse down/up); Goran klickt ihn selbst. Im Einzelformular geht «Veröffentlichen» per Skript.

## Angebote beenden

`/de/my-ricardo/selling/offers/`: je Zeile ein Kästchen (Kästchen 0 ist «alle»), Zuordnung über «Ref.: <nr>» im
nächsten Vorfahren (einzeln eingestellte Angebote haben keine Ref., dann über den Titel). Nach dem Anhaken erscheint
«Beenden (n)», der Dialog «Angebote beenden ?» bestätigt mit «Angebote beenden»; danach steht die Zeile auf «Nicht
verkauft» und lässt sich von dort neu aufschalten.

## Bild-Upload über die Playwright Extension

Angehängt per `chrome-anhaengen` (Extension statt CDP) hängen `setInputFiles` und `playwright-cli upload` im
Timeout, und ein geöffneter Dateidialog blockiert die Session (dann `chrome-anhaengen` neu). Was geht: das Bild als
Base64 ins Skript legen und im Browser per `DataTransfer` als `File` ins `input[type=file]` setzen, dann ein
`change`-Event (`ricardo_einstellen.py`, ebenso tutti). Echte Klicks warten dort oft endlos auf «stable»: Knöpfe
per `evaluate(e => e.click())`, MUI-Selects per `mousedown`-Event. Laufende Angebote ändern: `/de/list/?a=<id>`,
alle Felder änderbar, «Änderungen bestätigen» (`ricardo_einstellen.py <nr> --aendern`). Nach `goto` von einem
Formular weg (goto, reload, tab-close, auch nach einem abgebrochenen Lauf) fragt Chrome «Website verlassen?».
Die Extension bricht den laufenden Befehl mit «does not handle the modal state» ab; stammt der Dialog aus einem
früheren Befehl, kennt sie ihn nicht mehr, `dialog-accept` meldet «no modal state», und nur ein Klick im Browser
hilft. Weder `window.onbeforeunload = null`, `page.once('dialog')`, ein eigener Tab (`newPage`: Hintergrund-Tabs
drosselt Chrome, Uploads hängen) noch `tab-close` umgehen ihn. Abhilfe: die Erweiterung
`~/projects/tools/chrome-kein-verlassen-dialog` (einmal entpackt laden, README dort) macht `beforeunload` auf
ricardo.ch und tutti.ch wirkungslos. Es gibt nur eine Session: Läufe nie parallel. Mehrere
Fotos als Base64 sprengen die Grenze eines Befehlsarguments (128 KB): Code in eine Datei schreiben und
`playwright-cli run-code --filename <datei>` aufrufen.

tutti: Inserate unter `/de/myads/active`, je Inserat «Weitere Optionen» → Bearbeiten (`/de/listings/<id>/edit`,
Fotos per Knopf «Entfernen»), Deaktivieren, Löschen. Neue
und bearbeitete Inserate stehen erst auf «Wird geprüft». Fotos per DataTransfer ins Dateifeld kommen beim
Bearbeiten nicht mehr an (Zähler «n/5 Fotos» steigt nicht, 25.10.2026); Text- und Preisänderungen darum mit
`tutti_einstellen.py <nr> --aendern --nur-text`, Fotos bleiben stehen.

## Einzelformular (`/de/list/`)

Reihenfolge, die funktioniert (`ricardo_einstellen.py`): Bild hochladen → Titel (max. 60 Zeichen) → Produkttyp
(erscheint erst nach Bild oder Titel; «Parfüm») → Details (Geschlecht, Parfümtyp, Marke «Andere») → Zustand
«Neu und originalverpackt» → Beschreibung (max. 5000) → Auktion aus, Sofort-Kaufpreis an, Preis → Laufzeit
(Fixpreis: Dauer 90 Tage, Reaktivierung bis 9 Mal vorangehakt) → Versand an (Standard «Paket, Economy, CHF 9.00,
Vorauszahlung»), Abholung an (Adresse aus dem Konto, Barzahlung) → Veröffentlichen. Die Erfolgsseite bietet
«Angebot kopieren» (`/de/list/?prefill=<id>`): übernimmt alles ausser dem Bild (das alte Bild bleibt mit drin und
muss gelöscht werden).

## Mehrfach-Formular (`/de/bulk/landing/`)

1. «Anzahl der Angebote» eintragen (max. 100), «Weiter» → `/de/bulk/edit/?draftsNb=n` mit je Block Titel,
   Referenz-Nr. (eigene Artikelnummer), Zustand (MUI-Select `#condition-select-<i>`), Beschreibung
   (`[contenteditable=true]` nth i), Fotos (`input[type=file]` nth i). Ein Block ohne Titel und Foto wird nicht
   gespeichert; der Rückgängig-Knopf (`img[alt=undo-button]`) leert ihn samt Bild. «Speichern & Weiter» legt
   Entwürfe an (`ricardo_mehrfach.py fuellen`).
2. Entwürfe-Liste: Kästchen 0 ist «alle», die übrigen je Entwurf; Zuordnung über den Text «Ref.: <nr>» in der
   Zeile. «Weiter Bearbeiten» → Menü «Artikeldetails | Eigenschaften | Angebot & Preis | Lieferung» öffnet je ein
   Panel für die Auswahl mit «Speichern (n)». Eigenschaften (Produkttyp, Geschlecht, Parfümtyp, Marke) gelten für
   die ganze Auswahl, darum Gruppen bilden (Damen/EdP, Herren/EdT; `ricardo_gruppe.js`). Preis-Panel wie im
   Einzelformular (Auktion aus, Sofort an, spinbutton 1 = Preis); Lieferung: Versand und Abholung anhaken.
3. Alle auswählen → «Überprüfen & Veröffentlichen» → Prüfseite «n Angebote bereit» → «Veröffentlichen (n)» von
   Hand (siehe Fallen). Danach stehen die Links in `/de/my-ricardo/selling/offers/` (`a[href*="/de/a/"]`).
