#!/usr/bin/env python3
"""
thunderbird-konten: Thunderbird mit ~/.config/mail/accounts.toml (Konten von mailbox) abgleichen.
Nur Python-Standardbibliothek, dazu libnss3 des Systems über ctypes für die Passwörter.

Legt fehlende Postfächer als IMAP-Konto mit SMTP-Server an; ein Konto, dessen `login` schon als Postfach
in Thunderbird steht (Domain-Alias), wird zusätzliche Identität dieses Kontos. Ergänzt nur: vorhandene
Konten, Ordner, Einstellungen und Mails bleiben unberührt. Vor jeder Änderung Sicherung von prefs.js,
logins.json und key4.db im Profil (<datei>.vor-thunderbird-konten-<zeit>). Läuft Thunderbird, bricht das
Werkzeug ab (Thunderbird überschreibt prefs.js beim Beenden), Thunderbird also vorher schliessen.

Passwörter neuer Konten kommen aus password_file und werden über NSS verschlüsselt in logins.json
eingetragen, nie ausgegeben. Klappt das nicht (Hauptpasswort, NSS fehlt), fragt Thunderbird beim ersten
Abruf nach dem Passwort.

Aufruf:
    thunderbird-konten [--dry-run] [--ohne-passwoerter] [--accounts PFAD] [--tb-root PFAD]
"""
import argparse
import configparser
import ctypes
import ctypes.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import uuid
from base64 import b64decode, b64encode
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

FLATPAK_ID = "org.mozilla.thunderbird_esr"
TB_ROOT = Path.home() / ".var/app" / FLATPAK_ID / ".thunderbird"
ACCOUNTS = Path.home() / ".config/mail/accounts.toml"
SICHERUNG = "vor-thunderbird-konten"

PREF_RE = re.compile(r'^user_pref\("((?:[^"\\]|\\.)*)",\s*(.*)\);\s*$')


class Abbruch(Exception):
    pass


# --- prefs.js ---

def _wert(roh):
    try:
        return json.loads(roh)
    except ValueError:
        return roh


def lese_prefs(text):
    prefs = {}
    for zeile in text.splitlines():
        m = PREF_RE.match(zeile)
        if m:
            prefs[json.loads(f'"{m.group(1)}"')] = _wert(m.group(2))
    return prefs


def pref_zeile(key, wert):
    if isinstance(wert, bool):
        roh = "true" if wert else "false"
    elif isinstance(wert, int):
        roh = str(wert)
    else:
        roh = json.dumps(str(wert), ensure_ascii=False)
    return f"user_pref({json.dumps(key)}, {roh});"


def schreibe_prefs(text, aenderungen):
    """Vorhandene Schlüssel zeilenweise ersetzen, neue anhängen; alle übrigen Zeilen bleiben wortgleich."""
    offen = dict(aenderungen)
    zeilen = []
    for zeile in text.splitlines():
        m = PREF_RE.match(zeile)
        if m:
            key = json.loads(f'"{m.group(1)}"')
            if key in offen:
                zeile = pref_zeile(key, offen.pop(key))
        zeilen.append(zeile)
    zeilen += [pref_zeile(k, v) for k, v in offen.items()]
    return "\n".join(zeilen) + "\n"


# --- Profil und Konten ---

def finde_profil(root):
    root = Path(root)

    def pfad(p):
        return Path(p) if p.startswith("/") else root / p

    for ini in ("installs.ini", "profiles.ini"):
        cp = configparser.ConfigParser(interpolation=None)
        cp.optionxform = str
        cp.read(root / ini)
        for abschnitt in cp.sections():
            if (ini == "installs.ini" or abschnitt.startswith("Install")) and cp[abschnitt].get("Default"):
                return pfad(cp[abschnitt]["Default"])
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str
    cp.read(root / "profiles.ini")
    for abschnitt in cp.sections():
        if abschnitt.startswith("Profile") and cp[abschnitt].get("Default") == "1":
            return pfad(cp[abschnitt]["Path"])
    raise Abbruch(f"kein Thunderbird-Profil in {root} gefunden")


def lese_konten(path):
    with open(path, "rb") as f:
        daten = tomllib.load(f)
    konten = []
    for key, k in daten.items():
        konten.append(dict(key=key, address=k["address"], login=k.get("login") or k["address"],
                           name=k.get("name", ""), imap=k["imap"], smtp=k.get("smtp") or k["imap"],
                           password_file=Path(k["password_file"]).expanduser(),
                           sent_folder=k.get("sent_folder", "Sent")))
    return konten


