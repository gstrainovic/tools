#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["regex>=2024.11.6"]
# ///
"""fr-po-pruefen: französische .po-Dateien nach den Regeln des französischen WordPress-Teams prüfen.

    fr-po-pruefen DATEI.po [DATEI.po …] [--ausnahmen fr-ausnahmen.toml]
    fr-po-pruefen --glossar-aktualisieren

Exit-Code 0 ohne Fund, 1 bei Verstoss oder ungenutzter Ausnahme. Je Fund: Datei:Zeile des msgstr, Regel, msgid.

Geprüft wird jede Übersetzung (msgstr) auf
1. Typografie und verbotene Wörter wie SPTE (github.com/Association-WPFR/SPTE, utils/rules.js, Version 3.1.1,
   GPL-2.0-or-later; die Regeln sind hier nachgebaut, Namen der Regeln wie dort). Abweichungen: vor «:» und «»»
   gilt nur U+00A0 (Gorans Entscheid 64b; vor «; ! ?» genügt U+00A0 oder U+202F wie in SPTE), Platzhalter zählen
   als Wort (SPTEs Ausnahmen für ' neben %s entfallen), HTML-Tags und URLs werden vorher ausgeblendet, dazu
   «prozent» aus dem Handbuch (U+00A0 vor %).
2. Glossar des französischen Teams (fr-po/glossar-fr.csv) wie GlotDict: kommt ein englischer Begriff im msgid
   vor, muss eine der französischen Entsprechungen mindestens gleich oft im msgstr stehen. Erkennung der
   englischen Formen angelehnt an GlotPress (gp_glossary_add_suffixes: -s, -es, -ies, -ed, -ing); Varianten mit
   «/» zählen einzeln; bei Verben auf -er/-ir/-re genügt der Stamm (Imperativ in Hilfetexten, «Sélectionnez»).
3. Platzhalter (%s, %1$s, %%) und HTML-Tags wie im msgid.

Ausnahmen (TOML, je Repo):
    unveraendert = ["Shop Invoices for KLARA"]   # Texte, die nie übersetzt werden; vor der Prüfung ausgeblendet
    [[ausnahme]]
    regel = "glossar:order"   # Regelname aus der Ausgabe
    msgid = "Order %s"        # optional, sonst gilt sie für alle Einträge
    grund = "…"               # Pflicht
"""
import argparse
import csv
import datetime
import sys
import tomllib
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import regex

GLOSSAR_URL = "https://translate.wordpress.org/locale/fr/default/glossary/-export/"
GLOSSAR_ORDNER = Path(__file__).resolve().parent / "fr-po"

NB = " "
NNB = " "
NB_ALLE = f"(?:{NB}|{NNB})"
GMI = regex.M | regex.I

# --- 1. SPTE, utils/rules.js (Version 3.1.1) -------------------------------------------------------------------

BAD_WORDS = ["etes vous", "ets", "fdp", "font-size", "melle", "n4est", "plug-in", "plug-ins", "responsif", "s4est",
             "plugin", "greffon", "uploader", "downloader", "customiser", "updater", "mr", "sidebar", "shortcode",
             "tooltip", "breadcrumb", "changelog", "thumbnail", "addon", "add-on", "back-end", "front-end",
             "capabilities", "en-tête", "et/ou", "customizer", "template", "templates", "add-ons", "événement"]
FILE_EXTENSIONS = "|".join([
    "avi", "bak", "bat", "bin", "bmp", "css", "csv", "doc", "docx", "eot", "exe", "gif", "git", "github", "htaccess",
    "html", "ico", "ics", "jpg", "jpeg", "js", "log", "maintenance", "mail", "mo", "mov", "mp3", "mp4", "mpeg", "otf",
    "pdf", "pem", "php", "po", "pot", "png", "ppt", "psd", "ods", "rar", "rtf", "svg", "sql", "tar", "gz", "tiff",
    "tif", "ttf", "txt", "vcf", "wav", "woff", "xls", "xlsx", "xml", "zip"])
WPCS = r"[^()]*\)\s*;"
_vor_wort = r"(?<=[\s,:;\"']|^)(?<!«\s)"
_nach_wort = r"(?=[\s,.:;\"']|$)"
_keine_zeit = rf"https|http| \d{{2}}|{NB}\d{{2}}| hh|{NB}hh| mm|{NB}mm| aaaa|{NB}aaaa|(?<![a-zA-Z])[gsiahymd]"


