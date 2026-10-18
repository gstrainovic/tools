---
name: whatsapp-cloud-api
description: WhatsApp-Bot direkt bei Meta (Cloud API, ohne Twilio-Aufpreis) einrichten, auch beim Kunden - Business-Portfolio, Entwicklerkonto, App, Nummer mit Bestätigung per Anruf, Systemnutzer-Token, Webhook, Registrierung mit PIN, Profilbild, Stolpersteine in Metas Oberfläche. Laden, bevor eine WhatsApp-Nummer an die Meta Cloud API angebunden, ein Meta-Webhook gebaut oder ein WhatsApp-Bot für einen Kunden angeboten wird.
---

# WhatsApp über die Meta Cloud API

Referenz: `ki-tel` (Webhook `/meta` in `whatsapp_demo/app.py`, Tests in `tests/test_meta_whatsapp.py`, Einrichtung
in `deploy/README.md`, Codeleser `deploy/code_aus_aufnahme.py`). Live auf +41 71 539 30 77 seit 17.10.2026.

## Was nur in der Oberfläche geht (rund eine Stunde, Facebook-Passwort mehrmals)

Reihenfolge so, dass der Token früh da ist und der Rest per API läuft:

1. **Business-Portfolio:** `business.facebook.com/settings/` mit dem Facebook-Konto; Dialog «Erstelle dein
   Business-Portfolio» (Name ohne Sonderzeichen, Meta lehnt «Strainovic IT» ab und nimmt «Strainovic It»;
   geschäftliche Mail). Bestätigungsmail «Bestätige deine geschäftliche E-Mail-Adresse» per `mailbox read … --html`
   lesen, Link `business.facebook.com/verify/email/checkpoint/?token=…` im eingeloggten Chrome öffnen.
2. **Entwicklerkonto:** `developers.facebook.com/async/registration/` → Weiter → E-Mail bestätigen → Rolle
   «Entwickler» → Registrierung abschliessen.
3. **App:** `developers.facebook.com/apps/creation/`: Name, Kontaktmail, Anwendungsfall «Über WhatsApp mit deinen
   Kunden in Kontakt treten», Portfolio wählen, Anforderungen, «App erstellen» (Passwortabfrage). App-ID und
   App-Geheimcode: App-Einstellungen → Allgemeines → «Anzeigen» (Passwortabfrage).
4. **Systemnutzer und Token:** `business.facebook.com/latest/settings/system_users?business_id=…` → Hinzufügen;
   beim ersten Mal Zustimmung zur Werberichtlinie (Gorans Entscheid 113a für Strainovic IT; beim Kunden dessen
   Entscheid). Name ohne Bindestrich («kitelbot», Meta: «zu viele Bindestriche»), Rolle Admin → Assets zuweisen →
   Apps → App mit «App verwalten» → Token generieren: App, Ablauf «Nie», Berechtigungen
   `whatsapp_business_management` und `whatsapp_business_messaging`. Token aus dem Dialog per `--raw eval`
   direkt in eine Datei lesen (`.secrets/meta.env`, Tresor), nie ausgeben; prüfen mit `debug_token`
   (`type: SYSTEM_USER`, `expires_at: 0`).
5. **Nummer anlegen** (im Dashboard, Anwendungsfall → Schritt 2 Produktionseinrichtung → Neue Nummer; per API siehe
   unten): Unternehmensinfos (Name, Website, Land), Profil (Display-Name, Zeitzone Zürich, Kategorie
   «Professionelle Dienstleistungen»), Nummer mit «Anruf» (Festnetz kann kein SMS). Nach einem abgebrochenen
   Versuch sperrt Meta den nächsten Anruf 60 Minuten, nach dem zweiten 3 Stunden: nie Escape, Dialog offen lassen.
   WABA-ID und Telefonnummer-ID stehen danach im Abschnitt «Telefonnummer registrieren».

## Was per API geht (Token aus Schritt 4)

