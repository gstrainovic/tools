#!/usr/bin/env python3
"""Fragen an Goran: eindeutige Nummern vergeben und prüfen, dass jede Antwort überall angekommen ist.

    fragen neu [ANZAHL]     nächste freie Nummer(n), eindeutig über alle Repos unter ~/projects
    fragen pruefen          offene Fragen mit Datum; VERALTET, wo eine Stelle noch auf eine beantwortete Frage wartet

Grund (Frage 307, 05.11.2026): Fragenummern begannen je Sitzung neu, eine Antwort wie «28b» kam darum nicht an
jeder Stelle an, die auf Frage 28 wartete. Ab START ist jede Nummer eindeutig; nur für diese meldet `pruefen`
veraltete Stellen. Ältere Nummern erscheinen nur in der Liste der offenen Fragen (mit «alt»).

Als offen gilt eine Zeile mit «**Frage N», «Frage N offen», «offen in Frage N» oder «bis Frage N». Als Antwort
gilt «Na» bis «Nh» nach «Entscheid», «Goran», «Antwort» oder «Freigabe» in derselben Zeile (nicht die Optionen und
die Empfehlung in der Frage selbst). Gelesen werden die von git verwalteten .md- und .py-Dateien jedes Repos,
ohne Tests (test_*) und Archive. Exit-Code 1, wenn etwas veraltet ist.
"""
import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

START = 310
WURZEL = Path.home() / "projects"
ZAEHLER = Path.home() / ".local" / "state" / "fragen" / "zaehler"

FRAGE = re.compile(r"Frage (\d+)\b")
OFFEN = re.compile(r"\*\*Frage (\d+)\b|Frage (\d+) offen|offen in Frage (\d+)\b|bis Frage (\d+)\b")
ANTWORT = re.compile(r"(?:Entscheid|Goran|Antwort|Freigabe)[^.;\n]{0,60}?(?<![\w.,'’])(\d+)[a-h](?![\wäöüß])")


@dataclass
class Stelle:
    repo: Path
    datei: Path
    zeile: int
    nummer: int
    text: str
    datum: str = ""
    alt: bool = False


@dataclass
class Bericht:
    offen: list = field(default_factory=list)
    veraltet: list = field(default_factory=list)


def repos(wurzel: Path) -> list[Path]:
    return sorted(p for p in wurzel.iterdir() if (p / ".git").exists())


def dateien(repo: Path) -> list[Path]:
    namen = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True).stdout.splitlines()
    return [repo / n for n in namen
            if n.endswith((".md", ".py")) and not Path(n).name.startswith("test_") and "archiv" not in n.lower()]


def zeilen(wurzel: Path):
    for repo in repos(wurzel):
        for datei in dateien(repo):
            try:
                text = datei.read_text(errors="replace")
            except OSError:
                continue
            for i, zeile in enumerate(text.splitlines(), 1):
                yield repo, datei, i, zeile


def antworten(zeile: str) -> set[int]:
    if "Empfehlung" in zeile:
        zeile = zeile.split("Empfehlung")[0]
    return {int(n) for n in ANTWORT.findall(zeile)}


def datum(repo: Path, datei: Path, zeile: int) -> str:
    aus = subprocess.run(["git", "-C", str(repo), "blame", "-L", f"{zeile},{zeile}", "--porcelain", "--",
                          str(datei.relative_to(repo))], capture_output=True, text=True).stdout
    zeit = re.search(r"^committer-time (\d+)", aus, re.M)
    if not zeit:
        return ""
    import datetime as dt
    return dt.datetime.fromtimestamp(int(zeit.group(1))).strftime("%Y-%m-%d")


def pruefen(wurzel: Path = WURZEL) -> Bericht:
    alle = list(zeilen(wurzel))
    beantwortet = set().union(*(antworten(z) for _, _, _, z in alle)) if alle else set()
    bericht, gesehen = Bericht(), set()
    for repo, datei, i, zeile in alle:
        for treffer in OFFEN.finditer(zeile):
            nummer = int(next(g for g in treffer.groups() if g))
            if (datei, nummer) in gesehen:
                continue
            gesehen.add((datei, nummer))
            stelle = Stelle(repo, datei, i, nummer, zeile.strip(), alt=nummer < START)
            if not stelle.alt and nummer in beantwortet:
                bericht.veraltet.append(stelle)
            else:
                stelle.datum = datum(repo, datei, i)
                bericht.offen.append(stelle)
    bericht.offen.sort(key=lambda s: (s.datum, s.nummer))
    return bericht


def hoechste(wurzel: Path) -> int:
    nummern = {START - 1}
    for _, _, _, zeile in zeilen(wurzel):
        nummern |= {int(n) for n in FRAGE.findall(zeile)} | antworten(zeile)
    # Unter 1900: Jahreszahlen («Frage 2020 im Forum») sind keine Fragenummern
    return max(n for n in nummern if n < 1900 and (n >= START or n == START - 1))


def neu(wurzel: Path = WURZEL, zaehler: Path = ZAEHLER, anzahl: int = 1) -> list[int]:
    zuletzt = int(zaehler.read_text()) if zaehler.exists() else 0
    erste = max(hoechste(wurzel), zuletzt) + 1
    nummern = list(range(erste, erste + anzahl))
    zaehler.parent.mkdir(parents=True, exist_ok=True)
    zaehler.write_text(str(nummern[-1]))
    return nummern


def ausgabe(bericht: Bericht) -> str:
    def ort(s: Stelle) -> str:
        return str(s.datei.relative_to(s.repo.parent))

    teile = []
    for s in bericht.veraltet:
        teile.append(f"VERALTET Frage {s.nummer} ist beantwortet, diese Stelle wartet noch: {ort(s)}:{s.zeile}\n"
                     f"    {s.text[:160]}")
    for s in bericht.offen:
        alt = " (alt, Nummer nicht eindeutig)" if s.alt else ""
        teile.append(f"offen seit {s.datum or '?'} Frage {s.nummer}{alt}: {ort(s)}:{s.zeile}\n    {s.text[:160]}")
    return "\n".join(teile) if teile else "Keine offenen Fragen."


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="befehl", required=True)
    p_neu = sub.add_parser("neu")
    p_neu.add_argument("anzahl", nargs="?", type=int, default=1)
    sub.add_parser("pruefen")
    args = p.parse_args(argv)
    if args.befehl == "neu":
        print(" ".join(map(str, neu(anzahl=args.anzahl))))
        return 0
    bericht = pruefen()
    print(ausgabe(bericht))
    return 1 if bericht.veraltet else 0


if __name__ == "__main__":
    sys.exit(main())
