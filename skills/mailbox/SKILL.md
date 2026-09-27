---
name: mailbox
description: Mails per Kommandozeile lesen, suchen, senden und beantworten (mailbox, IMAP/SMTP, Konten gmail, strainovic, wartungsheft). Laden, bevor eine Mail gelesen oder verschickt wird oder mailbox.py geändert wird.
---

# mailbox

`~/.local/bin/mailbox` ist eine Verknüpfung auf `~/projects/tools/mailbox.py` (angelegt von `setup.sh`). Nur Python-Standardbibliothek, liest und schreibt direkt auf dem Server; Thunderbird zeigt denselben Stand.

## Konten

- Konfiguration in `~/.config/mail/accounts.toml` (Vorlage `mailbox-accounts.example.toml`), ein Abschnitt pro Konto, der Abschnittsname ist der Kontoname in den Befehlen.
- Konten: `gmail` (privat, Gmail), `strainovic` (info@strainovic-it.ch, Infomaniak), `wartungsheft` (info@wartungsheft.ch, Infomaniak).
- Passwörter je Konto in einer eigenen Datei (`password_file`, eine Zeile, chmod 600), nie in der TOML-Datei, nie im Repo.
- Gmail: IMAP/SMTP `imap.gmail.com`/`smtp.gmail.com`, Google App-Passwort, `sent_folder = ""` (Gmail legt gesendete Mails selbst ab).
- Infomaniak: IMAP/SMTP `mail.infomaniak.com`, `sent_folder = "Sent"`. Infomaniak vergibt Gerätekennwörter pro Programm (Manager → Adresse → «Geräte verbunden»).
- Gesendete Mails landen per IMAP APPEND im `sent_folder`, ein fehlender Ordner wird angelegt.

## Befehle

```bash
mailbox accounts                                   # Konten und Verbindungstest
mailbox list [KONTO] --unread [--limit 20] [--folder INBOX]   # ohne KONTO: alle Konten mit Passwortdatei
mailbox read KONTO UID [--html]
mailbox search KONTO 'SINCE 01-Sep-2026'           # IMAP-Suchsyntax, auch 'FROM "x"', 'SUBJECT "y"'
mailbox send KONTO --to x@y.ch --subject "…" --body-file text.txt [--cc …] [--attach datei.pdf] [--dry-run]
mailbox reply KONTO UID --body-file text.txt [--all] # Re:, In-Reply-To und References gesetzt
mailbox seen|unseen KONTO UID
mailbox move KONTO UID Trash
mailbox folders KONTO
```

UID ist die IMAP-UID im jeweiligen Ordner. Vollständige Hilfe: `mailbox --help`.

## Entwicklung

- Tests ohne Netz: `python3 -m unittest test_mailbox.py` im tools-Repo.
- Python 3.13+: `email.utils.getaddresses` liefert für leere Felder `('', '')`, darum filtert `addresses()` leere Kopfzeilen vorher; ohne das weist SMTP die Nachricht mit `SMTPRecipientsRefused: {}` ab.
