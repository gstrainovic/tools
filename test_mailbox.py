"""Tests für die reinen Bausteine von mailbox.py (ohne Netz): python3 -m unittest ~/.local/share/mailbox/test_mailbox.py"""
import contextlib
import email
import email.policy
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Eigener Modulname, weil «mailbox» in der Standardbibliothek existiert; vor exec registrieren (dataclasses braucht das)
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("mailbox_tool", HERE / "mailbox.py")
mb = importlib.util.module_from_spec(spec)
sys.modules["mailbox_tool"] = mb
spec.loader.exec_module(mb)


def account(**over):
    base = dict(key="test", address="info@wartungsheft.ch", name="Wartungsheft", imap="mail.example",
                smtp="mail.example", password_file=Path("/nonexistent"), sent_folder="Sent")
    base.update(over)
    return mb.Account(**base)


class Konfiguration(unittest.TestCase):
    def test_liest_konten_aus_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accounts.toml"
            path.write_text('[gmail]\naddress="a@gmail.com"\nname="A"\nimap="imap.gmail.com"\nsmtp="smtp.gmail.com"\n'
                            'password_file="/tmp/x"\nsent_folder=""\n[wh]\naddress="info@wartungsheft.ch"\nimap="mail.infomaniak.com"\n'
                            'password_file="/tmp/y"\n', encoding="utf-8")
            accounts = mb.load_accounts(path)
        self.assertEqual(list(accounts), ["gmail", "wh"])
        self.assertEqual(accounts["gmail"].sent_folder, "")
        self.assertEqual(accounts["wh"].smtp, "mail.infomaniak.com")
        self.assertEqual(accounts["wh"].sent_folder, "Sent")
        self.assertEqual(accounts["wh"].login, "info@wartungsheft.ch")

    def test_alias_absender_meldet_sich_mit_dem_postfach_an(self):
        # Domain-Alias: Absender info@x.dev, Anmeldung am Postfach info@x.ch
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accounts.toml"
            path.write_text('[dev]\naddress="info@x.dev"\nlogin="info@x.ch"\nimap="mail.infomaniak.com"\n'
                            'password_file="/tmp/y"\n', encoding="utf-8")
            acc = mb.load_accounts(path)["dev"]
        self.assertEqual(acc.login, "info@x.ch")
        self.assertIn("info@x.dev", acc.sender)


class Kopfzeilen(unittest.TestCase):
    def test_dekodiert_mime_kopfzeilen(self):
        self.assertEqual(mb.decode("=?utf-8?q?Gr=C3=BCezi_Herr_M=C3=BCller?="), "Grüezi Herr Müller")
        self.assertEqual(mb.decode(None), "")

    def test_adressen_auch_bei_leeren_feldern(self):
        self.assertEqual(mb.addresses("A <a@b.ch>", "", None, "c@d.ch, E <e@f.ch>"), ["a@b.ch", "c@d.ch", "e@f.ch"])
        self.assertEqual(mb.addresses("", None), [])

    def test_re_praefix_nur_einmal(self):
        self.assertEqual(mb.reply_subject("Offerte"), "Re: Offerte")
        self.assertEqual(mb.reply_subject("Re: Offerte"), "Re: Offerte")
        self.assertEqual(mb.reply_subject("AW: Offerte"), "AW: Offerte")


class Textkoerper(unittest.TestCase):
    def test_bevorzugt_text_plain(self):
        msg = email.message.EmailMessage()
        msg.set_content("Hallo\nText")
        msg.add_alternative("<p>Hallo</p><p>HTML</p>", subtype="html")
        self.assertEqual(mb.body_text(msg), "Hallo\nText")

    def test_html_zu_text_wenn_kein_plain(self):
        msg = email.message.EmailMessage()
        msg.set_content("<h1>Titel</h1><p>Erste&nbsp;Zeile<br>Zweite</p><style>p{}</style>", subtype="html")
        self.assertEqual(mb.body_text(msg), "Titel\nErste Zeile\nZweite")

    def test_nennt_anhaenge(self):
        msg = email.message.EmailMessage()
        msg.set_content("Text")
        msg.add_attachment(b"%PDF-", maintype="application", subtype="pdf", filename="Rechnung.pdf")
        self.assertEqual(mb.attachments(msg), ["Rechnung.pdf"])
        self.assertEqual(mb.body_text(msg), "Text")