```sh
T=…; WABA=…; PHONE_ID=…; APP_ID=…
curl -X POST "https://graph.facebook.com/v24.0/$WABA/phone_numbers" -H "Authorization: Bearer $T" \
  -d cc=41 -d phone_number=715393077 -d verified_name="Strainovic It"        # nicht geprüft, Doku «Phone numbers»
curl -X POST "https://graph.facebook.com/v24.0/$PHONE_ID/request_code" -H "Authorization: Bearer $T" -d code_method=VOICE -d language=de
curl -X POST "https://graph.facebook.com/v24.0/$PHONE_ID/verify_code" -H "Authorization: Bearer $T" -d code=123456
curl -X POST "https://graph.facebook.com/v24.0/$PHONE_ID/register" -H "Authorization: Bearer $T" \
  -H "Content-Type: application/json" -d '{"messaging_product":"whatsapp","pin":"<6 Ziffern, aufbewahren>"}'   # geprüft
curl -X POST "https://graph.facebook.com/v24.0/$WABA/subscribed_apps" -H "Authorization: Bearer $T"          # Webhook-Abo
curl "https://graph.facebook.com/v24.0/$PHONE_ID?fields=status,platform_type,webhook_configuration&access_token=$T"  # CONNECTED, CLOUD_API
```

Die Registrierung über den Dashboard-Knopf «Registrieren» mit PIN blieb bei «Nicht registriert», per API ging sie
sofort. Profilbild: `deploy/README.md` in ki-tel (Upload-Sitzung `POST /$APP_ID/uploads`, Handle als
`profile_picture_handle` an `whatsapp_business_profile`).

## Bestätigungscode auf einer Nummer, die ein Bot abnimmt

Twilio-Voice-URL vor dem Anruf auf `https://twimlets.com/echo?Twiml=<Response><Record maxLength="90"
playBeep="false" timeout="15"/></Response>` (URL-kodiert, GET) stellen, Code anfordern, Zeitpunkt merken, dann
`uv run python -I deploy/code_aus_aufnahme.py <Zeitpunkt> <mp3>` (Twilio-Umgebung aus `.secrets/twilio.env`):
faster-whisper `small` liest «Ihr Prüfcode lautet 830868» auf Deutsch und Englisch gleich. Danach die Voice-URL
auf die Ansage zurückstellen. Der Dialog hat sechs Einzelfelder: erstes Feld anklicken, Ziffern mit
`keyboard.type(code, { delay: 120 })` tippen.

## Webhook (Code in ki-tel, Tests als Vorlage)

- `GET /meta`: `hub.mode=subscribe`, `hub.verify_token` gegen das eigene Prüfwort, `hub.challenge` als Text zurück.
  Der Dienst muss laufen, bevor die Callback-URL im Dashboard gespeichert wird (Meta prüft sofort).
- `POST /meta`: Signatur `X-Hub-Signature-256` = `sha256=` + HMAC-SHA256 über den Rohkörper mit dem App-Geheimcode;
  Nachrichten unter `entry[].changes[].value.messages[]` (Typen `text`, `audio`, `document`, `image`),
  Statusmeldungen unter `statuses[]` ignorieren; sofort 200 antworten, Arbeit im Hintergrund.
- Medien in zwei Schritten: `GET /{media_id}` liefert eine 5 Minuten gültige URL, `GET <url>` mit Bearer-Token die
  Datei. Versand: `POST /{phone_number_id}/messages` mit `{"messaging_product":"whatsapp","to":"<wa_id ohne +>",
  "type":"text","text":{"body":…}}`, Text höchstens 4096 Zeichen.
- Nachrichten desselben Absenders nacheinander verarbeiten (Sperre je Absender), sonst überschreibt die zweite
  Hintergrundaufgabe den Verlauf der ersten.
- Nach jedem Neustart den Zwischenspeicher mit einem Aufruf vorwärmen, sonst dauert die erste Antwort bis 30 s;
  danach rund 4 s (Zustellung durch Meta 1.8 s, Modell 1.5 s, Versand 0.6 s).