def _nummern(prefs, praefix, name):
    muster = re.compile(rf"^{re.escape(praefix)}{name}(\d+)\.")
    return {int(m.group(1)) for k in prefs if (m := muster.match(k))}


def ordner_url(login, host, ordner):
    return f"imap://{quote(login, safe='')}@{host}/{ordner}"


def plane(prefs, konten):
    """Liefert (aenderungen, meldungen, neue_postfaecher) für die fehlenden Konten."""
    if any(k.startswith("mail.outgoingserver") for k in prefs):
        raise Abbruch("Profil nutzt mail.outgoingserver.* statt mail.smtpserver.*, nicht unterstützt; nichts geändert")
    p = dict(prefs)
    aend, meldungen, neue = {}, [], []

    def setze(k, v):
        p[k] = v
        aend[k] = v

    def naechste(praefix, name):
        return max(_nummern(p, praefix, name) | {0}) + 1

    for konto in konten:
        emails = {v.lower() for k, v in p.items() if k.startswith("mail.identity.") and k.endswith(".useremail")}
        if konto["address"].lower() in emails:
            continue
        accounts = [a for a in str(p.get("mail.accountmanager.accounts", "")).split(",") if a]
        haupt = None
        for acc in accounts:
            srv = p.get(f"mail.account.{acc}.server")
            s = f"mail.server.{srv}"
            if (p.get(f"{s}.type") == "imap" and p.get(f"{s}.hostname") == konto["imap"]
                    and str(p.get(f"{s}.userName", "")).lower() == konto["login"].lower()):
                haupt = acc
                break
        idn = f"id{naechste('mail.identity.', 'id')}"
        i = f"mail.identity.{idn}"
        if haupt:
            idents = [x for x in str(p.get(f"mail.account.{haupt}.identities", "")).split(",") if x]
            erste = f"mail.identity.{idents[0]}" if idents else None
            setze(f"{i}.useremail", konto["address"])
            setze(f"{i}.fullName", konto["name"])
            setze(f"{i}.valid", True)
            if erste:
                for feld in ("smtpServer", "fcc_folder", "fcc_folder_picker_mode", "draft_folder",
                             "drafts_folder_picker_mode", "archive_folder", "archives_folder_picker_mode",
                             "doBcc", "attachPgpKey"):
                    if f"{erste}.{feld}" in p:
                        setze(f"{i}.{feld}", p[f"{erste}.{feld}"])
            setze(f"mail.account.{haupt}.identities", ",".join(idents + [idn]))
            meldungen.append(f"Identität {konto['address']} im Konto {konto['login']} ({haupt}, {idn})")
            continue
        nr = max(naechste("mail.account.", "account"), int(p.get("mail.account.lastKey", 0)) + 1)
        acc = f"account{nr}"
        srv = f"server{naechste('mail.server.', 'server')}"
        smtp = f"smtp{naechste('mail.smtpserver.', 'smtp')}"
        s, o = f"mail.server.{srv}", f"mail.smtpserver.{smtp}"
        login, host = konto["login"], konto["imap"]
        for k, v in [(f"{s}.type", "imap"), (f"{s}.hostname", host), (f"{s}.port", 993), (f"{s}.socketType", 3),
                     (f"{s}.authMethod", 3), (f"{s}.userName", login), (f"{s}.name", konto["address"]),
                     (f"{s}.using_subscription", False)]:
            setze(k, v)
        domain = konto["address"].split("@")[-1]
        beschreibung = f"Infomaniak {domain}" if "infomaniak" in konto["smtp"] else domain
        for k, v in [(f"{o}.hostname", konto["smtp"]), (f"{o}.port", 465), (f"{o}.try_ssl", 3),
                     (f"{o}.authMethod", 3), (f"{o}.username", login), (f"{o}.description", beschreibung)]:
            setze(k, v)
        setze(f"{i}.useremail", konto["address"])
        setze(f"{i}.fullName", konto["name"])
        setze(f"{i}.smtpServer", smtp)
        setze(f"{i}.valid", True)
        setze(f"{i}.doBcc", False)
        setze(f"{i}.attachPgpKey", False)
        if konto["sent_folder"]:
            setze(f"{i}.fcc_folder", ordner_url(login, host, konto["sent_folder"]))
            setze(f"{i}.fcc_folder_picker_mode", "1")
        setze(f"{i}.draft_folder", ordner_url(login, host, "Drafts"))
        setze(f"{i}.drafts_folder_picker_mode", "1")
        setze(f"{i}.archive_folder", ordner_url(login, host, "Archives"))
        setze(f"{i}.archives_folder_picker_mode", "1")
        setze(f"mail.account.{acc}.server", srv)
        setze(f"mail.account.{acc}.identities", idn)
        lokal = p.get("mail.accountmanager.localfoldersserver")
        pos = next((n for n, a in enumerate(accounts) if lokal and p.get(f"mail.account.{a}.server") == lokal),
                   len(accounts))
        setze("mail.accountmanager.accounts", ",".join(accounts[:pos] + [acc] + accounts[pos:]))
        setze("mail.account.lastKey", nr)
        smtps = [x for x in str(p.get("mail.smtpservers", "")).split(",") if x]
        setze("mail.smtpservers", ",".join(smtps + [smtp]))
        meldungen.append(f"Postfach {konto['address']} (Login {login}, IMAP {host}:993 SSL, "
                         f"SMTP {konto['smtp']}:465 SSL; {acc}, {srv}, {idn}, {smtp})")
        neue.append(konto)
    return aend, meldungen, neue