def _quote(q):
    return rf"(?<!href\=|href\='[a-z0-9.]*?|%[a-z]){q}(?!%[a-z])"


SPTE = [  # (Regel, Beschreibung, Muster, Flags)
    ("badWords", "Wort aus der SPTE-Liste (Anglizismus oder falsche Schreibweise)",
     _vor_wort + f"{_nach_wort}|{_vor_wort}".join(regex.escape(w) for w in BAD_WORDS) + _nach_wort, GMI),
    ("quotes", "gerader Apostroph ' statt ’", _quote("'"), regex.M),
    ("reversedQuote", "Apostroph ‘ statt ’", _quote("‘"), regex.M),
    ("doubleQuotes", "gerades Anführungszeichen \" statt « »",
     r'(?<!href\=|href\="[^"]*?|title\=|title\="[^"]*?)"', regex.M),
    ("slash", "Leerzeichen vor oder nach dem Schrägstrich",
     rf"(?<= |{NB})/(?!/|&gt;|\}}{{2}}|\]{{2}})|(?<!/)/(?= |{NB})", GMI),
    ("openHook", "vor «[» fehlt ein Leerzeichen oder danach steht eines", rf"(?<! |\[|^)\[(?!\[)|\[(?=[ |{NB}])", GMI),
    ("openParenthesis", "vor «(» fehlt ein Leerzeichen oder danach steht eines",
     rf"(?<![ ]|^|<br>|<br/>|<br />)\((?!{WPCS})(?!\%|\)|s\)|x\)|e\)|es\)|nt\)|vent\))|(?<!^)\((?!{WPCS})(?=[ |{NB}])",
     GMI),
    ("openBrace", "vor «{» fehlt ein Leerzeichen oder danach steht eines",
     rf"(?<! |\{{|^)\{{(?!\{{)|\{{(?=[ |{NB}])(?![ {NB}][a-zA-Z0-9]+\}})", GMI),
    ("ellipsis", "Leerzeichen vor «…» oder danach keines", rf"(?<=[ |{NB}])…|…(?=[a-zÀ-ú0-9]| $|{NB}$)", GMI),
    ("asciiEllipsis", "«...» statt «…»", r"\.\.\.", regex.M),
    ("period", "Leerzeichen vor dem Punkt oder danach keines",
     rf"(?<= |{NB})\.(?!{FILE_EXTENSIONS})|(?<![a-zÀ-ú0-9\.]*?)\.(?=[a-zÀ-ú0-9])|\.( $|{NB}$)", GMI),
    ("comma", "Leerzeichen vor dem Komma oder danach keines", rf"(?<=[ |{NB}]),|,(?=[a-zÀ-ú]| $|{NB}$)", GMI),
    ("closeHook", "Leerzeichen vor «]» oder danach keines",
     rf"(?<=[ |{NB}])\]|(?<!\])\](?=[a-zÀ-ú0-9]| $|{NB}$)", GMI),
    ("closeParenthesis", "Leerzeichen vor «)» oder danach keines",
     rf"(?<= |{NB}|\([a-d]|\([f-r]|\([t-w]|\([y-z])\)(?!\s*;)|\)(?=[a-rt-zÀ-ú0-9]{NB}$|{NB}[a-zÀ-ú]{{2,}})", GMI),
    ("closeBrace", "Leerzeichen vor «}» oder danach keines",
     rf"(?<=[ |{NB}])\}}|(?<!\}})\}}(?=[a-zÀ-ú0-9]|{NB}| $|{NB}$)", GMI),
    ("exclamationPoint", "vor «!» fehlt U+00A0 oder U+202F, oder danach kein Leerzeichen",
     rf"(?<!{NB_ALLE}|^)!(?!important)|!(?!important)(?! |$|\))", GMI),
    ("plusSign", "vor «+» fehlt U+00A0 oder danach kein Leerzeichen", rf"(?<!{NB}|google|^)\+|\+(?! |$)", GMI),
    ("questionMark", "vor «?» fehlt U+00A0 oder U+202F, oder danach kein Leerzeichen",
     rf"(?<!{NB_ALLE}|/|\.php|/[a-z0-9\-\#\.\_]*?|^)\?|(?<!/|\.php|/[a-z0-9\-\#\.\_]*?|^)\?(?! |$|\))", GMI),
    # Entscheid 64b: vor «:» nur U+00A0 (SPTE: U+00A0 oder U+202F)
    ("colon", "vor «:» fehlt U+00A0 oder danach kein Leerzeichen",
     rf"(?<!{NB}|{_keine_zeit}):(?= )|(?<={NB_ALLE}):(?! |$)|(?<!{NB}|{_keine_zeit}):(?! )", GMI),
    ("semiColon", "vor «;» fehlt U+00A0 oder U+202F, oder danach kein Leerzeichen",
     rf"(?<!{NB_ALLE}|:[a-z0-9.]*?|&[;a-z0-9#]*?);(?!$)|(?<!:[a-z0-9.]*?|&[;a-z0-9#]*?);(?! |$)", GMI),
    # Entscheid 64b: vor «»» nur U+00A0 (SPTE: U+00A0 oder U+202F)
    ("closingFrQuote", "vor «»» fehlt U+00A0 oder danach kein Leerzeichen",
     rf"(?<!{NB})»|»(?! |\.|,|{NB_ALLE}\?|{NB_ALLE}!|{NB_ALLE}:|{NB_ALLE};|&lt;|$)", GMI),
    ("openFrQuote", "nach «« » fehlt U+00A0 oder davor kein Leerzeichen", rf"(?<! |^|&gt;)«|«(?!{NB}|$)", GMI),
    ("epicenePunctuation", "Mittelpunkt · (U+00B7) statt Punkt, Bindestrich oder Stern",
     r"(?<=[a-zÀ-ú])[.\-*](?:e|rice|trice|ve|euse|esse|ale|ère|enne|ienne|elle)(?:[.\-*]s)?(?=[\s,.;:!?)»]|$)",
     regex.M),
    # Nicht in SPTE: Handbuch, Typografie-Tabelle
    ("prozent", "vor «%» fehlt U+00A0", rf"(?<!{NB}|^)%", regex.M),
]
REGELN = [(name, text, regex.compile(muster, flags)) for name, text, muster, flags in SPTE]

