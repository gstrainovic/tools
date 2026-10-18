#!/usr/bin/env python3
"""
mailbox: mehrere Postfächer per IMAP/SMTP aus der Kommandozeile, für Agenten ohne Mailprogramm.
Nur Python-Standardbibliothek. Liest und schreibt direkt auf dem Server, ein Mailprogramm (Thunderbird)
zeigt denselben Stand.

Konten in ~/.config/mail/accounts.toml (Vorlage: mailbox-accounts.example.toml), Passwörter je Konto in
einer eigenen Datei (Anwendungs- oder Gerätekennwort, Modus 600), nie in der TOML-Datei:

    [firma]
    address = "info@example.ch"
    name = "Vorname Nachname"
    imap = "mail.infomaniak.com"
    smtp = "mail.infomaniak.com"
    password_file = "~/.config/mail/firma.pass"
    sent_folder = "Sent"        # Kopie per IMAP APPEND; "" wenn der Server selbst ablegt (Gmail)
    login = "info@example.ch"   # nur nötig, wenn address ein Domain-Alias eines anderen Postfachs ist

Befehle:
    mailbox accounts                                   Konten und Verbindungstest
    mailbox list [KONTO] [--unread] [--limit 20] [--folder INBOX]
    mailbox read KONTO UID [--folder INBOX] [--html]
    mailbox search KONTO 'FROM "x"' | 'SUBJECT "y"' | 'SINCE 01-Sep-2026' [--folder INBOX]
    mailbox send KONTO --to a@b.ch [--cc ...] [--bcc ...] --subject "…" --body-file text.txt [--reply-to ...] [--attach cv.pdf ...] [--list-unsubscribe [--unsubscribe-url https://…]] [--dry-run]
    mailbox reply KONTO UID --body-file text.txt [--all] [--cc ...] [--attach ...] [--folder INBOX] [--dry-run]
    mailbox seen KONTO UID | mailbox unseen KONTO UID
    mailbox move KONTO UID ZIELORDNER
    mailbox folders KONTO
send und reply schicken multipart/alternative: den Text unverändert plus eine daraus erzeugte schlichte HTML-Fassung
(jede Zeile mit <br>, Links, «>»-Zitate als Blockquote), damit Outlook keine Zeilen zusammenzieht.
Ohne KONTO bei list: alle Konten. Ausgabe ist Text, eine Zeile pro Mail, UID ist die IMAP-UID im Ordner.
"""
from __future__ import annotations

import argparse
import base64
import email
import email.policy
import imaplib
import mimetypes
import os
import re
import smtplib
import sys
import tomllib
from dataclasses import dataclass
from datetime import date
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parsedate_to_datetime
from html import escape, unescape
from pathlib import Path

CONFIG = Path(os.environ.get("MAILBOX_CONFIG", "~/.config/mail/accounts.toml")).expanduser()


@dataclass
class Account:
    key: str
    address: str
    name: str
    imap: str
    smtp: str
    password_file: Path
    sent_folder: str = "Sent"
    drafts_folder: str = ""  # leer: der Ordner, den der Server mit \Drafts kennzeichnet, sonst «Drafts»
    imap_port: int = 993
    smtp_port: int = 465
    login_name: str = ""  # Anmeldung, wenn sie vom Absender abweicht (Domain-Alias)

    @property
    def login(self) -> str:
        return self.login_name or self.address

    @property
    def has_password(self) -> bool:
        path = self.password_file.expanduser()
        return path.exists() and bool(path.read_text(encoding="utf-8").strip())

    @property
    def password(self) -> str:
        path = self.password_file.expanduser()
        if not self.has_password:
            raise SystemExit(f"{self.key}: Passwortdatei fehlt oder leer: {path}")
        return path.read_text(encoding="utf-8").strip()

    @property
    def sender(self) -> str:
        return formataddr((self.name, self.address))