- Meta schreibt nach der Einrichtung selbst an die Nummer («Continue setting up your account», Absender +1 646…);
  der Bot antwortet darauf, harmlos, die Tagesgrenze deckelt es.

## Grenzen und Kosten

Ohne Unternehmensverifizierung 2 Nummern je Portfolio und 250 vom Unternehmen gestartete Nachrichten pro Tag;
Antworten innerhalb von 24 Stunden auf Kundennachrichten bis 1'000 im Monat gratis (Region Rest of Western Europe,
Stand Recherche in `ki-tel/recherche/ki-telefonassistent-inbound.md`). Das Limit zählt nur Nachrichten, die das
Unternehmen ausserhalb des 24-Stunden-Fensters beginnt (Doku «Messaging limits»); ein Bot, der nur antwortet,
braucht weder Verifizierung noch Veröffentlichung der App.

Die App bleibt im Entwicklungsmodus: Webhooks fremder Nummern kommen so an (Metas eigene Hinweisnachricht von
+1 646… ohne Rolle in der App löste den Webhook aus und wurde beantwortet). App Review verlangt die Webhook-Doku
nur von Partnern, die fremde WhatsApp-Konten bedienen; direkte Entwickler geben dem Systemnutzer-Token die
Berechtigungen selbst. Der Dashboard-Hinweis «Webhooks nur zum Testen, bis die App veröffentlicht ist» meint
diesen Partnerfall. Metas Seite «Business Verification» sagt ausdrücklich, dass eine App, die nur von
Rollennutzern benutzt wird, keine Verifizierung braucht.

WhatsApp-Anrufe (Calling API) verlangen dagegen ein Limit von mindestens 2'000 (Doku «Calling», «Call
settings»); auf `TIER_250` lehnt `POST /<PHONE_ID>/settings` `{"calling":{"status":"ENABLED"}}` mit Fehler
138015 ab. Der Weg ohne Massenversand ist die Unternehmensverifizierung.

**Unternehmensverifizierung (Einzelunternehmen ohne Handelsregister, so eingereicht für Strainovic IT):**
`business.facebook.com/latest/settings/security_center?business_id=…` → «Verifizierung starten» → Land →
Unternehmensart «Einzelunternehmen» → «Noch nicht registriert» → Name genau wie auf den Dokumenten (Personenname,
Firmenname als alternativer Name) → Adresse wie auf den Dokumenten → Telefon und Website → reCAPTCHA (kommt im
Playwright-Chrome mit kopierten Cookies; im eigenen Chrome per Anhängen vermutlich nicht) → Bestätigung per Mail an
eine Adresse der Website-Domain (Code kommt sofort, `mailbox`) → zwei Uploads: Name (Auswahl Bankauszug,
Gewerbeanmeldung, Steuerdokument, Gründungsurkunde) und Adresse (dieselben ohne Bankauszug, dazu
Betriebskostenabrechnung). Einen Ausweis verlangt der Ablauf nicht. Für Strainovic IT gingen Seite 1 eines
Kontoauszugs (Name) und Seite 1 der Zins- und Kapitalbescheinigung der Bank (Steuerdokument, Adresse). Meta prüft
laut Abschlussdialog in etwa 2 Werktagen; die Freigabe kommt per Mail und Webhook `business_capability_update`.

## Beim Kunden

Portfolio, App und Systemnutzer gehören dem Kunden (sein Facebook-Konto, sein Portfolio), nicht Strainovic IT;
Token, App-Geheimcode und PIN in seinen Tresor. Ist die Nummer schon in der WhatsApp-App des Kunden registriert,
muss sie dort zuerst gelöscht werden oder über «Coexistence» (Partner-Embedded-Signup) angebunden werden; beides
vor dem Angebot klären. Browserarbeit nach Skill `browser-wahl` (Gorans Chrome anhängen); Metas Knöpfe reagieren nur
auf `page.mouse.click()` auf die Mitte der `boundingBox()`, eigene Auswahllisten ebenso.