PLATZHALTER = regex.compile(r"%(?:\d+\$)?(?:[-+0]|'.)*\d*(?:\.\d+)?[bcdeEfFgGosuxX%]")
TAG = regex.compile(r"</?[a-zA-Z][^>]*>")
BR = regex.compile(r"<br\s*/?>", regex.I)
URL = regex.compile(r"https?://[^\s<>\"']+")


@dataclass
class Fund:
    regel: str
    beschreibung: str
    stelle: str = ""


@dataclass
class Ausnahmen:
    unveraendert: list = field(default_factory=list)
    regeln: list = field(default_factory=list)
    genutzt: set = field(default_factory=set)

    def __post_init__(self):
        for a in self.regeln:
            if not a.get("regel") or not str(a.get("grund", "")).strip():
                raise ValueError(f"Ausnahme braucht «regel» und «grund»: {a}")

    @classmethod
    def laden(cls, pfad):
        if not pfad:
            return cls()
        with open(pfad, "rb") as f:
            daten = tomllib.load(f)
        return cls(unveraendert=list(daten.get("unveraendert", [])), regeln=list(daten.get("ausnahme", [])))

    def erlaubt(self, regel, msgid):
        for i, a in enumerate(self.regeln):
            if a["regel"].lower() == regel.lower() and a.get("msgid", msgid) == msgid:
                self.genutzt.add(i)
                return True
        return False

    def ungenutzt(self):
        return [a for i, a in enumerate(self.regeln) if i not in self.genutzt]


def _ausblenden(text, unveraendert):
    """Text ohne Tags, URLs und unveränderte Texte; Platzhalter werden zu «X», «%%» zu «%»."""
    text = BR.sub("\n", text)
    text = TAG.sub("", text)
    text = URL.sub("X", text)
    for u in sorted(unveraendert, key=len, reverse=True):
        text = text.replace(u, "X")
    text = text.replace("%%", "\0")
    text = PLATZHALTER.sub("X", text)
    return text.replace("\0", "%")


# --- 2. Glossar -------------------------------------------------------------------------------------------------

def _normal(text):
    return text.lower().replace("’", "'").replace(NB, " ").replace(NNB, " ")


def _formen(begriff):
    """Englische Formen eines Glossarbegriffs, angelehnt an GlotPress gp_glossary_add_suffixes."""
    formen = {begriff, begriff + "s", begriff + "es", begriff + "ed", begriff + "ing"}
    if begriff.endswith("e"):
        formen |= {begriff + "d", begriff[:-1] + "ing"}
    if regex.search(r"[b-df-hj-np-tv-xz]y$", begriff):
        formen |= {begriff[:-1] + "ies", begriff[:-1] + "ied"}
    return formen