def load_accounts(path: Path = CONFIG) -> dict[str, Account]:
    if not path.exists():
        raise SystemExit(f"Konfiguration fehlt: {path} (siehe Kopf von mailbox.py)")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    accounts: dict[str, Account] = {}
    for key, cfg in data.items():
        accounts[key] = Account(
            key=key,
            address=cfg["address"],
            name=cfg.get("name", ""),
            imap=cfg["imap"],
            smtp=cfg.get("smtp", cfg["imap"]),
            password_file=Path(cfg["password_file"]),
            sent_folder=cfg.get("sent_folder", "Sent"),
            drafts_folder=cfg.get("drafts_folder", ""),
            imap_port=int(cfg.get("imap_port", 993)),
            smtp_port=int(cfg.get("smtp_port", 465)),
            login_name=cfg.get("login", ""),
        )
    return accounts


# ---------- reine Helfer (getestet in test_mailbox.py) ----------

def decode(value: str | None) -> str:
    """MIME-kodierte Kopfzeile (=?utf-8?…?=) lesbar machen."""
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def body_text(msg: email.message.Message, prefer_html: bool = False) -> str:
    """Textkörper: text/plain bevorzugt, sonst HTML zu Text; Anhänge werden nur genannt."""
    plain, html = "", ""
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        ctype = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" in disposition:
            continue
        try:
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            content = payload.decode(charset, errors="replace") if payload else ""
        except Exception:
            continue
        if ctype == "text/plain" and not plain:
            plain = content
        elif ctype == "text/html" and not html:
            html = content
    if prefer_html and html:
        return html
    if plain.strip():
        return plain.strip()
    return html_to_text(html)


def attachments(msg: email.message.Message) -> list[str]:
    names = []
    for part in msg.walk():
        if "attachment" in str(part.get("Content-Disposition", "")):
            names.append(decode(part.get_filename()) or part.get_content_type())
    return names


def addresses(*fields: object) -> list[str]:
    """Adressen aus Kopfzeilen; leere Felder vorher entfernen, sonst liefert getaddresses ab Python 3.13 [('', '')]."""
    values = [str(f) for f in fields if f]
    return [addr for _, addr in email.utils.getaddresses(values) if addr]


LINK = re.compile(r"(?P<url>(?:https?://|www\.)[^\s<>\"]+)|(?P<mail>[\w.+-]+@[\w-]+(?:\.[\w-]+)+)")
HTML_STYLE = ("font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; "
              "font-size: 14px; line-height: 1.5;")  # keine Farbe: Dunkelmodus des Empfängers soll lesbar bleiben
P_STYLE = "margin: 0 0 1em 0;"
QUOTE_STYLE = "margin: 0 0 1em 0; padding-left: 0.8em; border-left: 3px solid #cccccc;"


def linkify(line: str) -> str:
    """Eine Textzeile HTML-escapen, URLs und Mailadressen als Links; Satzzeichen am Ende gehören nicht zum Link."""
    out, pos = [], 0
    for m in LINK.finditer(line):
        target = m.group(0)
        trail = ""
        if m.group("url"):
            stripped = target.rstrip(".,;:!?)")
            trail, target = target[len(stripped):], stripped
            href = target if target.startswith("http") else f"https://{target}"
        else:
            href = f"mailto:{target}"
        out.append(escape(line[pos:m.start()]))
        out.append(f'<a href="{escape(href)}">{escape(target)}</a>{escape(trail)}')
        pos = m.end()
    out.append(escape(line[pos:]))
    return "".join(out)


def _html_blocks(lines: list[str]) -> list[str]:
    """Absätze (durch Leerzeilen getrennt) als <p>, jede Zeile mit <br>; Zeilen mit «>» als <blockquote>."""
    blocks: list[str] = []
    paragraph: list[str] = []
    quote: list[str] = []

    def flush_paragraph():
        if paragraph:
            blocks.append(f'<p style="{P_STYLE}">' + "<br>\n".join(linkify(ln) for ln in paragraph) + "</p>")
            paragraph.clear()

    def flush_quote():
        if quote:
            inner = "\n".join(_html_blocks([re.sub(r"^> ?", "", ln) for ln in quote]))
            blocks.append(f'<blockquote style="{QUOTE_STYLE}">\n{inner}\n</blockquote>')
            quote.clear()

    for line in lines:
        if line.startswith(">"):
            flush_paragraph()
            quote.append(line)
        elif not line.strip():
            flush_paragraph()
            flush_quote()
        else:
            flush_quote()
            paragraph.append(line.rstrip())
    flush_paragraph()
    flush_quote()
    return blocks