# --- NSS und logins.json ---

class SECItem(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("data", ctypes.POINTER(ctypes.c_ubyte)), ("len", ctypes.c_uint)]


class Nss:
    """libnss3 auf dem Profilordner (sql:), legt key4.db in einem leeren Ordner an."""

    def __init__(self, profil):
        name = ctypes.util.find_library("nss3")
        if not name:
            raise Abbruch("libnss3 nicht gefunden")
        lib = self.lib = ctypes.CDLL(name)
        lib.PK11_GetInternalKeySlot.restype = ctypes.c_void_p
        for f in ("PK11_NeedUserInit", "PK11_NeedLogin", "PK11_FreeSlot"):
            getattr(lib, f).argtypes = [ctypes.c_void_p]
        lib.PK11_InitPin.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.PK11_CheckUserPassword.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.PK11SDR_Encrypt.argtypes = [ctypes.POINTER(SECItem)] * 3 + [ctypes.c_void_p]
        lib.PK11SDR_Decrypt.argtypes = [ctypes.POINTER(SECItem)] * 2 + [ctypes.c_void_p]
        lib.SECITEM_ZfreeItem.argtypes = [ctypes.POINTER(SECItem), ctypes.c_int]
        if lib.NSS_IsInitialized():
            lib.NSS_Shutdown()
        if lib.NSS_InitReadWrite(f"sql:{profil}".encode()) != 0:
            raise Abbruch("NSS kann das Profil nicht öffnen")
        slot = lib.PK11_GetInternalKeySlot()
        try:
            if lib.PK11_NeedUserInit(slot):
                if lib.PK11_InitPin(slot, None, b"") != 0:
                    raise Abbruch("NSS-Schlüsseldatenbank liess sich nicht anlegen")
            elif lib.PK11_NeedLogin(slot) and lib.PK11_CheckUserPassword(slot, b"") != 0:
                raise Abbruch("Thunderbird-Profil hat ein Hauptpasswort")
        finally:
            lib.PK11_FreeSlot(slot)

    def _item(self, daten):
        puffer = (ctypes.c_ubyte * len(daten)).from_buffer_copy(daten)
        return SECItem(0, ctypes.cast(puffer, ctypes.POINTER(ctypes.c_ubyte)), len(daten)), puffer

    def verschluesseln(self, text):
        keyid = SECItem(0, None, 0)
        rein, _puffer = self._item(text.encode())
        raus = SECItem(0, None, 0)
        if self.lib.PK11SDR_Encrypt(ctypes.byref(keyid), ctypes.byref(rein), ctypes.byref(raus), None) != 0:
            raise Abbruch("PK11SDR_Encrypt fehlgeschlagen")
        try:
            return b64encode(ctypes.string_at(raus.data, raus.len)).decode()
        finally:
            self.lib.SECITEM_ZfreeItem(ctypes.byref(raus), 0)

    def entschluesseln(self, b64):
        rein, _puffer = self._item(b64decode(b64))
        raus = SECItem(0, None, 0)
        if self.lib.PK11SDR_Decrypt(ctypes.byref(rein), ctypes.byref(raus), None) != 0:
            raise ValueError("nicht entschlüsselbar")
        try:
            return ctypes.string_at(raus.data, raus.len).decode()
        finally:
            self.lib.SECITEM_ZfreeItem(ctypes.byref(raus), 0)

    def schliessen(self):
        self.lib.NSS_Shutdown()


