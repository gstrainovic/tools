#!/usr/bin/env -S uv run --script --quiet
# /// script
# dependencies = ["cryptography"]
# ///
"""Übernimmt Anmeldungen aus Gorans Chrome als Playwright-Speicherstand (Skill browser-wahl, «Sitzung übernehmen»).

Aufruf: chrome-sitzung <ziel.json> <domain> [domain …]
        chrome-sitzung /tmp/…/stand.json linkedin.com upwork.com freelancermap.de

Liest eine Kopie von ~/.config/google-chrome/Default/Cookies, entschlüsselt die Cookies der Domains samt Subdomains
(Schlüssel aus dem GNOME-Schlüsselbund, `secret-tool lookup application chrome`, AES-128-CBC; ab Datenbankversion 24
stehen 32 Byte SHA-256 des Hosts vor dem Wert) und schreibt sie mit chmod 600 im Format von `playwright-cli
state-load`. Werte werden nie ausgegeben, die Kopie der Datenbank wird gelöscht. Den Speicherstand nach der Arbeit
löschen. Meldet eine Domain «FEHLT», ist Goran dort in Chrome nicht angemeldet: Seite in Chrome öffnen, per Autofill
anmelden, erneut aufrufen. Ob die Sitzung gültig ist, zeigt erst der Login-Indikator im Browser.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DB = Path.home() / ".config/google-chrome/Default/Cookies"
CHROME_EPOCHE = 11_644_473_600  # Sekunden zwischen 1601 und 1970


def schluessel(passwort: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha1", passwort.encode(), b"saltysalt", 1, 16)


def entschluesseln(wert: bytes, k: bytes, version: int) -> str:
    if wert[:3] not in (b"v10", b"v11"):
        return wert.decode()
    d = Cipher(algorithms.AES(k), modes.CBC(b" " * 16)).decryptor()
    roh = d.update(wert[3:]) + d.finalize()
    u = padding.PKCS7(128).unpadder()
    klar = u.update(roh) + u.finalize()
    if version >= 24:
        klar = klar[32:]
    return klar.decode()


def cookie(host, name, wert, pfad, ablauf, secure, httponly, samesite):
    return {
        "name": name, "value": wert, "domain": host, "path": pfad,
        "expires": ablauf / 1_000_000 - CHROME_EPOCHE if ablauf else -1,
        "httpOnly": bool(httponly), "secure": bool(secure),
        "sameSite": {0: "None", 1: "Lax", 2: "Strict"}.get(samesite, "Lax"),
    }


def lesen(db, k, domains):
    """Cookies der Domains (samt Subdomains) aus einer Chrome-Cookie-Datenbank, entschlüsselt."""
    con = sqlite3.connect(db)
    try:
        version = int(con.execute("select value from meta where key='version'").fetchone()[0])
        bedingung = " or ".join("host_key = ? or host_key like ?" for _ in domains)
        werte = [w for d in domains for w in (d, f"%.{d}")]
        zeilen = con.execute("select host_key, name, encrypted_value, value, path, expires_utc, is_secure, "
                             f"is_httponly, samesite from cookies where {bedingung}", werte).fetchall()
    finally:
        con.close()
    return [cookie(h, n, entschluesseln(e, k, version) if e else v, p, a, s, ho, ss)
            for h, n, e, v, p, a, s, ho, ss in zeilen]


def schreiben(db, k, ziel, domains):
    """Speicherstand nach ziel schreiben (chmod 600); Bericht nennt je Domain die Anzahl Cookies oder FEHLT."""
    cookies = lesen(db, k, domains)
    fd = os.open(ziel, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"cookies": cookies, "origins": []}, f)
    anzahl = {d: sum(1 for c in cookies if c["domain"] == d or c["domain"].endswith(f".{d}")) for d in domains}
    return ", ".join(f"{d} {n or 'FEHLT'}" for d, n in anzahl.items())


def main(ziel, domains):
    passwort = subprocess.run(["secret-tool", "lookup", "application", "chrome"], capture_output=True, text=True,
                              check=True).stdout.strip()
    k = schluessel(passwort or "peanuts")
    with tempfile.TemporaryDirectory() as tmp:
        kopie = Path(tmp) / "Cookies"
        shutil.copy(DB, kopie)
        bericht = schreiben(kopie, k, ziel, domains)
    print(f"Speicherstand {ziel}: {bericht}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
