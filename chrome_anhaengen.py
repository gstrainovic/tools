#!/usr/bin/env python3
"""playwright-cli an Gorans laufenden Chrome hängen, über die Playwright Extension ohne Freigabedialog, in einem
eigenen minimierten Chrome-Fenster («Arbeitsfenster»), damit die Browserarbeit Goran nicht stört.

Aufruf: chrome-anhaengen [--session gchrome]

Läuft die Session schon, bleibt sie (nie schliessen). Sonst:
1. Arbeitsfenster der Session bereitstellen: die gemerkte Fenster-ID (~/.config/playwright-extension/fenster-<session>)
   wird per GNOME-Erweiterung «Window Calls» (D-Bus org.gnome.Shell.Extensions.Windows) aktiviert; fehlt das Fenster,
   öffnet `google-chrome --new-window` ein neues Fenster in Gorans laufendem Chrome (gleiches Profil, gleiche Cookies).
2. `playwright-cli attach --extension=chrome` mit dem Token aus ~/.config/playwright-extension/token
   (PLAYWRIGHT_MCP_EXTENSION_TOKEN): Die Erweiterung legt den Session-Tab im zuletzt fokussierten Chrome-Fenster an,
   also im Arbeitsfenster, und fokussiert es.
3. Prüfen, dass der Session-Tab im Arbeitsfenster liegt (Titel des Tabs = Fenstertitel), dann das Fenster minimieren.
   Alle weiteren Tabs der Session entstehen in ihrer Tabgruppe, also im minimierten Fenster.
Ohne Window Calls (anderer Rechner, Erweiterung fehlt) nur anhängen wie früher. Die Session sieht nur die Tabs ihrer
eigenen Tabgruppe, Gorans übrige Tabs nicht. Einrichtung: Skill browser-wahl, «Gorans Chrome anhängen».
"""
import argparse
import ast
import json
import os
import subprocess
import sys
import time
from pathlib import Path

KONFIG = Path.home() / ".config" / "playwright-extension"
DBUS = ["gdbus", "call", "--session", "--dest", "org.gnome.Shell", "--object-path", "/org/gnome/Shell/Extensions/Windows",
        "--method"]


def session_laeuft(session: str) -> bool:
    r = subprocess.run(["playwright-cli", f"-s={session}", "tab-list"], capture_output=True, text=True)
    return r.returncode == 0 and "is not open" not in r.stdout + r.stderr


class Fenster:
    """GNOME-Fenster über die Erweiterung Window Calls; liste() ist None, wenn die Erweiterung fehlt."""

    def liste(self):
        r = subprocess.run([*DBUS, "org.gnome.Shell.Extensions.Windows.List"], capture_output=True, text=True)
        if r.returncode != 0:
            return None
        return json.loads(ast.literal_eval(r.stdout.strip())[0])

    def chrome_ids(self):
        liste = self.liste()
        return None if liste is None else {w["id"] for w in liste if w.get("wm_class") == "google-chrome"}

    def aktivieren(self, fenster_id: int):
        subprocess.run([*DBUS, "org.gnome.Shell.Extensions.Windows.Activate", str(fenster_id)], capture_output=True)

    def minimieren(self, fenster_id: int):
        subprocess.run([*DBUS, "org.gnome.Shell.Extensions.Windows.Minimize", str(fenster_id)], capture_output=True)

    def id_mit_titel(self, anfang: str):
        for w in self.liste() or []:
            if w.get("wm_class") == "google-chrome" and w.get("title", "").startswith(anfang):
                return w["id"]
        return None


def arbeitsfenster_bereitstellen(session: str, fenster: Fenster):
    """Gibt die Fenster-ID zurück (aktiviert oder neu geöffnet), None ohne Window Calls."""
    vorher = fenster.chrome_ids()
    if vorher is None:
        return None
    datei = KONFIG / f"fenster-{session}"
    if datei.is_file():
        try:
            bekannt = int(datei.read_text().strip())
        except ValueError:
            bekannt = None
        if bekannt in vorher:
            fenster.aktivieren(bekannt)
            time.sleep(1)
            return bekannt
    subprocess.Popen(["google-chrome", "--new-window", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    for _ in range(20):
        time.sleep(0.5)
        neu = (fenster.chrome_ids() or set()) - vorher
        if neu:
            fenster_id = sorted(neu)[0]
            datei.write_text(f"{fenster_id}\n")
            time.sleep(1)
            return fenster_id
    print("WARNUNG: kein neues Chrome-Fenster erschienen, hänge ohne Arbeitsfenster an", file=sys.stderr)
    return None


def tab_im_fenster(session: str, fenster: Fenster, fenster_id: int) -> bool:
    titel = f"Arbeitsfenster {session}"
    subprocess.run(["playwright-cli", f"-s={session}", "run-code",
                    f"async page => page.evaluate(() => {{ document.title = '{titel}'; return document.title; }})"],
                   capture_output=True, text=True)
    time.sleep(0.5)
    return fenster.id_mit_titel(titel) == fenster_id


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--session", default="gchrome")
    ap.add_argument("--zeigen", action="store_true", help="Arbeitsfenster hervorholen (Goran soll etwas klicken)")
    ap.add_argument("--verstecken", action="store_true", help="Arbeitsfenster wieder minimieren")
    args = ap.parse_args()
    s = args.session
    if args.zeigen or args.verstecken:
        fenster = Fenster()
        datei = KONFIG / f"fenster-{s}"
        bekannt = int(datei.read_text().strip()) if datei.is_file() else None
        if bekannt is None or bekannt not in (fenster.chrome_ids() or set()):
            print(f"FEHLER: kein Arbeitsfenster für Session {s} bekannt (erst chrome-anhaengen)", file=sys.stderr)
            return 1
        if args.zeigen:
            fenster.aktivieren(bekannt)
            print(f"Arbeitsfenster {bekannt} hervorgeholt")
        else:
            fenster.minimieren(bekannt)
            print(f"Arbeitsfenster {bekannt} minimiert")
        return 0
    if session_laeuft(s):
        print(f"Session {s} läuft schon")
        return 0
    datei = KONFIG / "token"
    if not datei.is_file():
        print(f"FEHLER: kein token in {datei} (Skill browser-wahl, «Gorans Chrome anhängen»)", file=sys.stderr)
        return 1
    fenster = Fenster()
    fenster_id = arbeitsfenster_bereitstellen(s, fenster)
    env = {**os.environ, "PLAYWRIGHT_MCP_EXTENSION_TOKEN": datei.read_text().strip()}
    r = subprocess.run(["playwright-cli", "attach", "--extension=chrome", f"--session={s}"],
                       env=env, capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not session_laeuft(s):
        print(f"FEHLER: Anhängen gescheitert\n{r.stdout[-500:]}{r.stderr[-500:]}", file=sys.stderr)
        return 1
    if fenster_id is None:
        print(f"Session {s} angehängt (ohne Window Calls kein eigenes Arbeitsfenster; Tabs liegen in Gorans Fenster)")
        return 0
    if tab_im_fenster(s, fenster, fenster_id):
        fenster.minimieren(fenster_id)
        print(f"Session {s} angehängt, Arbeitsfenster {fenster_id} minimiert")
    else:
        print(f"Session {s} angehängt, aber der Session-Tab liegt nicht im Arbeitsfenster {fenster_id} "
              f"(Goran hat wohl dazwischen geklickt); nichts minimiert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
