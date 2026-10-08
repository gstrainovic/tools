"""Tests für die reinen Bausteine von mailbox.py (ohne Netz): python3 -m unittest ~/.local/share/mailbox/test_mailbox.py"""
import email
import email.policy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

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


SIGNATUR = ("Guten Tag\n\nText mit <Tag> & Co.\n\nFreundliche Grüsse\nGoran Strainovic\n\nStrainovic IT\n"
            "Bahnstrasse 9b\n9323 Steinach\ninfo@strainovic-it.ch\nwww.strainovic-it.ch\n")


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
        self.assertEqual(konten["a"].drafts_folder, "Drafts")
        self.assertEqual(konten["g"].drafts_folder, "[Gmail]/Entwürfe")

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


if __name__ == "__main__":
    unittest.main()