def text_to_html(text: str) -> str:
    """HTML-Fassung einer Textmail, damit Outlook keine Zeilen zusammenklebt: schlicht, ohne Bilder und Tracking."""
    body = "\n".join(_html_blocks(text.splitlines()))
    return ('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n</head>\n'
            f'<body>\n<div style="{HTML_STYLE}">\n{body}\n</div>\n</body>\n</html>\n')


def reply_subject(subject: str) -> str:
    return subject if re.match(r"(?i)^\s*(re|aw|wg|fwd?)\s*:", subject) else f"Re: {subject}"


def build_message(
    account: Account,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
    attachments: list[Path] | None = None,
    list_unsubscribe: bool = False,
    unsubscribe_url: str | None = None,
) -> EmailMessage:
    # Zeilen bis 998 Zeichen (RFC 5322): Python 3.13 kodiert sonst lange Message-IDs in In-Reply-To und References
    # als =?utf-8?q?…?=, und Mailprogramme ordnen die Antwort nicht mehr dem Faden zu
    msg = EmailMessage(policy=email.policy.SMTP.clone(max_line_length=998))
    msg["From"] = account.sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=account.address.split("@")[1])
    if reply_to:
        msg["Reply-To"] = reply_to
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = f"{references} {in_reply_to}".strip() if references else in_reply_to
    if list_unsubscribe:
        # Akquise-Mails: Abmeldung per Antwort ans eigene Postfach; One-Click (RFC 8058) nur mit https-Adresse
        ziele = [f"<mailto:{account.address}?subject=Abmelden>"]
        if unsubscribe_url:
            if not unsubscribe_url.startswith("https://"):
                raise SystemExit(f"--unsubscribe-url braucht https: {unsubscribe_url}")
            ziele.insert(0, f"<{unsubscribe_url}>")
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        msg["List-Unsubscribe"] = ", ".join(ziele)
    msg.set_content(body)
    msg.add_alternative(text_to_html(body), subtype="html")
    for path in attachments or []:
        path = Path(path).expanduser()
        if not path.is_file():
            raise SystemExit(f"Anhang fehlt: {path}")
        ctype, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    return msg


def raw_header(msg: email.message.Message, name: str) -> str | None:
    """Kopfzeile als Rohtext ohne Faltung; msg.get wirft bei kodierten Zeilenumbrüchen im Anzeigenamen (Outlook)."""
    for key, value in msg.raw_items():
        if key.lower() == name.lower():
            return " ".join(str(value).split())
    return None


def reply_recipients(original: email.message.Message, own: str, all_recipients: bool) -> tuple[list[str], list[str]]:
    """Eigene Mail: ursprüngliche To; fremde Mail: Reply-To oder From; --all ergänzt Cc ohne uns."""
    get = lambda name: raw_header(original, name)  # noqa: E731
    to = addresses(get("Reply-To") or get("From"))
    if own.lower() in [a.lower() for a in addresses(get("From"))]:
        to = [a for a in addresses(get("To")) if a.lower() != own.lower()]
    cc: list[str] = []
    if all_recipients:
        others = addresses(get("To"), get("Cc"))
        cc = [a for a in others if a.lower() != own.lower() and a not in to]
    return to, cc


def format_line(account_key: str, uid: str, msg: email.message.Message, unread: bool) -> str:
    try:
        when = parsedate_to_datetime(msg.get("Date", "")).strftime("%d.%m.%Y %H:%M")
    except Exception:
        when = "?"
    sender = decode(msg.get("From", ""))
    subject = decode(msg.get("Subject", "")) or "(kein Betreff)"
    flag = "*" if unread else " "
    return f"{flag} {account_key:<12} {uid:>6}  {when}  {sender[:40]:<40}  {subject[:70]}"


# ---------- IMAP / SMTP ----------

def imap_connect(account: Account) -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL(account.imap, account.imap_port)
    conn.login(account.login, account.password)
    return conn


