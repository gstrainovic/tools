#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["regex>=2024.11.6"]
# ///
"""fr-po-pruefen: französische Texte nach den Regeln des französischen WordPress-Teams prüfen.

    fr-po-pruefen DATEI [DATEI …] [--ausnahmen fr-ausnahmen.toml]
    fr-po-pruefen --glossar-aktualisieren

Exit-Code 0 ohne Fund, 1 bei Verstoss, ungenutzter Ausnahme oder fehlendem englischem Gegenstück. Je Fund:
Datei:Zeile, Regel, englisches Original und französischer Text.

Formate (Erkennung über Name und Inhalt), je französischer Text das englische Original:
- .po: msgstr gegen msgid (msgid_plural); Platzhalter printf (%s, %1$s, %%).
- Shopware-Snippet name.fr.json (oder fr-FR): Werte, nicht Schlüssel, gegen name.en.json; Platzhalter %name%.
- Shopware config.xml: Elemente mit lang="fr-FR" gegen das gleichnamige Geschwister ohne lang.
- composer.json: unter «extra» jeder Wert «fr-FR» gegen «en-GB», Links (http, mailto) ausgenommen; Platzhalter %name%.
- REDAXO fr_fr.lang («schluessel = wert») gegen en_gb.lang; Platzhalter {0}.
- Textpaare-JSON, etwa aus PHP exportiert: [{"stelle": "…", "en": "…", "fr": "…"}]; Zeile = Nummer des Paars.
  Ohne «en» (zusammengesetzte Zeile aus geprüften Texten und Daten) gilt nur die Typografie.
Ausnahmen mit «msgid» meinen in allen Formaten den englischen Originaltext.

Geprüft wird jede Übersetzung auf
1. Typografie und verbotene Wörter wie SPTE (github.com/Association-WPFR/SPTE, utils/rules.js, Version 3.1.1,
   GPL-2.0-or-later; die Regeln sind hier nachgebaut, Namen der Regeln wie dort). Abweichungen: vor «:» und «»»
   gilt nur U+00A0 (Gorans Entscheid 64b; vor «; ! ?» genügt U+00A0 oder U+202F wie in SPTE), Platzhalter zählen
   als Wort (SPTEs Ausnahmen für ' neben %s entfallen), HTML-Tags und URLs werden vorher ausgeblendet, dazu
   «prozent» und «einheit» aus dem Handbuch (U+00A0 vor %, zwischen Zahl und Einheit, Währung oder ×).
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
import json
import sys
import tomllib
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

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
    ("einheit", "zwischen Zahl und Einheit, Währung oder «×» fehlt U+00A0",
     r"(?<=\d)[ \t](?=(?:×|mm|cm|km|m²|kg|CHF|€|\$)(?!\w))", regex.M),
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


def _ausblenden(text, unveraendert, platzhalter=PLATZHALTER):
    """Text ohne Tags, URLs und unveränderte Texte; Platzhalter werden zu «X», bei printf «%%» zu «%»."""
    text = BR.sub("\n", text)
    text = TAG.sub("", text)
    text = URL.sub("X", text)
    for u in sorted(unveraendert, key=len, reverse=True):
        text = text.replace(u, "X")
    if platzhalter is PLATZHALTER:
        text = text.replace("%%", "\0")
    text = platzhalter.sub("X", text)
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

def pruefe(msgid, msgstr, ausnahmen=None, schluessel=None, platzhalter=PLATZHALTER, nur_typografie=False):
    """Funde für eine Übersetzung; schluessel ist der msgid (das englische Original), gegen den Ausnahmen verglichen
    werden; platzhalter ist das Muster der Platzhalter im jeweiligen Format. nur_typografie: ohne Original, also
    ohne Glossar, Platzhalter und HTML."""
    ausnahmen = ausnahmen or Ausnahmen()
    schluessel = msgid if schluessel is None else schluessel
    funde = []
    text = _ausblenden(msgstr, ausnahmen.unveraendert, platzhalter)
    for name, beschreibung, muster in REGELN:
        for m in muster.finditer(text):
            a, b = max(0, m.start() - 12), min(len(text), m.end() + 12)
            funde.append(Fund(name, beschreibung, text[a:b]))
    if nur_typografie:
        return [f for f in funde if not ausnahmen.erlaubt(f.regel, schluessel)]
    funde += glossar().funde(_ausblenden(msgid, ausnahmen.unveraendert, platzhalter), text)
    if sorted(platzhalter.findall(msgid)) != sorted(platzhalter.findall(msgstr)):
        funde.append(Fund("platzhalter", "Platzhalter anders als im Original: "
                          f"{sorted(platzhalter.findall(msgid))} → {sorted(platzhalter.findall(msgstr))}"))
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


# --- Weitere Formate: je französischer Text das englische Original ---------------------------------------------

SHOPWARE_PLATZHALTER = regex.compile(r"%[A-Za-z_]+%")
REDAXO_PLATZHALTER = regex.compile(r"\{\d+\}")
LINK = regex.compile(r"^(?:https?|mailto):", regex.I)


class FormatFehler(Exception):
    pass


@dataclass
class Text:
    zeile: int
    original: str | None  # None: kein englisches Gegenstück
    fr: str
    schluessel: str       # gegen ihn werden Ausnahmen verglichen (msgid bzw. englisches Original)
    stelle: str = ""      # Schlüssel im Format, nur zur Anzeige
    platzhalter: object = PLATZHALTER
    po: bool = False
    nur_typografie: bool = False  # Textpaar ohne «en»: zusammengesetzte Zeile ohne englisches Gegenstück


def _texte_po(pfad):
    for e in eintraege(pfad):
        for index, (msgstr, zeile) in sorted(e["msgstr"].items()):
            if msgstr:
                original = e["msgid"] if index == 0 or e["msgid_plural"] is None else e["msgid_plural"]
                yield Text(zeile, original, msgstr, e["msgid"], po=True)


def _partner(pfad, ersetzungen):
    name = pfad.name
    for alt, neu in ersetzungen:
        name = name.replace(alt, neu)
    partner = pfad.with_name(name)
    if name == pfad.name or not partner.exists():
        raise FormatFehler(f"{pfad}: englisches Gegenstück {partner.name} fehlt")
    return partner


def _blaetter(daten, praefix=""):
    for k, v in daten.items():
        if isinstance(v, dict):
            yield from _blaetter(v, f"{praefix}{k}.")
        else:
            yield f"{praefix}{k}", str(v)


def _zeilen_der_schluessel(roh, namen):
    """Zeile je Schlüssel in Dokumentreihenfolge: nächste Zeile ab der letzten, die «"name":» enthält."""
    zeilen, ab, ergebnis = roh.splitlines(), 0, []
    for name in namen:
        muster = regex.compile(rf'"{regex.escape(name)}"\s*:')
        for i in range(ab, len(zeilen)):
            if muster.search(zeilen[i]):
                ab = i
                break
        ergebnis.append(ab + 1)
    return ergebnis


def _texte_snippet(pfad, daten, roh):
    """Shopware-Snippet (name.fr.json oder name.fr-FR.json): Werte, nicht Schlüssel, gegen name.en(-GB).json."""
    partner = _partner(pfad, [(".fr.json", ".en.json"), ("fr-FR", "en-GB"), ("fr_FR", "en_GB")])
    englisch = dict(_blaetter(json.loads(partner.read_text(encoding="utf-8"))))
    blaetter = list(_blaetter(daten))
    zeilen = _zeilen_der_schluessel(roh, [k.rsplit(".", 1)[-1] for k, _ in blaetter])
    for (k, wert), zeile in zip(blaetter, zeilen):
        if wert:
            original = englisch.get(k)
            yield Text(zeile, original, wert, original or k, k, SHOPWARE_PLATZHALTER)


def _texte_composer(pfad, daten, roh):
    """composer.json eines Shopware-Plugins: unter «extra» jeder Wert «fr-FR» gegen «en-GB», ohne Links."""
    funde = []

    def suchen(o, weg):
        if isinstance(o, dict):
            if isinstance(o.get("fr-FR"), str):
                funde.append((weg, o))
            for k, v in o.items():
                suchen(v, f"{weg}.{k}")

    suchen(daten.get("extra", {}), "extra")
    vorkommen = [i + 1 for i, z in enumerate(roh.splitlines()) if '"fr-FR"' in z]
    for (weg, o), zeile in zip(funde, vorkommen):
        wert = o["fr-FR"]
        if wert and not LINK.match(wert):
            original = next((o[s] for s in ("en-GB", "en-US", "en") if isinstance(o.get(s), str)), None)
            yield Text(zeile, original, wert, original or weg, weg, SHOPWARE_PLATZHALTER)


def _texte_config_xml(pfad):
    """Shopware config.xml: jedes Element mit lang="fr-FR" gegen das gleichnamige Geschwister ohne lang (oder en-GB)."""
    roh = pfad.read_text(encoding="utf-8")
    wurzel = ElementTree.fromstring(roh.encode("utf-8"))
    vorkommen = [roh.count("\n", 0, m.start()) + 1 for m in regex.finditer(r'''lang\s*=\s*["']fr-FR["']''', roh)]
    fr_elemente = []
    for eltern in wurzel.iter():
        for kind in eltern:
            if kind.get("lang") == "fr-FR":
                fr_elemente.append((eltern, kind))
    reihenfolge = {id(e): i for i, e in enumerate(wurzel.iter())}
    fr_elemente.sort(key=lambda p: reihenfolge[id(p[1])])
    for (eltern, kind), zeile in zip(fr_elemente, vorkommen):
        wert = "".join(kind.itertext()).strip()
        en = [g for g in eltern if g.tag == kind.tag and g.get("lang") in (None, "en-GB")]
        original = "".join(en[0].itertext()).strip() if en else None
        name = eltern.findtext("name") or ""
        yield Text(zeile, original, wert, original or kind.tag, f"{eltern.tag} {name} {kind.tag}".replace("  ", " "))


LANG_ZEILE = regex.compile(r"^([^=\s#]+)\h*=\h*(\S.*?)\s*$")


def _lang_lesen(pfad):
    return {m.group(1): (m.group(2), nr) for nr, z in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1)
            if (m := LANG_ZEILE.match(z))}


def _texte_lang(pfad):
    """REDAXO lang/fr_fr.lang («schluessel = wert») gegen lang/en_gb.lang."""
    englisch = _lang_lesen(_partner(pfad, [("fr_fr", "en_gb"), ("fr_FR", "en_GB")]))
    for k, (wert, zeile) in _lang_lesen(pfad).items():
        original = englisch.get(k, (None,))[0]
        yield Text(zeile, original, wert, original or k, k, REDAXO_PLATZHALTER)


def _texte_paare(pfad, daten):
    """Textpaare, etwa aus PHP exportiert: [{"stelle": "…", "en": "…", "fr": "…"}]; Zeile = Nummer des Paars.
    Ohne «en» (zusammengesetzte Zeile ohne englisches Gegenstück) gilt nur die Typografie."""
    for nr, p in enumerate(daten, 1):
        if not isinstance(p, dict) or not isinstance(p.get("fr"), str):
            raise FormatFehler(f"{pfad}: Paar {nr} braucht «fr» (und «en», «stelle»)")
        if p["fr"]:
            stelle = p.get("stelle", "")
            if "en" in p:
                yield Text(nr, p["en"], p["fr"], p["en"] or stelle, stelle)
            else:
                yield Text(nr, "", p["fr"], stelle, stelle, nur_typografie=True)


def texte(pfad):
    """Alle französischen Texte einer Datei; das Format folgt aus Name und Inhalt."""
    pfad = Path(pfad)
    if pfad.suffix == ".po":
        return list(_texte_po(pfad))
    if pfad.suffix == ".lang":
        return list(_texte_lang(pfad))
    if pfad.suffix == ".xml":
        return list(_texte_config_xml(pfad))
    if pfad.suffix == ".json":
        roh = pfad.read_text(encoding="utf-8")
        daten = json.loads(roh)
        if pfad.name == "composer.json":
            return list(_texte_composer(pfad, daten, roh))
        if isinstance(daten, list):
            return list(_texte_paare(pfad, daten))
        return list(_texte_snippet(pfad, daten, roh))
    raise FormatFehler(f"{pfad}: unbekanntes Format (erwartet .po, .lang, config.xml, composer.json, .json)")


def _sichtbar(s):
    return s.replace(NB, "<U+00A0>").replace(NNB, "<U+202F>").replace("\n", "\\n")


def pruefe_dateien(dateien, ausnahmen, aus=sys.stdout):
    anzahl_funde = anzahl_eintraege = 0
    for datei in dateien:
        try:
            alle = texte(datei)
        except (FormatFehler, ValueError, ElementTree.ParseError) as fehler:
            print(f"fr-po-pruefen: {fehler}", file=aus)
            return 1
        for t in alle:
            anzahl_eintraege += 1
            if t.original is None:
                funde = [Fund("original", f"kein englisches Gegenstück zu «{t.stelle}»")]
            else:
                funde = pruefe(t.original, t.fr, ausnahmen, schluessel=t.schluessel, platzhalter=t.platzhalter,
                               nur_typografie=t.nur_typografie)
            for f in funde:
                anzahl_funde += 1
                stelle = f" bei «{_sichtbar(f.stelle)}»" if f.stelle else ""
                links, rechts = ("msgid ", "msgstr") if t.po else ("en", "fr")
                ort = f" [{t.stelle}]" if t.stelle else ""
                print(f"{datei}:{t.zeile}: {f.regel}: {f.beschreibung}{stelle}{ort}\n"
                      f"    {links} «{_sichtbar(t.original or '')}»\n    {rechts} «{_sichtbar(t.fr)}»", file=aus)
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
    p.add_argument("dateien", nargs="*", help="fr_FR.po, Shopware *.fr.json, config.xml, composer.json, "
                   "REDAXO fr_fr.lang oder Textpaare-JSON")
    p.add_argument("--ausnahmen", help="TOML-Datei mit Ausnahmen (unveraendert, [[ausnahme]])")
    p.add_argument("--glossar-aktualisieren", action="store_true",
                   help=f"Glossar neu von {GLOSSAR_URL} nach {GLOSSAR_ORDNER} laden")
    args = p.parse_args(argv)
    if args.glossar_aktualisieren:
        n = glossar_aktualisieren()
        print(f"Glossar aktualisiert: {n} Einträge in {GLOSSAR_ORDNER / 'glossar-fr.csv'}")
        return 0
    if not args.dateien:
        p.error("mindestens eine Datei angeben")
    return pruefe_dateien(args.dateien, Ausnahmen.laden(args.ausnahmen))


if __name__ == "__main__":
    sys.exit(main())
