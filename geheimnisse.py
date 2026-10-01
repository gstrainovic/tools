#!/usr/bin/env python3
"""Dateien mit Zugangsdaten (.env, Schlüssel, Tokens) im Bitwarden Secrets Manager ablegen und von dort holen.

Jedes Geheimnis heisst wie der Pfad der Datei relativ zum Projektordner (dem Ordner über diesem Repo), Dateien
ausserhalb davon als «~/…» relativ zum Home-Verzeichnis; der Wert ist der Dateiinhalt. So legt `holen` auf einem
anderen Gerät jede Datei wieder an ihren Platz. Werte werden nie ausgegeben.

  geheimnisse hochladen <datei> [<datei> …]
  geheimnisse holen [--ueberschreiben]
  geheimnisse status

Braucht `bws` im Pfad, einmalig `bws config server-base https://vault.bitwarden.eu`, und das Zugriffstoken des
Geräts in ~/.config/bws/token (oder BWS_ACCESS_TOKEN). Einrichtung: README.md, «geheimnisse».
"""
import json
import os
import pathlib
import subprocess
import sys

PROJEKT = "strainovic"
BASIS = pathlib.Path(__file__).resolve().parents[1]
TOKEN = pathlib.Path.home() / ".config" / "bws" / "token"


def bws(args):
    umgebung = dict(os.environ)
    if "BWS_ACCESS_TOKEN" not in umgebung:
        umgebung["BWS_ACCESS_TOKEN"] = TOKEN.read_text(encoding="utf-8").strip()
    lauf = subprocess.run(["bws", *args], capture_output=True, text=True, env=umgebung)
    if lauf.returncode != 0:
        # Nie den Fehlertext von bws ausgeben: Er wiederholt Argumente, also auch Werte.
        raise SystemExit(f"bws {' '.join(args[:2])} scheiterte (Exit {lauf.returncode})")
    return lauf.stdout


class Tresor:
    def __init__(self, lauf=bws):
        self.lauf = lauf
        self._projekt = None

    def projekt(self):
        if self._projekt is None:
            treffer = [p["id"] for p in json.loads(self.lauf(["project", "list"])) if p["name"] == PROJEKT]
            if not treffer:
                raise SystemExit(f"Projekt «{PROJEKT}» fehlt oder das Gerätekonto hat keinen Zugriff darauf")
            self._projekt = treffer[0]
        return self._projekt

    def liste(self):
        """Name -> (ID, Wert) aller Geheimnisse des Projekts."""
        return {g["key"]: (g["id"], g["value"]) for g in json.loads(self.lauf(["secret", "list", self.projekt()]))}

    def hochladen(self, basis, dateien, heim=None):
        basis = pathlib.Path(basis).resolve()
        heim = pathlib.Path(heim).resolve() if heim else None
        paare = []
        for datei in dateien:
            pfad = pathlib.Path(datei).resolve()
            if basis in pfad.parents:
                name = pfad.relative_to(basis).as_posix()
            elif heim and heim in pfad.parents:
                name = "~/" + pfad.relative_to(heim).as_posix()
            else:
                raise ValueError(f"{datei} liegt weder unter {basis} noch im Home-Verzeichnis")
            paare.append((name, pfad.read_text(encoding="utf-8")))
        vorhanden = self.liste()
        ergebnis = []
        for name, wert in paare:
            if name not in vorhanden:
                # Werte können mit «-» beginnen (Schlüsseldateien): Optionen vor «--», Werte dahinter.
                self.lauf(["secret", "create", "--note", "Datei, Name ist der Pfad", "--", name, wert, self.projekt()])
                ergebnis.append((name, "neu"))
            elif vorhanden[name][1] != wert:
                self.lauf(["secret", "edit", f"--value={wert}", "--", vorhanden[name][0]])
                ergebnis.append((name, "geändert"))
            else:
                ergebnis.append((name, "gleich"))
        return ergebnis

    def _dateien(self, basis, heim=None):
        """(Name, Zielpfad, Wert) der Geheimnisse, deren Name ein Pfad in der Basis oder («~/…») im Home ist."""
        basis = pathlib.Path(basis).resolve()
        heim = pathlib.Path(heim).resolve() if heim else None
        for name, (_, wert) in sorted(self.liste().items()):
            if "/" not in name or name.startswith("/"):
                continue
            wurzel, rest = (heim, name[2:]) if name.startswith("~/") else (basis, name)
            if wurzel is None:
                continue
            ziel = (wurzel / rest).resolve()
            if wurzel in ziel.parents:
                yield name, ziel, wert

    def holen(self, basis, ueberschreiben=False, heim=None):
        """Schreibt fehlende Dateien; nennt nur, was geschrieben wurde oder abweicht."""
        ergebnis = []
        for name, ziel, wert in self._dateien(basis, heim):
            if ziel.is_file() and ziel.read_text(encoding="utf-8") == wert:
                ergebnis.append((name, "gleich"))
                continue
            if ziel.exists() and not ueberschreiben:
                ergebnis.append((name, "abweichend"))
                continue
            ziel.parent.mkdir(parents=True, exist_ok=True)
            deskriptor = os.open(ziel, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(deskriptor, "w", encoding="utf-8", newline="") as f:
                f.write(wert)
            if sys.platform != "win32":
                os.chmod(ziel, 0o600)
            ergebnis.append((name, "geschrieben"))
        return [e for e in ergebnis if e[1] != "gleich"]

    def status(self, basis, heim=None):
        ergebnis = []
        for name, ziel, wert in self._dateien(basis, heim):
            if not ziel.is_file():
                ergebnis.append((name, "fehlt lokal"))
            else:
                ergebnis.append((name, "gleich" if ziel.read_text(encoding="utf-8") == wert else "abweichend"))
        return ergebnis


def main(argv):
    befehl = argv[1] if len(argv) > 1 else ""
    tresor = Tresor()
    heim = pathlib.Path.home()
    if befehl == "hochladen" and len(argv) > 2:
        zeilen = tresor.hochladen(BASIS, argv[2:], heim=heim)
    elif befehl == "holen":
        zeilen = tresor.holen(BASIS, ueberschreiben="--ueberschreiben" in argv[2:], heim=heim)
    elif befehl == "status":
        zeilen = tresor.status(BASIS, heim=heim)
    else:
        print(__doc__)
        return 2
    for name, stand in zeilen:
        print(f"{stand:12} {name}")
    if not zeilen:
        print("nichts zu tun, alle Dateien stimmen mit dem Tresor überein")
    if any(stand == "abweichend" for _, stand in zeilen) and befehl == "holen":
        print("Abweichende Dateien blieben unverändert; mit --ueberschreiben gewinnt der Tresor.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