def fetch(conn: imaplib.IMAP4_SSL, uid: str, what: str = "(BODY.PEEK[] FLAGS)") -> tuple[email.message.Message, bool]:
    status, data = conn.uid("fetch", uid, what)
    if status != "OK" or not data or data[0] is None:
        raise SystemExit(f"UID {uid} nicht gefunden")
    raw = b""
    flags = b""
    for item in data:
        if isinstance(item, tuple):
            flags += item[0]
            raw += item[1]
        elif isinstance(item, bytes):
            flags += item
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    return msg, b"\\Seen" not in flags


def cmd_accounts(accounts: dict[str, Account], _args) -> None:
    for acc in accounts.values():
        if not acc.has_password:
            print(f"{acc.key:<12} {acc.address:<28} kein Passwort ({acc.password_file}), übersprungen")
            continue
        try:
            conn = imap_connect(acc)
            status, data = conn.select("INBOX", readonly=True)
            count = data[0].decode() if status == "OK" else "?"
            conn.logout()
            print(f"{acc.key:<12} {acc.address:<28} ok, INBOX {count} Mails")
        except Exception as err:
            print(f"{acc.key:<12} {acc.address:<28} FEHLER: {err}")


def cmd_folders(accounts: dict[str, Account], args) -> None:
    conn = imap_connect(accounts[args.account])
    status, boxes = conn.list()
    for box in boxes or []:
        line = box.decode(errors="replace") if isinstance(box, bytes) else str(box)
        m = LIST_ZEILE.match(box) if isinstance(box, bytes) else None
        if m:  # Namen lesbar, mit Umlauten statt Modified UTF-7
            name = list_folders([box])[0][1]
            line = line[:m.start("name")] + (f'"{name}"' if m.group("name").startswith(b'"') else name)
        print(line)
    conn.logout()


NON_ASCII_TERM = re.compile(r'((?:HEADER\s+\S+)|\w+)\s+"([^"]*[^\x00-\x7f][^"]*)"', re.IGNORECASE)


def search_args(criteria: str) -> tuple[list[str], bytes | None]:
    """IMAP-Suche als Argumente für conn.uid("search", ...). Ein Begriff mit Umlaut geht als UTF-8-Literal mit
    CHARSET UTF-8; imaplib hängt das Literal ans Kommandoende, darum wandert der Begriff nach hinten (die Suchschlüssel
    sind UND-verknüpft, die Reihenfolge ist egal). imaplib kennt nur ein Literal pro Kommando."""
    matches = list(NON_ASCII_TERM.finditer(criteria))
    if not matches:
        return [criteria], None
    if len(matches) > 1:
        raise SystemExit("Nur ein Suchbegriff mit Umlaut pro Suche möglich")
    match = matches[0]
    rest = (criteria[:match.start()] + criteria[match.end():]).strip()
    return ["CHARSET", "UTF-8", *([rest] if rest else []), match.group(1)], match.group(2).encode()


MUTF7_FOLGE = re.compile(r"&([A-Za-z0-9+,]*)-")


def mutf7_encode(name: str) -> str:
    """Ordnernamen nach IMAP Modified UTF-7 (RFC 3501, 5.1.3): «Entwürfe» → «Entw&APw-rfe», «&» → «&-»."""
    out: list[str] = []
    rest: list[str] = []

    def flush():
        if rest:
            b64 = base64.b64encode("".join(rest).encode("utf-16-be")).decode().rstrip("=").replace("/", ",")
            out.append(f"&{b64}-")
            rest.clear()

    for ch in name:
        if 0x20 <= ord(ch) <= 0x7E:
            flush()
            out.append("&-" if ch == "&" else ch)
        else:
            rest.append(ch)
    flush()
    return "".join(out)


def mutf7_decode(name: str) -> str:
    """Gegenstück zu mutf7_encode; ValueError, wenn der Name kein gültiges Modified UTF-7 ist."""
    if not name.isascii() or "&" in MUTF7_FOLGE.sub("", name):
        raise ValueError(f"kein Modified UTF-7: {name}")

    def zeichen(m: re.Match) -> str:
        if not m.group(1):
            return "&"
        b64 = m.group(1).replace(",", "/")
        return base64.b64decode(b64 + "=" * (-len(b64) % 4)).decode("utf-16-be")

    return MUTF7_FOLGE.sub(zeichen, name)


