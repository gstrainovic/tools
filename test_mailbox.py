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
        self.assertEqual(msg.get_content().strip(), "Hallo")

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


if __name__ == "__main__":
    unittest.main()
