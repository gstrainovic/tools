#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["ddgs>=9"]
# ///
"""
recherche: Websuche per Skript (ddgs und Exa), Trefferseiten per curl holen und nur Ort, Preise und
Stichwortstellen ausgeben, damit das Modell keine ganzen Seiten liest (Skill recherche, «Zuerst per Skript»).

  recherche.py -q "spray tanning st. gallen" -q "sprühbräune ostschweiz" --muster "spray ?tan|sprühbräun" -m 8

Optionen: -r Region für ddgs (Standard ch-de), -m Treffer je Anfrage und Quelle, --ohne-exa, --ohne-ddgs,
--stellen Anzahl Stichwortstellen je Seite (Standard 3), --json für die Rohdaten. Exa-Schlüssel in ~/.config/exa/key.
"""
import argparse
import html
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

PREIS = re.compile(r"(?:CHF|Fr\.|SFr\.)\s?\d{1,5}(?:[.,']\d{3})*(?:[.,]\d{2}|\.[–-])?", re.I)
ORT = re.compile(r"\b[1-9]\d{3} [A-ZÄÖÜ][A-Za-zäöüéèàâ.\-]+(?: [A-ZÄÖÜ][A-Za-zäöüéèàâ.\-]+){0,2}")
UMFELD = 50


def text_aus_html(seite: str) -> str:
    seite = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", seite)
    seite = re.sub(r"(?is)</?(p|div|br|li|tr|h[1-6]|td|th|section|article|footer|header)\b[^>]*>", "\n", seite)
    seite = re.sub(r"(?s)<[^>]+>", " ", seite)
    seite = html.unescape(seite).replace("\xa0", " ")
    seite = re.sub(r"[ \t\r\f\v]+", " ", seite)
    return re.sub(r"\s*\n\s*", "\n", seite).strip()


def auswerten(url: str, seite: str, muster: str | None, stellen_max: int = 3) -> dict:
    titel = re.search(r"(?is)<title[^>]*>(.*?)</title>", seite)
    text = text_aus_html(seite)
    orte, preise, stellen = [], [], []
    for m in ORT.finditer(text):
        wort = m.group(0).split(" ", 1)[1]
        if wort.isupper() or wort.split()[0] in {"Alle", "Rechte", "Copyright", "Uhr", "Jahre", "Stk", "Bewertungen"}:
            continue  # Jahreszahlen wie «2026 STATT» oder «2023 Alle Rechte» sind keine Orte
        if m.group(0) not in orte:
            orte.append(m.group(0))
    for m in PREIS.finditer(text):
        p = re.sub(r"\s+", " ", m.group(0))
        if p not in preise:
            preise.append(p)
    if muster:
        for m in re.finditer(muster, text, re.I):
            stellen.append("…" + text[max(0, m.start() - UMFELD):m.end() + UMFELD].replace("\n", " ") + "…")
            if len(stellen) >= stellen_max:
                break
    return {"url": url, "titel": text_aus_html(titel.group(1)).replace("\n", " ") if titel else "", "orte": orte[:4],
            "preise": preise[:8], "stellen": stellen}


def tabellenzeile(a: dict) -> str:
    felder = [a.get("quelle", ""), a["titel"][:60], ", ".join(a["orte"][:2]), ", ".join(a["preise"][:5]),
              " ".join(a["stellen"])[:300], a["url"]]
    return "| " + " | ".join(f.replace("|", "/").replace("\n", " ") for f in felder) + " |"


def exa_auslesen(antwort: dict) -> tuple[list[tuple[str, str, str]], float]:
    treffer = [(r["url"], r.get("title") or "", " ".join(r.get("highlights") or [])) for r in antwort.get("results", [])]
    return treffer, float(antwort.get("costDollars", {}).get("total", 0))


def exa_suche(frage: str, anzahl: int) -> tuple[list[tuple[str, str, str]], float]:
    schluessel = Path.home() / ".config/exa/key"
    if not schluessel.exists():
        return [], 0.0
    daten = json.dumps({"query": frage, "type": "auto", "numResults": anzahl, "userLocation": "CH",
                        "contents": {"highlights": {"numSentences": 2}}}).encode()
    req = urllib.request.Request("https://api.exa.ai/search", data=daten, headers={
        "x-api-key": schluessel.read_text().strip(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return exa_auslesen(json.load(r))


def ddgs_suche(frage: str, anzahl: int, region: str) -> list[tuple[str, str, str]]:
    from ddgs import DDGS
    try:
        return [(t["href"], t.get("title", ""), t.get("body", "")) for t in DDGS().text(frage, region=region, max_results=anzahl)]
    except Exception as e:  # ddgs wirft bei Blockierung oder leeren Treffern
        print(f"ddgs: {e}", file=sys.stderr)
        return []


def seite_holen(url: str) -> str:
    try:
        r = subprocess.run(["curl", "-sL", "--max-time", "20", "-A", "Mozilla/5.0 (X11; Linux x86_64) Chrome/130",
                            "--compressed", url], capture_output=True, timeout=25)
        return r.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return ""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-q", "--frage", action="append", required=True)
    p.add_argument("-r", "--region", default="ch-de")
    p.add_argument("-m", "--max", type=int, default=8)
    p.add_argument("--muster")
    p.add_argument("--stellen", type=int, default=3)
    p.add_argument("--ohne-exa", action="store_true")
    p.add_argument("--ohne-ddgs", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    # Windows-Konsole ohne PYTHONUTF8 kodiert cp1252; Zeichen ausserhalb davon dürfen die Ausgabe nicht abbrechen
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    gefunden: dict[str, dict] = {}
    kosten = 0.0
    for frage in a.frage:
        quellen = []
        if not a.ohne_ddgs:
            quellen.append(("ddgs", ddgs_suche(frage, a.max, a.region)))
        if not a.ohne_exa:
            t, k = exa_suche(frage, a.max)
            kosten += k
            quellen.append(("exa", t))
        for name, treffer in quellen:
            for url, titel, auszug in treffer:
                eintrag = gefunden.setdefault(url, {"quelle": set(), "titel": titel, "auszug": auszug})
                eintrag["quelle"].add(name)

    ergebnis = []
    for url, e in gefunden.items():
        seite = seite_holen(url)
        aus = auswerten(url, seite, a.muster, a.stellen) if seite else {"url": url, "titel": "", "orte": [], "preise": [], "stellen": []}
        aus["quelle"] = "+".join(sorted(e["quelle"]))
        if not aus["titel"]:
            aus["titel"] = e["titel"]
        if not seite:
            aus["stellen"] = ["(nicht ladbar) " + e["auszug"][:200]]
        ergebnis.append(aus)

    if a.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=1))
    else:
        print("| Quelle | Titel | Ort | Preise | Stellen | URL |\n|---|---|---|---|---|---|")
        for aus in ergebnis:
            print(tabellenzeile(aus))
    print(f"\n{len(ergebnis)} Seiten, Exa-Kosten {kosten:.3f} USD", file=sys.stderr)


if __name__ == "__main__":
    main()