def folder_name(name: str) -> str:
    """Lesbarer Name: schon kodierte Namen («[Gmail]/Entw&APw-rfe») dekodiert, andere unverändert."""
    try:
        return mutf7_decode(name)
    except (ValueError, UnicodeDecodeError):
        return name


LIST_ZEILE = re.compile(rb'\((?P<flags>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<name>"(?:[^"\\]|\\.)*"|\S+)')


def list_folders(lines: list) -> list[tuple[bytes, str]]:
    """LIST-Antwort → (Kennzeichen, lesbarer Ordnername) je Ordner."""
    found = []
    for line in lines or []:
        m = LIST_ZEILE.match(line) if isinstance(line, bytes) else None
        if not m:
            continue
        raw = m.group("name").decode("ascii", errors="replace")
        if raw.startswith('"'):
            raw = re.sub(r'\\(.)', r'\1', raw[1:-1])
        found.append((m.group("flags"), folder_name(raw)))
    return found


def flagged_folder(lines: list, flag: bytes) -> str | None:
    return next((name for flags, name in list_folders(lines) if flag in flags.split()), None)


def imap_folder(name: str) -> str:
    """Ordnernamen für IMAP: Umlaute als Modified UTF-7 (schon kodierte Namen bleiben), dann quoten, imaplib tut
    beides nicht ("[Gmail]/Alle Nachrichten")."""
    if name.startswith('"') and name.endswith('"') and len(name) > 1 and name.isascii():
        return name
    name = mutf7_encode(folder_name(name))
    if re.search(r'[\s"\\(){%*]', name):
        return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return name


def list_account(acc: Account, folder: str, unread_only: bool, limit: int, query: str | None = None) -> list[str]:
    conn = imap_connect(acc)
    conn.select(imap_folder(folder), readonly=True)
    args, literal = search_args(query or ("UNSEEN" if unread_only else "ALL"))
    if literal is not None:
        conn.literal = literal
    status, data = conn.uid("search", *args)
    uids = data[0].split() if status == "OK" and data and data[0] else []
    lines = []
    for uid in uids[-limit:][::-1]:
        msg, unread = fetch(conn, uid.decode(), "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)] FLAGS)")
        lines.append(format_line(acc.key, uid.decode(), msg, unread))
    conn.logout()
    return lines


def cmd_list(accounts: dict[str, Account], args) -> None:
    keys = [args.account] if args.account else [k for k, a in accounts.items() if a.has_password]
    for key in keys:
        for line in list_account(accounts[key], args.folder, args.unread, args.limit):
            print(line)


def cmd_search(accounts: dict[str, Account], args) -> None:
    for line in list_account(accounts[args.account], args.folder, False, args.limit, args.query):
        print(line)


def cmd_read(accounts: dict[str, Account], args) -> None:
    acc = accounts[args.account]
    conn = imap_connect(acc)
    conn.select(imap_folder(args.folder), readonly=True)
    msg, unread = fetch(conn, args.uid)
    conn.logout()
    # Rohwerte statt msg.get: policy.default wirft bei kodierten Zeilenumbrüchen im Anzeigenamen (Outlook)
    raw = {k.lower(): v for k, v in reversed(list(msg.raw_items()))}
    for field in ("From", "To", "Cc", "Reply-To", "Date", "Subject", "Message-ID"):
        value = raw.get(field.lower())
        if value:
            print(f"{field}: {' '.join(decode(value).split())}")
    names = attachments(msg)
    if names:
        print(f"Anhänge: {', '.join(names)}")
    print(f"Ungelesen: {'ja' if unread else 'nein'}")
    print()
    print(body_text(msg, prefer_html=args.html))


