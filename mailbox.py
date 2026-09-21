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

Befehle:
    mailbox accounts                                   Konten und Verbindungstest
    mailbox list [KONTO] [--unread] [--limit 20] [--folder INBOX]
    mailbox read KONTO UID [--folder INBOX] [--html]
    mailbox search KONTO 'FROM "x"' | 'SUBJECT "y"' | 'SINCE 01-Sep-2026' [--folder INBOX]
    mailbox send KONTO --to a@b.ch [--cc ...] [--bcc ...] --subject "…" --body-file text.txt [--reply-to ...] [--attach cv.pdf ...] [--dry-run]
    mailbox reply KONTO UID --body-file text.txt [--all] [--attach ...] [--folder INBOX] [--dry-run]
    mailbox seen KONTO UID | mailbox unseen KONTO UID
    mailbox move KONTO UID ZIELORDNER
    mailbox folders KONTO
Ohne KONTO bei list: alle Konten. Ausgabe ist Text, eine Zeile pro Mail, UID ist die IMAP-UID im Ordner.
"""
from __future__ import annotations

import argparse
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
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parsedate_to_datetime
from html import unescape
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
    imap_port: int = 993
    smtp_port: int = 465

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
            imap_port=int(cfg.get("imap_port", 993)),
            smtp_port=int(cfg.get("smtp_port", 465)),
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
) -> EmailMessage:
    msg = EmailMessage(policy=email.policy.SMTP)
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
    msg.set_content(body)
    for path in attachments or []:
        path = Path(path).expanduser()
        if not path.is_file():
            raise SystemExit(f"Anhang fehlt: {path}")
        ctype, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    return msg


def reply_recipients(original: email.message.Message, own: str, all_recipients: bool) -> tuple[list[str], list[str]]:
    """An wen die Antwort geht: Reply-To oder From; bei --all zusätzlich To/Cc ohne die eigene Adresse."""
    to = addresses(original.get("Reply-To") or original.get("From"))
    cc: list[str] = []
    if all_recipients:
        others = addresses(original.get("To"), original.get("Cc"))
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
    conn.login(account.address, account.password)
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
        print(box.decode(errors="replace"))
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


def list_account(acc: Account, folder: str, unread_only: bool, limit: int, query: str | None = None) -> list[str]:
    conn = imap_connect(acc)
    conn.select(folder, readonly=True)
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
    conn.select(args.folder, readonly=True)
    msg, unread = fetch(conn, args.uid)
    conn.logout()
    for field in ("From", "To", "Cc", "Reply-To", "Date", "Subject", "Message-ID"):
        if msg.get(field):
            print(f"{field}: {decode(msg.get(field))}")
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
        smtp.login(acc.address, acc.password)
        smtp.send_message(msg, to_addrs=recipients)
    if acc.sent_folder:
        conn = imap_connect(acc)
        # Neues Postfach hat noch keinen Ordner «Sent»; anlegen ist idempotent genug (Fehler beim Anlegen ignorieren)
        try:
            conn.create(acc.sent_folder)
        except imaplib.IMAP4.error:
            pass
        conn.append(acc.sent_folder, r"(\Seen)", imaplib.Time2Internaldate(__import__("time").time()), msg.as_bytes())
        conn.logout()


def read_body(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").rstrip("\n") + "\n"


def cmd_send(accounts: dict[str, Account], args) -> None:
    acc = accounts[args.account]
    msg = build_message(acc, args.to, args.subject, read_body(args.body_file), cc=args.cc, bcc=args.bcc, reply_to=args.reply_to,
                        attachments=[Path(a) for a in args.attach])
    if args.dry_run:
        print(msg.as_string())
        return
    smtp_send(acc, msg)
    print(f"gesendet als {acc.address} an {', '.join(args.to)}: {args.subject}")


def cmd_reply(accounts: dict[str, Account], args) -> None:
    acc = accounts[args.account]
    conn = imap_connect(acc)
    conn.select(args.folder, readonly=True)
    original, _ = fetch(conn, args.uid)
    conn.logout()
    to, cc = reply_recipients(original, acc.address, args.all)
    msg = build_message(
        acc, to, reply_subject(decode(original.get("Subject", ""))), read_body(args.body_file), cc=cc,
        in_reply_to=original.get("Message-ID"), references=original.get("References"),
        attachments=[Path(a) for a in args.attach],
    )
    if args.dry_run:
        print(msg.as_string())
        return
    smtp_send(acc, msg)
    mark(acc, args.folder, args.uid, seen=True)
    print(f"geantwortet als {acc.address} an {', '.join(to)}: {msg['Subject']}")


def mark(acc: Account, folder: str, uid: str, seen: bool) -> None:
    conn = imap_connect(acc)
    conn.select(folder)
    conn.uid("store", uid, "+FLAGS" if seen else "-FLAGS", r"(\Seen)")
    conn.logout()


def cmd_seen(accounts: dict[str, Account], args) -> None:
    mark(accounts[args.account], args.folder, args.uid, seen=True)


def cmd_unseen(accounts: dict[str, Account], args) -> None:
    mark(accounts[args.account], args.folder, args.uid, seen=False)


def cmd_move(accounts: dict[str, Account], args) -> None:
    conn = imap_connect(accounts[args.account])
    conn.select(args.folder)
    status, _ = conn.uid("move", args.uid, args.target)
    if status != "OK":
        conn.uid("copy", args.uid, args.target)
        conn.uid("store", args.uid, "+FLAGS", r"(\Deleted)")
        conn.expunge()
    conn.logout()
    print(f"verschoben nach {args.target}")


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
    p.add_argument("--attach", nargs="*", default=[], help="Dateien anhängen, z. B. den CV als PDF")
    p.add_argument("--dry-run", action="store_true", help="Nachricht nur anzeigen")
    p.set_defaults(fn=cmd_send)

    p = sub.add_parser("reply")
    p.add_argument("account")
    p.add_argument("uid")
    p.add_argument("--body-file", required=True)
    p.add_argument("--all", action="store_true", help="Antwort an alle Empfänger")
    p.add_argument("--attach", nargs="*", default=[])
    p.add_argument("--folder", default="INBOX")
    p.add_argument("--dry-run", action="store_true")
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