def speichere_passwoerter(profil, konten):
    """Trägt imap:// und smtp:// je neuem Konto in logins.json ein; liefert die Anzahl neuer Einträge."""
    pfad = profil / "logins.json"
    daten = (json.loads(pfad.read_text()) if pfad.exists()
             else {"nextId": 1, "logins": [], "potentiallyVulnerablePasswords": [], "version": 3})
    nss = Nss(profil)
    try:
        def vorhanden(ziel, user):
            for l in daten["logins"]:
                if l.get("hostname") == ziel:
                    try:
                        if nss.entschluesseln(l["encryptedUsername"]) == user:
                            return True
                    except (ValueError, KeyError):
                        pass
            return False

        neu = 0
        for konto in konten:
            kennwort = konto["password_file"].read_text().strip()
            for schema, host in (("imap", konto["imap"]), ("smtp", konto["smtp"])):
                ziel = f"{schema}://{host}"
                if vorhanden(ziel, konto["login"]):
                    continue
                eintrag_pw = nss.verschluesseln(kennwort)
                if nss.entschluesseln(eintrag_pw) != kennwort:
                    raise Abbruch("Gegenprobe der Verschlüsselung fehlgeschlagen")
                jetzt = int(time.time() * 1000)
                daten["logins"].append({
                    "id": daten.get("nextId", 1), "hostname": ziel, "httpRealm": ziel, "formSubmitURL": None,
                    "usernameField": "", "passwordField": "",
                    "encryptedUsername": nss.verschluesseln(konto["login"]), "encryptedPassword": eintrag_pw,
                    "guid": "{" + str(uuid.uuid4()) + "}", "encType": 1, "timeCreated": jetzt,
                    "timeLastUsed": jetzt, "timePasswordChanged": jetzt, "timesUsed": 0})
                daten["nextId"] = daten.get("nextId", 1) + 1
                neu += 1
    finally:
        nss.schliessen()
    if neu:
        atomar_schreiben(pfad, json.dumps(daten, separators=(",", ":")))
    return neu


# --- Ablauf ---

def thunderbird_laeuft_flatpak():
    try:
        aus = subprocess.run(["flatpak", "ps", "--columns=application"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return False
    return any("thunderbird" in z.lower() for z in aus.split())


def atomar_schreiben(pfad, text):
    tmp = pfad.with_name(pfad.name + ".tmp-thunderbird-konten")
    tmp.write_text(text, encoding="utf-8")
    if pfad.exists():
        shutil.copymode(pfad, tmp)
    os.replace(tmp, pfad)


def sichern(profil):
    zeit = datetime.now().strftime("%Y%m%d-%H%M%S")
    pfade = []
    for name in ("prefs.js", "logins.json", "key4.db"):
        quelle = profil / name
        if quelle.exists():
            ziel = profil / f"{name}.{SICHERUNG}-{zeit}"
            shutil.copy2(quelle, ziel)
            pfade.append(ziel)
    return pfade


def main(argv=None, thunderbird_laeuft=thunderbird_laeuft_flatpak):
    ap = argparse.ArgumentParser(prog="thunderbird-konten", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="nur zeigen, was fehlt")
    ap.add_argument("--ohne-passwoerter", action="store_true", help="logins.json nicht anfassen")
    ap.add_argument("--accounts", type=Path, default=ACCOUNTS)
    ap.add_argument("--tb-root", type=Path, default=TB_ROOT)
    args = ap.parse_args(argv)
    try:
        profil = finde_profil(args.tb_root)
        prefs_pfad = profil / "prefs.js"
        text = prefs_pfad.read_text(encoding="utf-8")
        aend, meldungen, neue = plane(lese_prefs(text), lese_konten(args.accounts))
        print(f"Profil: {profil}")
        if not aend:
            print("nichts zu tun, Thunderbird kennt alle Konten aus", args.accounts)
            return 0
        print("fehlt:" if args.dry_run else "lege an:")
        for m in meldungen:
            print("  " + m)
        if args.dry_run:
            return 0
        if thunderbird_laeuft():
            raise Abbruch("Thunderbird läuft, bitte schliessen und erneut starten; nichts geändert")
        for p in sichern(profil):
            print(f"Sicherung: {p}")
        hinweis = None
        if args.ohne_passwoerter or not neue:
            hinweis = "Passwörter nicht gespeichert" if neue else None
        else:
            try:
                n = speichere_passwoerter(profil, neue)
                print(f"Passwörter gespeichert: {n} neue Einträge in logins.json (Gegenprobe ok)")
            except (Abbruch, OSError) as e:
                hinweis = f"Passwörter nicht gespeichert ({e})"
        if hinweis:
            print(f"{hinweis}: Thunderbird fragt beim ersten Abruf nach dem Passwort")
        atomar_schreiben(prefs_pfad, schreibe_prefs(text, aend))
        print(f"prefs.js ergänzt: {len(aend)} Einträge")
        return 0
    except Abbruch as e:
        print(f"Abbruch: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