def smtp_send(acc: Account, msg: EmailMessage) -> None:
    recipients = addresses(msg.get("To"), msg.get("Cc"), msg.get("Bcc"))
    if not recipients:
        raise SystemExit("Keine Empfänger")
    with smtplib.SMTP_SSL(acc.smtp, acc.smtp_port) as smtp:
        smtp.login(acc.login, acc.password)
        smtp.send_message(msg, to_addrs=recipients)
    if acc.sent_folder:
        conn = imap_connect(acc)
        # Neues Postfach hat noch keinen Ordner «Sent»; anlegen ist idempotent genug (Fehler beim Anlegen ignorieren)
        try:
            conn.create(imap_folder(acc.sent_folder))
        except imaplib.IMAP4.error:
            pass
        conn.append(imap_folder(acc.sent_folder), r"(\Seen)", imaplib.Time2Internaldate(__import__("time").time()), msg.as_bytes())
        conn.logout()


def save_draft(acc: Account, msg: EmailMessage) -> str:
    """Legt die Nachricht als Entwurf in den Entwurfsordner, ohne sie zu senden; Thunderbird zeigt sie dort.
    Entwurfsordner: drafts_folder aus der TOML, sonst der Ordner mit \\Drafts (Gmail: «[Gmail]/Entwürfe»), sonst
    «Drafts» (wird angelegt). Gibt den Ordnernamen lesbar zurück."""
    conn = imap_connect(acc)
    folder = acc.drafts_folder
    if not folder:
        status, lines = conn.list()
        folder = flagged_folder(lines if status == "OK" else [], rb"\Drafts")
    if not folder:
        folder = "Drafts"
        try:
            conn.create(imap_folder(folder))
        except imaplib.IMAP4.error:
            pass
    conn.append(imap_folder(folder), r"(\Draft \Seen)",
                imaplib.Time2Internaldate(__import__("time").time()), msg.as_bytes())
    conn.logout()
    return folder_name(folder)


def imap_date(day: date) -> str:
    """Datum für IMAP SINCE (01-Oct-2026), unabhängig von der Sprachvariante des Systems."""
    monate = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{day.day:02d}-{monate[day.month - 1]}-{day.year}"


def sent_today(acc: Account, recipients: list[str]) -> list[email.message.Message]:
    """Heute gesendete Mails an einen der Empfänger (To, Cc, Bcc), auch aus Thunderbird. Ohne sent_folder
    (Gmail) zählt der Ordner, den der Server mit \\Sent kennzeichnet."""
    wanted = {a.lower() for a in recipients}
    conn = imap_connect(acc)
    folder = acc.sent_folder
    if not folder:
        status, lines = conn.list()
        folder = flagged_folder(lines if status == "OK" else [], rb"\Sent")
    if not folder:
        conn.logout()
        return []
    conn.select(imap_folder(folder), readonly=True)
    status, data = conn.uid("search", f"SINCE {imap_date(date.today())}")
    found = []
    for uid in (data[0].split() if status == "OK" and data and data[0] else []):
        msg, _ = fetch(conn, uid.decode(), "(BODY.PEEK[])")
        sent_to = {a.lower() for a in addresses(raw_header(msg, "To"), raw_header(msg, "Cc"), raw_header(msg, "Bcc"))}
        if sent_to & wanted:
            found.append(msg)
    conn.logout()
    return found


def guard_double(acc: Account, msg: EmailMessage, checked: str | None) -> None:
    """Sperre gegen Doppelversand: Ging heute schon eine Mail an einen der Empfänger, zeigt sie alle diese Mails
    und die neue und bricht ab. Der Aufrufer (Agent) vergleicht sie und sendet nur eine neue Nachricht erneut,
    mit --doppel-geprueft und dem Grund."""
    if checked:
        print(f"Doppelversand geprüft: {checked}", file=sys.stderr)
        return
    recipients = addresses(msg.get("To"), msg.get("Cc"), msg.get("Bcc"))
    earlier = sent_today(acc, recipients)
    if not earlier:
        return
    out = [f"NICHT GESENDET: heute ging schon {len(earlier)} Mail an {', '.join(recipients)}.", ""]
    for old in earlier:
        out += [f"--- früher gesendet: {decode(raw_header(old, 'Date'))} an {decode(raw_header(old, 'To'))}",
                f"Betreff: {decode(raw_header(old, 'Subject'))}", "", body_text(old).strip(), ""]
    out += [f"--- neue Mail, Betreff: {decode(msg['Subject'])}", "", msg.get_body(("plain",)).get_content().strip(), "",
            "Vergleichen: Ist die neue Mail dieselbe Nachricht (auch umformuliert, gekürzt oder aus einem Entwurf schon "
            "gesendet), nicht senden. Ist sie eine neue Nachricht (Antwort, Angebot, Nachtrag), erneut aufrufen mit "
            '--doppel-geprueft "<Grund>".']
    print("\n".join(out), file=sys.stderr)
    raise SystemExit(3)