class Glossar:
    def __init__(self, pfad=GLOSSAR_ORDNER / "glossar-fr.csv"):
        self.name = {}          # Begriff klein -> Schreibweise im Glossar
        self.entsprechungen = {}  # Begriff klein -> französische Varianten (normalisiert)
        with open(pfad, encoding="utf-8", newline="") as f:
            for zeile in csv.DictReader(f):
                en, frz = zeile["en"].strip(), zeile["fr"].strip()
                if not en or not frz or frz == "N/A":
                    continue
                k = en.lower()
                self.name.setdefault(k, en)
                varianten = self.entsprechungen.setdefault(k, set())
                for v in [frz, *frz.split("/")]:
                    v = _normal(v.strip())
                    if not v:
                        continue
                    varianten.add(v)
                    stamm = v[:-2]
                    if zeile["pos"] == "verb" and " " not in v and v[-2:] in ("er", "ir", "re") and len(stamm) >= 4:
                        varianten.add(stamm)
        form_zu_begriff = {k: k for k in self.name}
        for k in self.name:
            for form in _formen(k):
                form_zu_begriff.setdefault(form, k)
        self.form_zu_begriff = form_zu_begriff
        alternativen = "|".join(regex.escape(f) for f in sorted(form_zu_begriff, key=len, reverse=True))
        self.muster = regex.compile(rf"(?<!\w)(?:{alternativen})(?!\w)", regex.I)

    def funde(self, original, uebersetzung):
        anzahl = Counter(self.form_zu_begriff[m.group(0).lower()] for m in self.muster.finditer(original))
        ziel = _normal(uebersetzung)
        for begriff, n in anzahl.items():
            varianten = self.entsprechungen[begriff]
            if not any(ziel.count(v) >= n for v in varianten):
                yield Fund(f"glossar:{self.name[begriff]}",
                           f"Glossar: «{self.name[begriff]}» verlangt eine von «{' / '.join(sorted(varianten))}»"
                           + (f" ({n}-mal)" if n > 1 else ""))


_glossar = None


def glossar():
    global _glossar
    if _glossar is None:
        _glossar = Glossar()
    return _glossar


def glossar_aktualisieren(url=GLOSSAR_URL, ordner=GLOSSAR_ORDNER):
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as antwort:
        daten = antwort.read()
    kopf = daten.decode("utf-8").splitlines()[0] if daten else ""
    if not kopf.startswith("en,fr"):
        raise ValueError(f"unerwarteter Inhalt von {url}: {kopf[:80]!r}")
    (ordner / "glossar-fr.csv").write_bytes(daten)
    (ordner / "glossar-fr.quelle").write_text(f"{url}\nabgerufen {datetime.date.today().isoformat()}\n",
                                              encoding="utf-8")
    return sum(1 for _ in csv.DictReader(daten.decode("utf-8").splitlines()))


# --- Prüfung ----------------------------------------------------------------------------------------------------

def pruefe(msgid, msgstr, ausnahmen=None, schluessel=None):
    """Funde für eine Übersetzung; schluessel ist der msgid, gegen den Ausnahmen verglichen werden."""
    ausnahmen = ausnahmen or Ausnahmen()
    schluessel = msgid if schluessel is None else schluessel
    funde = []
    text = _ausblenden(msgstr, ausnahmen.unveraendert)
    for name, beschreibung, muster in REGELN:
        for m in muster.finditer(text):
            a, b = max(0, m.start() - 12), min(len(text), m.end() + 12)
            funde.append(Fund(name, beschreibung, text[a:b]))
    funde += glossar().funde(_ausblenden(msgid, ausnahmen.unveraendert), text)
    if sorted(PLATZHALTER.findall(msgid)) != sorted(PLATZHALTER.findall(msgstr)):
        funde.append(Fund("platzhalter", "Platzhalter anders als im msgid: "
                          f"{sorted(PLATZHALTER.findall(msgid))} → {sorted(PLATZHALTER.findall(msgstr))}"))
    if sorted(TAG.findall(msgid)) != sorted(TAG.findall(msgstr)):
        funde.append(Fund("html", "HTML-Tags anders als im msgid"))
    return [f for f in funde if not ausnahmen.erlaubt(f.regel, schluessel)]


