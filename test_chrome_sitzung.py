"""Tests für chrome_sitzung.py: uv run --with cryptography python -m unittest test_chrome_sitzung.py"""
import hashlib
import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

spec = importlib.util.spec_from_file_location("chrome_sitzung", Path(__file__).with_name("chrome_sitzung.py"))
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def verschluesseln(klar: bytes, schluessel: bytes) -> bytes:
    p = padding.PKCS7(128).padder()
    roh = p.update(klar) + p.finalize()
    e = Cipher(algorithms.AES(schluessel), modes.CBC(b" " * 16)).encryptor()
    return b"v11" + e.update(roh) + e.finalize()


def chrome_db(pfad, zeilen, version=24):
    con = sqlite3.connect(pfad)
    con.execute("create table meta (key, value)")
    con.execute("insert into meta values ('version', ?)", (str(version),))
    con.execute("create table cookies (host_key, name, encrypted_value, value, path, expires_utc, is_secure, "
                "is_httponly, samesite)")
    con.executemany("insert into cookies values (?, ?, ?, '', '/', 0, 1, 1, 1)", zeilen)
    con.commit()
    con.close()


class Speicherstand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.k = s.schluessel("geheim")
        self.db = Path(self.tmp.name) / "Cookies"
        hashv = lambda h, v: verschluesseln(hashlib.sha256(h.encode()).digest() + v, self.k)  # noqa: E731
        chrome_db(self.db, [
            (".linkedin.com", "li_at", hashv(".linkedin.com", b"l1")),
            ("www.upwork.com", "sb", hashv("www.upwork.com", b"u1")),
            (".google.com", "SID", hashv(".google.com", b"g1")),
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_schreibt_nur_die_genannten_domains_als_playwright_speicherstand(self):
        ziel = Path(self.tmp.name) / "stand.json"
        bericht = s.schreiben(self.db, self.k, ziel, ["linkedin.com", "upwork.com", "freelance.de"])
        stand = json.loads(ziel.read_text())
        self.assertEqual(sorted((c["domain"], c["value"]) for c in stand["cookies"]),
                         [(".linkedin.com", "l1"), ("www.upwork.com", "u1")])
        self.assertEqual(stand["origins"], [])
        self.assertEqual(oct(os.stat(ziel).st_mode & 0o777), "0o600")
        self.assertIn("linkedin.com 1", bericht)
        self.assertIn("freelance.de FEHLT", bericht)
        self.assertNotIn("l1", bericht)

    def test_ab_version_24_faellt_der_hash_des_hosts_weg(self):
        wert = verschluesseln(hashlib.sha256(b".bexio.com").digest() + b"sitzung-123", self.k)
        self.assertEqual(s.entschluesseln(wert, self.k, 24), "sitzung-123")

    def test_playwright_cookie(self):
        c = s.cookie(".hubspot.com", "hubspotapi", "x", "/", 13_400_000_000_000_000, 1, 1, 1)
        self.assertEqual(c["domain"], ".hubspot.com")
        self.assertEqual(c["sameSite"], "Lax")
        self.assertAlmostEqual(c["expires"], 13_400_000_000 - 11_644_473_600, places=0)


if __name__ == "__main__":
    unittest.main()