DOPPEL_HILFE = ("nur nach Vergleich mit den heute schon an dieselben Empfänger gesendeten Mails: Grund, warum die "
                "neue Mail keine Doppelung ist")


def read_body(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").rstrip("\n") + "\n"


def cmd_send(accounts: dict[str, Account], args) -> None:
    acc = accounts[args.account]
    msg = build_message(acc, args.to, args.subject, read_body(args.body_file), cc=args.cc, bcc=args.bcc, reply_to=args.reply_to,
                        attachments=[Path(a) for a in args.attach],
                        list_unsubscribe=getattr(args, "list_unsubscribe", False),
                        unsubscribe_url=getattr(args, "unsubscribe_url", None))
    if args.dry_run:
        print(msg.as_string())
        return
    if args.draft:
        folder = save_draft(acc, msg)
        print(f"Entwurf gespeichert in {folder} ({acc.address}): {args.subject}")
        return
    guard_double(acc, msg, args.doppel_geprueft)
    smtp_send(acc, msg)
    print(f"gesendet als {acc.address} an {', '.join(args.to)}: {args.subject}")


def cmd_reply(accounts: dict[str, Account], args) -> None:
    acc = accounts[args.account]
    conn = imap_connect(acc)
    conn.select(imap_folder(args.folder), readonly=True)
    original, _ = fetch(conn, args.uid)
    conn.logout()
    to, cc = reply_recipients(original, acc.address, args.all)
    cc += [a for a in args.cc if a not in cc and a not in to]
    msg = build_message(
        acc, to, reply_subject(decode(raw_header(original, "Subject") or "")), read_body(args.body_file), cc=cc,
        in_reply_to=raw_header(original, "Message-ID"), references=raw_header(original, "References"),
        attachments=[Path(a) for a in args.attach],
    )
    if args.dry_run:
        print(msg.as_string())
        return
    if args.draft:
        folder = save_draft(acc, msg)
        print(f"Entwurf gespeichert in {folder} ({acc.address}): {msg['Subject']}")
        return
    guard_double(acc, msg, args.doppel_geprueft)
    smtp_send(acc, msg)
    mark(acc, args.folder, args.uid, seen=True)
    print(f"geantwortet als {acc.address} an {', '.join(to)}: {msg['Subject']}")


def mark(acc: Account, folder: str, uid: str, seen: bool) -> None:
    conn = imap_connect(acc)
    conn.select(imap_folder(folder))
    conn.uid("store", uid, "+FLAGS" if seen else "-FLAGS", r"(\Seen)")
    conn.logout()


def cmd_seen(accounts: dict[str, Account], args) -> None:
    mark(accounts[args.account], args.folder, args.uid, seen=True)


def cmd_unseen(accounts: dict[str, Account], args) -> None:
    mark(accounts[args.account], args.folder, args.uid, seen=False)


SONDERORDNER = {"trash": rb"\Trash", "papierkorb": rb"\Trash", "spam": rb"\Junk", "junk": rb"\Junk"}


def resolve_folder(list_lines: list[bytes], name: str) -> str:
    """«Trash», «[Gmail]/Trash», «Papierkorb» oder «Spam» → der Ordner, den der Server mit \\Trash bzw. \\Junk
    kennzeichnet (Gmail: «[Gmail]/Papierkorb», Infomaniak: «Trash»). Andere Namen bleiben, wie sie sind."""
    kurz = name.rsplit("/", 1)[-1].lower()
    flag = SONDERORDNER.get(kurz)
    if not flag:
        return name
    return flagged_folder(list_lines, flag) or name


def cmd_move(accounts: dict[str, Account], args) -> None:
    conn = imap_connect(accounts[args.account])
    status, lines = conn.list()
    target_name = resolve_folder(lines if status == "OK" else [], args.target)
    conn.select(imap_folder(args.folder))
    target = imap_folder(target_name)
    status, _ = conn.uid("move", args.uid, target)
    if status != "OK":
        status, _ = conn.uid("copy", args.uid, target)
        if status != "OK":
            conn.logout()
            raise SystemExit(f"Zielordner {target_name} nicht gefunden, nichts verschoben (mailbox folders KONTO zeigt die Namen)")
        conn.uid("store", args.uid, "+FLAGS", r"(\Deleted)")
        conn.expunge()
    conn.logout()
    print(f"verschoben nach {target_name}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="mailbox", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("accounts").set_defaults(fn=cmd_accounts)

    p = sub.add_parser("folders")
    p.add_argument("account")
    p.set_defaults(fn=cmd_folders)

    p = sub.add_parser("list")
    p.add_argument("account", nargs="?")
    p.add_argument("--unread", action="store_true")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--folder", default="INBOX")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("search")
    p.add_argument("account")
    p.add_argument("query", help="IMAP-Suche, z. B. 'FROM \"muster.ch\"' oder 'SINCE 01-Sep-2026'")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--folder", default="INBOX")
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("read")
    p.add_argument("account")
    p.add_argument("uid")
    p.add_argument("--folder", default="INBOX")
    p.add_argument("--html", action="store_true", help="HTML-Teil roh statt als Text")
    p.set_defaults(fn=cmd_read)

    p = sub.add_parser("send")
    p.add_argument("account")
    p.add_argument("--to", nargs="+", required=True)
    p.add_argument("--cc", nargs="*", default=[])
    p.add_argument("--bcc", nargs="*", default=[])
    p.add_argument("--subject", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--reply-to")
    p.add_argument("--attach", nargs="+", action="extend", default=[],
                   help="Dateien anhängen, z. B. den CV als PDF; mehrfach angegeben werden alle angehängt")
    p.add_argument("--dry-run", action="store_true", help="Nachricht nur anzeigen")
    p.add_argument("--draft", action="store_true", help="nicht senden, als Entwurf in den Entwurfsordner legen")
    p.add_argument("--list-unsubscribe", action="store_true",
                   help="Akquise-Mail: Kopfzeile List-Unsubscribe mit mailto an das eigene Postfach (Betreff «Abmelden»)")
    p.add_argument("--unsubscribe-url", help="https-Adresse für One-Click-Abmeldung (List-Unsubscribe-Post), nur mit --list-unsubscribe")
    p.add_argument("--doppel-geprueft", metavar="GRUND", help=DOPPEL_HILFE)
    p.set_defaults(fn=cmd_send)

    p = sub.add_parser("reply")
    p.add_argument("account")
    p.add_argument("uid")
    p.add_argument("--body-file", required=True)
    p.add_argument("--all", action="store_true", help="Antwort an alle Empfänger")
    p.add_argument("--cc", nargs="+", action="extend", default=[], help="weitere Empfänger in Kopie")
    p.add_argument("--attach", nargs="+", action="extend", default=[])
    p.add_argument("--folder", default="INBOX")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--draft", action="store_true", help="nicht senden, als Entwurf in den Entwurfsordner legen")
    p.add_argument("--doppel-geprueft", metavar="GRUND", help=DOPPEL_HILFE)
    p.set_defaults(fn=cmd_reply)

    for name, fn in (("seen", cmd_seen), ("unseen", cmd_unseen)):
        p = sub.add_parser(name)
        p.add_argument("account")
        p.add_argument("uid")
        p.add_argument("--folder", default="INBOX")
        p.set_defaults(fn=fn)

    p = sub.add_parser("move")
    p.add_argument("account")
    p.add_argument("uid")
    p.add_argument("target")
    p.add_argument("--folder", default="INBOX")
    p.set_defaults(fn=cmd_move)

    args = parser.parse_args(argv)
    accounts = load_accounts()
    if getattr(args, "account", None) and args.account not in accounts:
        raise SystemExit(f"Unbekanntes Konto «{args.account}», bekannt: {', '.join(accounts)}")
    args.fn(accounts, args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