def _zitat(s):
    s = s.strip()
    if not (s.startswith('"') and s.endswith('"')):
        raise ValueError(f"kein PO-String: {s}")
    return regex.sub(r'\\(.)', lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s[1:-1])


def eintraege(pfad):
    """(msgid, msgid_plural, [(Index, msgstr, Zeile)]) je übersetztem Eintrag, ohne Kopf und #~."""
    ergebnis = []
    aktuell, feld = None, None

    def fertig():
        if aktuell and (aktuell["msgid"] or aktuell["msgctxt"]):
            ergebnis.append(aktuell)

    for nr, zeile in enumerate(Path(pfad).read_text(encoding="utf-8").splitlines(), 1):
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#"):
            continue
        m = regex.match(r'^(msgctxt|msgid_plural|msgid|msgstr(?:\[(\d+)\])?)\s+(".*")$', zeile)
        if m:
            schluessel, wert = m.group(1), _zitat(m.group(3))
            # Neuer Eintrag bei msgctxt und bei msgid, ausser der msgid folgt auf sein msgctxt
            if schluessel == "msgctxt" or (schluessel == "msgid" and (aktuell is None or aktuell["msgid"] is not None)):
                fertig()
                aktuell = {"msgctxt": None, "msgid": None, "msgid_plural": None, "msgstr": {}}
            if schluessel.startswith("msgstr"):
                index = int(m.group(2) or 0)
                aktuell["msgstr"][index] = [wert, nr]
                feld = ("msgstr", index)
            else:
                aktuell[schluessel] = wert
                feld = (schluessel, None)
        elif zeile.startswith('"') and aktuell is not None and feld:
            wert = _zitat(zeile)
            if feld[0] == "msgstr":
                aktuell["msgstr"][feld[1]][0] += wert
            else:
                aktuell[feld[0]] += wert
    fertig()
    return ergebnis


def _sichtbar(s):
    return s.replace(NB, "<U+00A0>").replace(NNB, "<U+202F>").replace("\n", "\\n")


def pruefe_dateien(dateien, ausnahmen, aus=sys.stdout):
    anzahl_funde = anzahl_eintraege = 0
    for datei in dateien:
        for e in eintraege(datei):
            for index, (msgstr, zeile) in sorted(e["msgstr"].items()):
                if not msgstr:
                    continue
                anzahl_eintraege += 1
                original = e["msgid"] if index == 0 or e["msgid_plural"] is None else e["msgid_plural"]
                for f in pruefe(original, msgstr, ausnahmen, schluessel=e["msgid"]):
                    anzahl_funde += 1
                    stelle = f" bei «{_sichtbar(f.stelle)}»" if f.stelle else ""
                    print(f"{datei}:{zeile}: {f.regel}: {f.beschreibung}{stelle}\n"
                          f"    msgid  «{_sichtbar(e['msgid'])}»\n    msgstr «{_sichtbar(msgstr)}»", file=aus)
    ungenutzt = ausnahmen.ungenutzt()
    for a in ungenutzt:
        print(f"ungenutzte Ausnahme (entfernen): regel={a['regel']!r} msgid={a.get('msgid', '*')!r}", file=aus)
    if anzahl_funde or ungenutzt:
        print(f"fr-po-pruefen: {anzahl_funde} Funde, {len(ungenutzt)} ungenutzte Ausnahmen", file=aus)
        return 1
    print(f"fr-po-pruefen: {anzahl_eintraege} Übersetzungen in {len(dateien)} Dateien ohne Fund", file=aus)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="fr-po-pruefen", description=__doc__.split("\n\n")[0])
    p.add_argument("dateien", nargs="*", help="fr_FR.po-Dateien")
    p.add_argument("--ausnahmen", help="TOML-Datei mit Ausnahmen (unveraendert, [[ausnahme]])")
    p.add_argument("--glossar-aktualisieren", action="store_true",
                   help=f"Glossar neu von {GLOSSAR_URL} nach {GLOSSAR_ORDNER} laden")
    args = p.parse_args(argv)
    if args.glossar_aktualisieren:
        n = glossar_aktualisieren()
        print(f"Glossar aktualisiert: {n} Einträge in {GLOSSAR_ORDNER / 'glossar-fr.csv'}")
        return 0
    if not args.dateien:
        p.error("mindestens eine .po-Datei angeben")
    return pruefe_dateien(args.dateien, Ausnahmen.laden(args.ausnahmen))


if __name__ == "__main__":
    sys.exit(main())