class Nachrichten(unittest.TestCase):
    def test_baut_nachricht_mit_absender_und_antwortadresse(self):
        msg = mb.build_message(account(), ["kunde@example.ch"], "Offerte", "Hallo\n", cc=["chef@example.ch"], reply_to="info@wartungsheft.ch")
        self.assertEqual(msg["From"], "Wartungsheft <info@wartungsheft.ch>")
        self.assertEqual(msg["To"], "kunde@example.ch")
        self.assertEqual(msg["Cc"], "chef@example.ch")
        self.assertEqual(msg["Reply-To"], "info@wartungsheft.ch")
        self.assertIn("@wartungsheft.ch>", msg["Message-ID"])
        self.assertEqual(msg.get_body(("plain",)).get_content().strip(), "Hallo")

    def test_haengt_dateien_an(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "Goran-CV.pdf"
            pdf.write_bytes(b"%PDF-1.4 test")
            msg = mb.build_message(account(), ["a@b.ch"], "Bewerbung", "CV im Anhang\n", attachments=[pdf])
        parts = [p for p in msg.iter_attachments()]
        self.assertEqual([p.get_filename() for p in parts], ["Goran-CV.pdf"])
        self.assertEqual(parts[0].get_content_type(), "application/pdf")
        self.assertEqual(parts[0].get_payload(decode=True), b"%PDF-1.4 test")
        self.assertEqual(msg.get_body(("plain",)).get_content().strip(), "CV im Anhang")

    def test_antwort_haengt_am_faden(self):
        msg = mb.build_message(account(), ["a@b.ch"], "Re: X", "ok\n", in_reply_to="<m1@b.ch>", references="<m0@b.ch>")
        self.assertEqual(msg["In-Reply-To"], "<m1@b.ch>")
        self.assertEqual(msg["References"], "<m0@b.ch> <m1@b.ch>")

    def test_lange_message_id_bleibt_unkodiert(self):
        # Gmail- und Outlook-IDs sind länger als eine Kopfzeile; als RFC-2047-Wort (=?utf-8?q?…?=) ordnen
        # Mailprogramme die Antwort nicht mehr dem Faden zu
        lang = "<CAJx" + "7" * 70 + "Q@mail.gmail.com>"
        msg = mb.build_message(account(), ["a@b.ch"], "Re: X", "ok\n", in_reply_to=lang, references="<m0@b.ch>")
        roh = msg.as_bytes().decode()
        self.assertNotIn("=?", roh.split("\n\n", 1)[0].replace("\r", ""))
        kopf = email.message_from_bytes(msg.as_bytes(), policy=email.policy.default)
        self.assertEqual(kopf["In-Reply-To"].strip(), lang)
        self.assertEqual(" ".join(kopf["References"].split()), f"<m0@b.ch> {lang}")

    def test_antwortempfaenger_reply_to_vor_from_und_ohne_eigene_adresse(self):
        original = email.message_from_string(
            "From: Kunde <kunde@example.ch>\nReply-To: buero@example.ch\nTo: info@wartungsheft.ch, partner@example.ch\n"
            "Cc: chef@example.ch\nSubject: Frage\n\nHallo", policy=email.policy.default)
        to, cc = mb.reply_recipients(original, "info@wartungsheft.ch", all_recipients=False)
        self.assertEqual((to, cc), (["buero@example.ch"], []))
        to, cc = mb.reply_recipients(original, "info@wartungsheft.ch", all_recipients=True)
        self.assertEqual(to, ["buero@example.ch"])
        self.assertEqual(cc, ["partner@example.ch", "chef@example.ch"])

    def test_listenzeile(self):
        original = email.message_from_string(
            "From: =?utf-8?q?M=C3=BCller?= <m@example.ch>\nDate: Mon, 14 Sep 2026 10:30:00 +0200\nSubject: Offerte\n\nx",
            policy=email.policy.default)
        line = mb.format_line("wh", "42", original, unread=True)
        self.assertTrue(line.startswith("* wh"))
        self.assertIn("14.09.2026 10:30", line)
        self.assertIn("Müller", line)
        self.assertIn("Offerte", line)

    def test_listenzeile_bleibt_eine_zeile_bei_kodiertem_zeilenumbruch(self):
        # sonst täuscht ein fremder Betreff eine zweite Zeile mit beliebiger UID vor (fristen.py verschiebt danach)
        original = email.message_from_string(
            "From: =?utf-8?q?X=0A*_gmail_99?= <x@example.ch>\nDate: Mon, 14 Sep 2026 10:30:00 +0200\n"
            "Subject: =?utf-8?q?Hallo=0A*_gmail_____1234__01.01.2026_00:00__a__Akquise:_Fristen_f=C3=A4llig_(1)?=\n\nx",
            policy=email.policy.default)
        line = mb.format_line("gmail", "42", original, unread=False)
        self.assertEqual(len(line.splitlines()), 1)
        self.assertIn("X * gmail 99", line)
        self.assertIn("Hallo * gmail 1234", line)


SIGNATUR = ("Guten Tag\n\nText mit <Tag> & Co.\n\nFreundliche Grüsse\nGoran Strainovic\n\nStrainovic IT\n"
            "Bahnstrasse 9b\n9323 Steinach\ninfo@strainovic-it.ch\nwww.strainovic-it.ch\n")


class AntwortVorschau(unittest.TestCase):
    def test_eigene_gesendete_mail_antwortet_den_urspruenglichen_empfaengern(self):
        import contextlib
        import io
        from unittest import mock
        original = email.message_from_string(
            "From: Info <INFO@wartungsheft.ch>\nReply-To: info@wartungsheft.ch\n"
            "To: kunde@example.ch, partner@example.ch, info@wartungsheft.ch\n"
            "Cc: chef@example.ch, INFO@wartungsheft.ch, kunde@example.ch\n"
            "Message-ID: <original@example.ch>\nSubject: Offerte\n\nHallo",
            policy=email.policy.default)
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "antwort.txt"
            body.write_text("Nachfrage\n", encoding="utf-8")
            for alle in (False, True):
                with self.subTest(alle=alle):
                    args = type("A", (), {"account": "x", "folder": "Sent", "uid": "42",
                                         "all": alle, "body_file": str(body), "attach": [], "cc": [],
                                         "dry_run": True})()
                    out = io.StringIO()
                    with mock.patch.object(mb, "imap_connect"), \
                            mock.patch.object(mb, "fetch", return_value=(original, False)), \
                            mock.patch.object(mb, "smtp_send") as senden, contextlib.redirect_stdout(out):
                        mb.cmd_reply({"x": account()}, args)
                    msg = email.message_from_string(out.getvalue(), policy=email.policy.default)
                    self.assertEqual(mb.addresses(msg["To"]), ["kunde@example.ch", "partner@example.ch"])
                    self.assertEqual(mb.addresses(msg["Cc"]), ["chef@example.ch"] if alle else [])
                    self.assertEqual(msg["In-Reply-To"], "<original@example.ch>")
                    senden.assert_not_called()


class AntwortAufOutlookKopf(unittest.TestCase):
    def test_antwort_an_alle_trotz_zeilenumbruch_im_namen(self):
        # Gleiche Kopfzeile wie bei «Lesen»: reply --all brach mit «address parts cannot contain CR or LF» ab
        original = email.message_from_bytes(
            b"From: Sakshi <sakshi@example.com>\r\nTo: Info <info@wartungsheft.ch>\r\n"
            b"Cc: =?utf-8?Q?Hritavash=0A_Saha?= <growth@example.com>, Subhajit\r\n\t<subhajit@example.com>\r\n"
            b"Message-ID: <o@example.com>\r\nSubject: Partner\r\n\r\nHallo", policy=email.policy.default)
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "antwort.txt"
            body.write_text("Danke\n", encoding="utf-8")
            args = type("A", (), {"account": "x", "folder": "INBOX", "uid": "7", "all": True,
                                 "body_file": str(body), "attach": [], "cc": [], "dry_run": True})()
            out = io.StringIO()
            with mock.patch.object(mb, "imap_connect"), \
                    mock.patch.object(mb, "fetch", return_value=(original, False)), contextlib.redirect_stdout(out):
                mb.cmd_reply({"x": account()}, args)
        msg = email.message_from_string(out.getvalue(), policy=email.policy.default)
        self.assertEqual(mb.addresses(msg["To"]), ["sakshi@example.com"])
        self.assertEqual(mb.addresses(msg["Cc"]), ["growth@example.com", "subhajit@example.com"])
        self.assertEqual(msg["In-Reply-To"], "<o@example.com>")


class AntwortMitZitat(unittest.TestCase):
    ORIGINAL = ("From: =?utf-8?Q?B=2E_Hofer?= <mail@zeichenbuero.ch>\nTo: info@strainovic-it.ch\n"
                "Date: Wed, 28 Oct 2026 13:42:41 +0100\nMessage-ID: <z@zeichenbuero.ch>\n"
                "Subject: Ihre Frage\n\nSehr geehrter Herr Strainovic\n\nWas ist mit Tablets?\n> alter Text\n")

    def antwort(self, *extra):
        original = email.message_from_string(self.ORIGINAL, policy=email.policy.default)
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "antwort.txt"
            body.write_text("Guten Tag Frau Hofer\n\nTablets gehen gut.\n", encoding="utf-8")
            out = io.StringIO()
            with mock.patch.object(mb, "load_accounts", return_value={"x": account()}), \
                    mock.patch.object(mb, "imap_connect"), \
                    mock.patch.object(mb, "fetch", return_value=(original, False)), contextlib.redirect_stdout(out):
                mb.main(["reply", "x", "7", "--body-file", str(body), "--dry-run", *extra])
        return email.message_from_string(out.getvalue(), policy=email.policy.default)

    def test_antwort_haengt_original_als_zitat_an(self):
        msg = self.antwort()
        text = msg.get_body(("plain",)).get_content().replace("\r\n", "\n")
        self.assertIn("Tablets gehen gut.\n\nAm 28.10.2026 um 13:42 schrieb B. Hofer <mail@zeichenbuero.ch>:\n", text)
        self.assertIn("> Sehr geehrter Herr Strainovic\n>\n> Was ist mit Tablets?\n> > alter Text", text)
        html = msg.get_body(("html",)).get_content()
        self.assertIn("<blockquote", html)
        self.assertIn("Was ist mit Tablets?", html)

    def test_ohne_zitat_nur_eigener_text(self):
        text = self.antwort("--ohne-zitat").get_body(("plain",)).get_content()
        self.assertNotIn("schrieb", text)
        self.assertNotIn("Tablets?", text)


class Lesen(unittest.TestCase):
    def test_kopf_mit_zeilenumbruch_im_namen_bricht_nicht_ab(self):
        # Outlook kodiert gelegentlich einen Zeilenumbruch in den Anzeigenamen (=0A), policy.default wirft dann
        msg = email.message_from_bytes(
            b"From: Sakshi <sakshi@example.com>\r\nTo: info@example.ch\r\n"
            b"Cc: =?utf-8?Q?Hritavash=0A_Saha?= <growth@example.com>, Subhajit\r\n\t<subhajit@example.com>\r\n"
            b"Subject: Partner\r\n\r\nHallo", policy=email.policy.default)
        args = type("A", (), {"account": "x", "folder": "INBOX", "uid": "7", "html": False})()
        out = io.StringIO()
        with mock.patch.object(mb, "imap_connect"), \
                mock.patch.object(mb, "fetch", return_value=(msg, True)), contextlib.redirect_stdout(out):
            mb.cmd_read({"x": account()}, args)
        self.assertIn("growth@example.com", out.getvalue())
        self.assertIn("subhajit@example.com", out.getvalue())
        self.assertIn("Hallo", out.getvalue())


class HtmlFassung(unittest.TestCase):
    def test_alternative_mit_text_und_html(self):
        msg = mb.build_message(account(), ["a@b.ch"], "Test", SIGNATUR)
        self.assertEqual(msg.get_content_type(), "multipart/alternative")
        typen = [p.get_content_type() for p in msg.iter_parts()]
        self.assertEqual(typen, ["text/plain", "text/html"])
        self.assertEqual(msg.get_body(("plain",)).get_content(), SIGNATUR)

    def test_anhang_um_die_alternative(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "CV.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            msg = mb.build_message(account(), ["a@b.ch"], "Test", SIGNATUR, attachments=[pdf])
        self.assertEqual(msg.get_content_type(), "multipart/mixed")
        teile = list(msg.iter_parts())
        self.assertEqual(teile[0].get_content_type(), "multipart/alternative")
        self.assertEqual([p.get_content_type() for p in teile[0].iter_parts()], ["text/plain", "text/html"])
        self.assertEqual([p.get_filename() for p in msg.iter_attachments()], ["CV.pdf"])

    def test_html_umlaute_utf8(self):
        msg = mb.build_message(account(), ["a@b.ch"], "Test", SIGNATUR)
        html = msg.get_body(("html",))
        self.assertEqual(html.get_content_charset(), "utf-8")
        self.assertIn("Freundliche Grüsse", html.get_content())
        roh = email.message_from_bytes(msg.as_bytes(), policy=email.policy.default)
        self.assertIn("Grüsse", roh.get_body(("html",)).get_content())

    def test_jede_zeile_eigener_umbruch(self):
        html = mb.text_to_html(SIGNATUR)
        self.assertIn("Strainovic IT<br>\nBahnstrasse 9b<br>\n9323 Steinach<br>\n", html)
        self.assertIn("Freundliche Grüsse<br>\nGoran Strainovic</p>", html)
        self.assertEqual(html.count("<p"), 4)

    def test_keine_feste_schriftfarbe(self):
        # Feste Farben ohne Hintergrund werden im Dunkelmodus (Thunderbird, Outlook, Apple Mail) unlesbar:
        # dunkle Schrift auf dunklem Grund. Das Mailprogramm des Empfängers wählt die Farbe selbst.
        html = mb.text_to_html("Zeile\n\n> Zitat\n")
        self.assertNotIn("color", html)

    def test_escaping(self):
        html = mb.text_to_html("a < b & c > d\n")
        self.assertIn("a &lt; b &amp; c &gt; d", html)
        self.assertNotIn("<Tag>", mb.text_to_html(SIGNATUR))

    def test_links_fuer_urls_und_mailadressen(self):
        html = mb.text_to_html("Siehe https://uid.strainovic-it.ch/?a=1&b=2. Oder www.strainovic-it.ch, info@strainovic-it.ch\n")
        self.assertIn('<a href="https://uid.strainovic-it.ch/?a=1&amp;b=2">https://uid.strainovic-it.ch/?a=1&amp;b=2</a>. ', html)
        self.assertIn('<a href="https://www.strainovic-it.ch">www.strainovic-it.ch</a>,', html)
        self.assertIn('<a href="mailto:info@strainovic-it.ch">info@strainovic-it.ch</a>', html)

    def test_zitat_als_blockquote(self):
        html = mb.text_to_html("Danke\n\nAm 1.9. schrieb X:\n> Frage <1>\n> zweite Zeile\n")
        self.assertIn("<blockquote", html)
        self.assertIn("Frage &lt;1&gt;<br>\nzweite Zeile", html)
        self.assertNotIn("&gt; Frage", html)

    def test_schlicht_ohne_bilder(self):
        html = mb.text_to_html(SIGNATUR)
        self.assertIn("font-family", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("<script", html)

    def test_dry_run_zeigt_beide_teile(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "b.txt"
            body.write_text(SIGNATUR, encoding="utf-8")
            args = type("A", (), {"account": "x", "to": ["a@b.ch"], "subject": "T", "body_file": str(body), "cc": [],
                                  "bcc": [], "reply_to": None, "attach": [], "dry_run": True})()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                mb.cmd_send({"x": account()}, args)
        self.assertIn("multipart/alternative", out.getvalue())
        self.assertIn("text/plain", out.getvalue())
        self.assertIn("text/html", out.getvalue())


class Abmeldekopf(unittest.TestCase):
    """Akquise-Mails tragen List-Unsubscribe (Gmail und Yahoo zeigen damit «Abbestellen» statt «Spam melden»);
    One-Click (List-Unsubscribe-Post, RFC 8058) nur mit einer https-Adresse, die per POST abmeldet."""

    def senden(self, *zusatz: str) -> email.message.Message:
        import contextlib
        import io
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "b.txt"
            body.write_text(SIGNATUR, encoding="utf-8")
            out = io.StringIO()
            with mock.patch.object(mb, "load_accounts", lambda: {"x": account()}), contextlib.redirect_stdout(out):
                mb.main(["send", "x", "--to", "a@b.ch", "--subject", "T", "--body-file", str(body), "--dry-run", *zusatz])
        return email.message_from_string(out.getvalue())

    def test_akquise_mail_mit_mailto_auf_das_eigene_postfach(self):
        msg = self.senden("--list-unsubscribe")
        self.assertEqual(msg["List-Unsubscribe"], "<mailto:info@wartungsheft.ch?subject=Abmelden>")
        self.assertIsNone(msg["List-Unsubscribe-Post"])

    def test_one_click_nur_mit_url(self):
        msg = self.senden("--list-unsubscribe", "--unsubscribe-url", "https://www.wartungsheft.ch/abmelden?m=1")
        self.assertEqual(msg["List-Unsubscribe"],
                         "<https://www.wartungsheft.ch/abmelden?m=1>, <mailto:info@wartungsheft.ch?subject=Abmelden>")
        self.assertEqual(msg["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")

    def test_gewoehnliche_mail_ohne_abmeldekopf(self):
        msg = self.senden()
        self.assertIsNone(msg["List-Unsubscribe"])
        self.assertIsNone(msg["List-Unsubscribe-Post"])

    def test_url_ohne_https_wird_abgelehnt(self):
        with self.assertRaises(SystemExit):
            self.senden("--list-unsubscribe", "--unsubscribe-url", "http://www.wartungsheft.ch/abmelden")


class Suche(unittest.TestCase):
    def test_ascii_bleibt_unveraendert(self):
        self.assertEqual(mb.search_args('SUBJECT "neue Anmeldung"'), (['SUBJECT "neue Anmeldung"'], None))

    def test_umlaut_geht_als_utf8_literal_ans_ende(self):
        args, literal = mb.search_args('SUBJECT "Prüfung" SINCE 01-Sep-2026')
        self.assertEqual(args, ["CHARSET", "UTF-8", "SINCE 01-Sep-2026", "SUBJECT"])
        self.assertEqual(literal, "Prüfung".encode())

    def test_header_mit_feldname(self):
        args, literal = mb.search_args('HEADER Subject "Rückmeldung"')
        self.assertEqual(args, ["CHARSET", "UTF-8", "HEADER Subject"])
        self.assertEqual(literal, "Rückmeldung".encode())

    def test_zwei_umlaut_begriffe_werden_abgelehnt(self):
        with self.assertRaises(SystemExit):
            mb.search_args('FROM "Müller" SUBJECT "Prüfung"')


class Ordnernamen(unittest.TestCase):
    def test_einfacher_name_bleibt(self):
        self.assertEqual(mb.imap_folder("INBOX"), "INBOX")
        self.assertEqual(mb.imap_folder("[Gmail]/Spam"), "[Gmail]/Spam")

    def test_leerzeichen_wird_gequotet(self):
        self.assertEqual(mb.imap_folder("[Gmail]/Alle Nachrichten"), '"[Gmail]/Alle Nachrichten"')

    def test_anfuehrungszeichen_und_backslash_werden_escaped(self):
        self.assertEqual(mb.imap_folder('a "b"\\c'), '"a \\"b\\"\\\\c"')

    def test_schon_gequotet_bleibt(self):
        self.assertEqual(mb.imap_folder('"Alle Nachrichten"'), '"Alle Nachrichten"')

    def test_move_quotet_ziel_und_quelle(self):
        aufrufe = []

        class Conn:
            def list(self):
                return "OK", [b'(\\HasNoChildren) "/" "[Gmail]/Alle Nachrichten"']

            def select(self, folder, readonly=False):
                aufrufe.append(("select", folder))
                return "OK", [b"1"]

            def uid(self, *args):
                aufrufe.append(("uid", *args))
                return "OK", [None]

            def logout(self):
                pass

        original = mb.imap_connect
        mb.imap_connect = lambda acc: Conn()
        try:
            args = type("A", (), {"account": "x", "folder": "[Gmail]/Alle Nachrichten", "uid": "7",
                                  "target": "[Gmail]/Alle Nachrichten"})()
            mb.cmd_move({"x": None}, args)
        finally:
            mb.imap_connect = original
        self.assertIn(("select", '"[Gmail]/Alle Nachrichten"'), aufrufe)
        self.assertIn(("uid", "move", "7", '"[Gmail]/Alle Nachrichten"'), aufrufe)

    def test_umlaute_als_modified_utf7(self):
        # RFC 3501, 5.1.3; Beispiel «~peter/mail/台北/日本語» aus dem RFC
        self.assertEqual(mb.imap_folder("[Gmail]/Entwürfe"), "[Gmail]/Entw&APw-rfe")
        self.assertEqual(mb.imap_folder("~peter/mail/台北/日本語"), "~peter/mail/&U,BTFw-/&ZeVnLIqe-")
        self.assertEqual(mb.imap_folder("A&B"), "A&-B")
        self.assertEqual(mb.imap_folder("Gelöschte Elemente"), '"Gel&APY-schte Elemente"')

    def test_schon_kodierter_name_bleibt(self):
        self.assertEqual(mb.imap_folder("[Gmail]/Entw&APw-rfe"), "[Gmail]/Entw&APw-rfe")
        self.assertEqual(mb.imap_folder("A&-B"), "A&-B")

    def test_folders_zeigt_umlaute(self):
        class Conn:
            def list(self):
                return "OK", [b'(\\Drafts \\HasNoChildren) "/" "[Gmail]/Entw&APw-rfe"', b'(\\HasNoChildren) "/" INBOX']

            def logout(self):
                pass

        out = io.StringIO()
        with mock.patch.object(mb, "imap_connect", return_value=Conn()), contextlib.redirect_stdout(out):
            mb.cmd_folders({"x": None}, type("A", (), {"account": "x"})())
        self.assertIn("[Gmail]/Entwürfe", out.getvalue())
        self.assertIn("\\Drafts", out.getvalue())
        self.assertIn("INBOX", out.getvalue())

    def test_list_und_move_mit_umlaut_ordner(self):
        aufrufe = []

        class Conn:
            def list(self):
                return "OK", [b'(\\Drafts \\HasNoChildren) "/" "[Gmail]/Entw&APw-rfe"']

            def select(self, folder, readonly=False):
                folder.encode("ascii")  # imaplib kodiert Argumente als ASCII
                aufrufe.append(("select", folder))
                return "OK", [b"1"]

            def uid(self, *args):
                for a in args:
                    a.encode("ascii")
                aufrufe.append(("uid", *args))
                return "OK", [b""]

            def logout(self):
                pass

        with mock.patch.object(mb, "imap_connect", return_value=Conn()):
            mb.list_account(account(), "[Gmail]/Entwürfe", False, 3)
            for quelle, ziel in (("INBOX", "[Gmail]/Entwürfe"), ("[Gmail]/Entw&APw-rfe", "INBOX"),
                                 ("INBOX", "[Gmail]/Entw&APw-rfe")):
                args = type("A", (), {"account": "x", "folder": quelle, "uid": "7", "target": ziel})()
                with contextlib.redirect_stdout(io.StringIO()):
                    mb.cmd_move({"x": None}, args)
        self.assertEqual(aufrufe.count(("select", "[Gmail]/Entw&APw-rfe")), 2)
        self.assertEqual(aufrufe.count(("uid", "move", "7", "[Gmail]/Entw&APw-rfe")), 2)

    def test_trash_und_spam_werden_auf_die_gekennzeichneten_ordner_des_kontos_aufgeloest(self):
        # Gmail nennt den Papierkorb «[Gmail]/Papierkorb», Infomaniak «Trash»; die Kennzeichen \Trash und \Junk
        # aus LIST sagen, welcher Ordner gemeint ist
        liste = [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasChildren \\Trash) "/" "[Gmail]/Papierkorb"',
                 b'(\\HasNoChildren \\Junk) "/" "[Gmail]/Spam"', b'(\\HasNoChildren) "/" "Strainovic IT"']
        for name in ("Trash", "[Gmail]/Trash", "Papierkorb"):
            self.assertEqual(mb.resolve_folder(liste, name), "[Gmail]/Papierkorb")
        self.assertEqual(mb.resolve_folder(liste, "Spam"), "[Gmail]/Spam")
        self.assertEqual(mb.resolve_folder(liste, "Strainovic IT"), "Strainovic IT")
        self.assertEqual(mb.resolve_folder([b'(\\HasNoChildren \\Trash) "/" Trash'], "Trash"), "Trash")
        self.assertEqual(mb.resolve_folder([b'(\\Trash) "/" "Gel&APY-schte Elemente"'], "Trash"), "Gelöschte Elemente")

    def test_move_loescht_nichts_wenn_der_zielordner_fehlt(self):
        # Bisher: MOVE scheitert, COPY scheitert still, dann \Deleted plus EXPUNGE, und bei Gmail ist die Mail
        # nur noch im Archiv statt im Papierkorb
        aufrufe = []

        class Conn:
            def list(self):
                return "OK", [b'(\\HasChildren \\Trash) "/" "[Gmail]/Papierkorb"', b'(\\HasNoChildren) "/" "INBOX"']

            def select(self, folder, readonly=False):
                return "OK", [b"1"]

            def uid(self, *args):
                aufrufe.append(("uid", *args))
                if args[0] in ("move", "copy"):
                    return "NO", [b"[TRYCREATE] No folder"]
                return "OK", [None]

            def expunge(self):
                aufrufe.append(("expunge",))

            def logout(self):
                pass

        original = mb.imap_connect
        mb.imap_connect = lambda acc: Conn()
        try:
            args = type("A", (), {"account": "x", "folder": "INBOX", "uid": "7", "target": "Gibt-es-nicht"})()
            with self.assertRaises(SystemExit):
                mb.cmd_move({"x": None}, args)
            args.target = "[Gmail]/Trash"
            with self.assertRaises(SystemExit):
                mb.cmd_move({"x": None}, args)
        finally:
            mb.imap_connect = original
        self.assertIn(("uid", "move", "7", mb.imap_folder("[Gmail]/Papierkorb")), aufrufe, "Trash muss auf den Papierkorb zeigen")
        self.assertNotIn(("expunge",), aufrufe)
        self.assertFalse([a for a in aufrufe if a[1:3] == ("store", "7")], "ohne Kopie kein Löschen")


class Entwuerfe(unittest.TestCase):
    def test_entwurf_landet_im_entwurfsordner_ohne_smtp(self):
        aufrufe = []

        class Conn:
            def create(self, folder):
                aufrufe.append(("create", folder))

            def append(self, folder, flags, date, data):
                aufrufe.append(("append", folder, flags, data))
                return "OK", [None]

            def logout(self):
                pass

        acc = mb.Account(key="x", address="info@example.ch", name="Info", imap="i", smtp="s",
                         password_file=Path("/nicht/da"), drafts_folder="Entwürfe")
        msg = mb.build_message(acc, ["kunde@example.ch"], "Betreff", "Text\n")
        original_imap, original_smtp = mb.imap_connect, mb.smtplib.SMTP_SSL
        mb.imap_connect = lambda a: Conn()
        mb.smtplib.SMTP_SSL = lambda *a, **k: self.fail("Entwurf darf nicht per SMTP gehen")
        try:
            mb.save_draft(acc, msg)
        finally:
            mb.imap_connect, mb.smtplib.SMTP_SSL = original_imap, original_smtp
        append = [a for a in aufrufe if a[0] == "append"][0]
        self.assertEqual(append[1], mb.imap_folder("Entwürfe"))
        self.assertIn(r"\Draft", append[2])
        self.assertIn(b"multipart/alternative", append[3])

    def test_entwurfsordner_aus_konfiguration_mit_standard(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.toml"
            p.write_text('[a]\naddress="a@b.ch"\nimap="i"\npassword_file="x"\n'
                         '[g]\naddress="g@b.ch"\nimap="i"\npassword_file="x"\ndrafts_folder="[Gmail]/Entwürfe"\n',
                         encoding="utf-8")
            konten = mb.load_accounts(p)
        self.assertEqual(konten["a"].drafts_folder, "", "ohne Angabe: Ordner mit \\Drafts vom Server")
        self.assertEqual(konten["g"].drafts_folder, "[Gmail]/Entwürfe")

    GMAIL_LISTE = [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren) "/" "Drafts"',
                   b'(\\Drafts \\HasNoChildren) "/" "[Gmail]/Entw&APw-rfe"',
                   b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Gesendet"']

    def entwurf_speichern(self, liste, **konto):
        aufrufe = []

        class Conn:
            def list(self):
                return "OK", liste

            def create(self, folder):
                aufrufe.append(("create", folder))

            def append(self, folder, flags, date, data):
                aufrufe.append(("append", folder))
                return "OK", [None]

            def logout(self):
                pass

        acc = mb.Account(key="x", address="g@gmail.com", name="G", imap="i", smtp="s",
                         password_file=Path("/nicht/da"), **konto)
        msg = mb.build_message(acc, ["kunde@example.ch"], "Betreff", "Text\n")
        with mock.patch.object(mb, "imap_connect", return_value=Conn()), \
                mock.patch.object(mb.smtplib, "SMTP_SSL", side_effect=AssertionError("kein SMTP")):
            ordner = mb.save_draft(acc, msg)
        return ordner, aufrufe

    def test_gmail_entwurf_landet_im_ordner_mit_drafts_kennzeichen(self):
        # Bisher landete er im Label «Drafts», das Gmail und Thunderbird nicht als Entwürfe zeigen
        ordner, aufrufe = self.entwurf_speichern(self.GMAIL_LISTE)
        self.assertEqual([a for a in aufrufe if a[0] == "append"], [("append", "[Gmail]/Entw&APw-rfe")])
        self.assertNotIn(("create", "Drafts"), aufrufe)
        self.assertEqual(ordner, "[Gmail]/Entwürfe")

    def test_ohne_kennzeichen_bleibt_drafts(self):
        ordner, aufrufe = self.entwurf_speichern([b'(\\HasNoChildren) "/" "INBOX"'])
        self.assertIn(("append", "Drafts"), aufrufe)
        self.assertEqual(ordner, "Drafts")

    def test_entwurfsordner_aus_konfiguration_hat_vorrang(self):
        ordner, aufrufe = self.entwurf_speichern(self.GMAIL_LISTE, drafts_folder="Vorlagen")
        self.assertIn(("append", "Vorlagen"), aufrufe)
        self.assertEqual(ordner, "Vorlagen")

    def test_send_draft_meldet_den_tatsaechlichen_ordner(self):
        acc = account(drafts_folder="")
        with tempfile.TemporaryDirectory() as d:
            body = Path(d) / "b.txt"
            body.write_text("Text\n", encoding="utf-8")
            args = type("A", (), {"account": "test", "to": ["a@b.ch"], "subject": "S", "body_file": str(body),
                                  "cc": [], "bcc": [], "reply_to": None, "attach": [], "dry_run": False,
                                  "draft": True, "doppel_geprueft": None})()
            out = io.StringIO()
            with mock.patch.object(mb, "save_draft", return_value="[Gmail]/Entwürfe"), contextlib.redirect_stdout(out):
                mb.cmd_send({"test": acc}, args)
        self.assertIn("Entwurf gespeichert in [Gmail]/Entwürfe", out.getvalue())

    def test_send_und_reply_kennen_draft(self):
        for argv in (["send", "x", "--to", "a@b.ch", "--subject", "s", "--body-file", "f", "--draft"],
                     ["reply", "x", "7", "--body-file", "f", "--draft"]):
            aufgerufen = {}
            original = mb.load_accounts
            mb.load_accounts = lambda *a, **k: {}
            try:
                parser_args = None
                import argparse as _ap
                orig_parse = _ap.ArgumentParser.parse_args

                def fang(self, args=None, namespace=None):
                    ns = orig_parse(self, args, namespace)
                    aufgerufen["draft"] = getattr(ns, "draft", None)
                    raise SystemExit(0)
                _ap.ArgumentParser.parse_args = fang
                with self.assertRaises(SystemExit):
                    mb.main(argv)
            finally:
                _ap.ArgumentParser.parse_args = orig_parse
                mb.load_accounts = original
            self.assertTrue(aufgerufen["draft"], argv[0])

    def test_reply_mit_cc_setzt_weitere_empfaenger_in_kopie(self):
        # Kunde antwortet nur an uns, die Antwort soll aber auch an die bisherigen Beteiligten gehen
        original = email.message_from_string(
            "From: Juliane <juliane@kunde.de>\nTo: info@wartungsheft.ch\nSubject: AW: Rechnung\n"
            "Message-ID: <m1@kunde.de>\n\nText\n")
        acc = mb.Account(key="x", address="info@wartungsheft.ch", name="Goran", imap="i", smtp="s",
                         password_file="p")
        with tempfile.TemporaryDirectory() as d:
            body = Path(d) / "b.txt"
            body.write_text("Hallo", encoding="utf-8")
            out = io.StringIO()
            with mock.patch.object(mb, "load_accounts", return_value={"x": acc}), \
                 mock.patch.object(mb, "imap_connect"), \
                 mock.patch.object(mb, "fetch", return_value=(original, None)), \
                 contextlib.redirect_stdout(out):
                mb.main(["reply", "x", "7", "--body-file", str(body), "--dry-run",
                         "--cc", "thomas@kunde.de", "rechnung@kunde.de"])
        msg = email.message_from_string(out.getvalue())
        self.assertEqual(msg["To"], "juliane@kunde.de")
        self.assertEqual(msg["Cc"], "thomas@kunde.de, rechnung@kunde.de")

    def test_mehrfaches_attach_behaelt_alle_dateien(self):
        # Früher galt bei «--attach a --attach b» still nur b; der Empfänger bekam Anhänge nicht
        for argv in (["send", "x", "--to", "a@b.ch", "--subject", "s", "--body-file", "f",
                      "--attach", "a.pdf", "--attach", "b.pdf", "c.pdf"],
                     ["reply", "x", "7", "--body-file", "f", "--attach", "a.pdf", "--attach", "b.pdf", "c.pdf"]):
            aufgerufen = {}
            original = mb.load_accounts
            mb.load_accounts = lambda *a, **k: {}
            import argparse as _ap
            orig_parse = _ap.ArgumentParser.parse_args

            def fang(self, args=None, namespace=None):
                ns = orig_parse(self, args, namespace)
                aufgerufen["attach"] = getattr(ns, "attach", None)
                raise SystemExit(0)
            _ap.ArgumentParser.parse_args = fang
            try:
                with self.assertRaises(SystemExit):
                    mb.main(argv)
            finally:
                _ap.ArgumentParser.parse_args = orig_parse
                mb.load_accounts = original
            self.assertEqual(aufgerufen["attach"], ["a.pdf", "b.pdf", "c.pdf"], argv[0])


class Doppelversand(unittest.TestCase):
    """Am 16.10.2026 ging dieselbe Bewerbung zweimal an info@einradshop.ch: einmal als Entwurf aus Thunderbird,
    zwölf Minuten später per mailbox send aus einer zweiten Sitzung. Ging heute schon eine Mail an einen der
    Empfänger, sendet mailbox erst, wenn der Aufrufer beide Mails verglichen und den Grund angegeben hat."""

    FRUEHER = (b"From: Goran <info@strainovic-it.ch>\r\nTo: Info <INFO@einradshop.ch>\r\n"
               b"Subject: Nachfolgemodul universalpay\r\nDate: Fri, 16 Oct 2026 08:56:12 +0200\r\n"
               b"User-Agent: Mozilla Thunderbird\r\n\r\nZwei Wege sehe ich: universalpay anpassen.\r\n")

    def conn(self, gesendet: dict[str, bytes], ordner=b'(\\HasNoChildren \\Sent) "/" "Sent"'):
        aufrufe = self.aufrufe = []

        class Conn:
            def list(self):
                return "OK", [b'(\\HasNoChildren) "/" "INBOX"', ordner]

            def select(self, folder, readonly=False):
                aufrufe.append(("select", folder))
                return "OK", [b"1"]

            def uid(self, cmd, *args):
                aufrufe.append(("uid", cmd, *args))
                if cmd == "search":
                    return "OK", [" ".join(gesendet).encode()]
                return "OK", [(b"1 (UID " + args[0].encode() + b" BODY[] {1}", gesendet[args[0]]), b")"]

            def logout(self):
                pass

        return Conn()

    def senden(self, argv, gesendet, acc=None, ordner=None):
        acc = acc or account(address="info@strainovic-it.ch")
        conn = self.conn(gesendet, **({"ordner": ordner} if ordner else {}))
        with tempfile.TemporaryDirectory() as d:
            body = Path(d) / "b.txt"
            body.write_text("Neuer Entwurf: Zwei Wege sehe ich.", encoding="utf-8")
            argv = [a if a != "BODY" else str(body) for a in argv]
            out = io.StringIO()
            original = email.message_from_string("From: Stefan <info@einradshop.ch>\nTo: info@strainovic-it.ch\n"
                                                 "Subject: Antwort\nMessage-ID: <m@einradshop.ch>\n\nText\n")
            echt = mb.fetch
            holen = lambda c, uid, *a: (original, False) if uid == "7" else echt(c, uid, *a)  # noqa: E731
            with mock.patch.object(mb, "load_accounts", return_value={"x": acc}), \
                    mock.patch.object(mb, "imap_connect", return_value=conn), \
                    mock.patch.object(mb, "fetch", side_effect=holen), \
                    mock.patch.object(mb, "smtp_send") as smtp, mock.patch.object(mb, "mark"), \
                    mock.patch.object(mb, "save_draft"), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                code = 0
                try:
                    mb.main(argv)
                except SystemExit as e:
                    code = e.code
        return code, smtp, out.getvalue()

    SEND = ["send", "x", "--to", "info@einradshop.ch", "--subject", "Nachfolgemodul", "--body-file", "BODY"]

    def test_neues_postfach_ohne_gesendet_ordner_sendet(self):
        # info@pink-deko.ch, 21.10.2026: «Sent» entsteht erst beim ersten APPEND, SELECT antwortet NO
        conn = self.conn({})
        conn.select = lambda folder, readonly=False: ("NO", [b"Mailbox doesn't exist: Sent"])
        conn.uid = lambda *a: (_ for _ in ()).throw(AssertionError("SEARCH ohne SELECT"))
        with mock.patch.object(mb, "imap_connect", return_value=conn):
            self.assertEqual(mb.sent_today(account(address="info@pink-deko.ch"), ["info@einradshop.ch"]), [])

    def test_heute_schon_an_dieselbe_adresse_gesendet_sperrt_und_zeigt_beide_mails(self):
        code, smtp, out = self.senden(self.SEND, {"1367": self.FRUEHER})
        smtp.assert_not_called()
        self.assertNotEqual(code, 0)
        self.assertIn("Nachfolgemodul universalpay", out)  # Betreff der früheren Mail
        self.assertIn("Zwei Wege sehe ich: universalpay anpassen.", out)  # Text der früheren Mail
        self.assertIn("Neuer Entwurf: Zwei Wege sehe ich.", out)  # Text der neuen Mail
        self.assertIn("--doppel-geprueft", out)
        self.assertIn(("uid", "search", "SINCE " + mb.imap_date(mb.date.today())), self.aufrufe)

    def test_nach_pruefung_mit_grund_wird_gesendet(self):
        code, smtp, out = self.senden(self.SEND + ["--doppel-geprueft", "Angebot auf seine Antwort"],
                                      {"1367": self.FRUEHER})
        self.assertEqual(code, 0)
        smtp.assert_called_once()

    def test_frueheres_an_andere_adresse_sperrt_nicht(self):
        anders = self.FRUEHER.replace(b"INFO@einradshop.ch", b"info@schwimmboje.ch")
        code, smtp, _ = self.senden(self.SEND, {"1367": anders})
        self.assertEqual(code, 0)
        smtp.assert_called_once()

    def test_kopie_an_dieselbe_adresse_zaehlt_auch(self):
        cc = self.FRUEHER.replace(b"To: Info <INFO@einradshop.ch>", b"To: a@b.ch\r\nCc: info@einradshop.ch")
        code, smtp, _ = self.senden(self.SEND, {"1367": cc})
        self.assertNotEqual(code, 0)
        smtp.assert_not_called()

    def test_antwort_wird_ebenso_gesperrt(self):
        code, smtp, out = self.senden(["reply", "x", "7", "--body-file", "BODY"], {"1367": self.FRUEHER})
        self.assertNotEqual(code, 0)
        smtp.assert_not_called()
        self.assertIn("Zwei Wege sehe ich: universalpay anpassen.", out)

    def test_gmail_sucht_im_gekennzeichneten_gesendet_ordner(self):
        # Gmail legt Gesendetes selbst ab (sent_folder = ""), der Ordner heisst je Sprache anders
        gmail = account(address="g@gmail.com", sent_folder="")
        code, smtp, _ = self.senden(self.SEND, {"5": self.FRUEHER}, acc=gmail,
                                    ordner=b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Gesendet"')
        self.assertNotEqual(code, 0)
        self.assertIn(("select", mb.imap_folder("[Gmail]/Gesendet")), self.aufrufe)

    def test_entwurf_und_vorschau_pruefen_nicht(self):
        for extra in (["--draft"], ["--dry-run"]):
            code, smtp, _ = self.senden(self.SEND + extra, {"1367": self.FRUEHER})
            self.assertEqual(code, 0, extra)


if __name__ == "__main__":
    unittest.main()
