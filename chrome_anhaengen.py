#!/usr/bin/env python3
"""playwright-cli an Gorans laufenden Chrome hängen, über die Playwright Extension ohne Freigabedialog, in einem
eigenen Chrome-Fenster («Arbeitsfenster») auf Arbeitsfläche 2, damit die Browserarbeit Goran nicht stört.

Aufruf: chrome-anhaengen [--session gchrome] [--zeigen | --verstecken]

Läuft die Session schon, bleibt sie (nie schliessen); ihr Arbeitsfenster geht wieder auf Arbeitsfläche 2. Sonst:
1. Arbeitsfenster der Session bereitstellen: die gemerkte Fenster-ID (~/.config/playwright-extension/fenster-<session>)
   wird per GNOME-Erweiterung «Window Calls» (D-Bus org.gnome.Shell.Extensions.Windows) auf Gorans Arbeitsfläche
   geholt und aktiviert (aktivieren auf Arbeitsfläche 2 würde seine Ansicht dorthin wechseln); fehlt das Fenster,
   öffnet `google-chrome --new-window` ein neues Fenster in Gorans laufendem Chrome (gleiches Profil, gleiche Cookies).
2. `playwright-cli attach --extension=chrome` mit dem Token aus ~/.config/playwright-extension/token
   (PLAYWRIGHT_MCP_EXTENSION_TOKEN): Die Erweiterung legt den Session-Tab im zuletzt fokussierten Chrome-Fenster an,
   also im Arbeitsfenster, und fokussiert es.
3. Prüfen, dass der Session-Tab im Arbeitsfenster liegt (Titel des Tabs = Fenstertitel), dann das Fenster auf
   Arbeitsfläche 2 schieben (MoveToWorkspace); bei fester Zahl Arbeitsflächen unter zwei stellt das Skript per dconf
   zwei ein. Alle weiteren Tabs der Session entstehen in ihrer Tabgruppe, also auf Arbeitsfläche 2.
   `--zeigen` holt das Fenster auf Gorans Arbeitsfläche, `--verstecken` schickt es zurück.
4. Hat Goran kein eigenes Chrome-Fenster, eines öffnen (sonst landen Links aus anderen Apps im Arbeitsfenster).
Ohne Window Calls (anderer Rechner, Erweiterung fehlt) nur anhängen wie früher. Die Session sieht nur die Tabs ihrer
eigenen Tabgruppe, Gorans übrige Tabs nicht. Einrichtung: Skill browser-wahl, «Gorans Chrome anhängen».

Windows (`python3 chrome_anhaengen.py`, Goran, Entscheid vom 03.11.2026): Jeder Lauf öffnet ein neues Fenster in
Gorans laufendem Chrome (`chrome.exe --new-window about:blank`, erscheint kurz auf dem sichtbaren Desktop, einen
Startparameter für einen anderen Desktop gibt es nicht), verschiebt es sofort auf den virtuellen Desktop 2 (legt ihn
an, falls er fehlt) und hängt erst dann an; ein früheres Session-Fenster wird vorher geschlossen. Verschieben per
MScholtes/VirtualDesktop (Quelle `vendor/virtualdesktop/`, beim ersten Aufruf mit dem csc aus .NET Framework nach
%LOCALAPPDATA%\\virtualdesktop\\vd.exe gebaut). `--zeigen` holt das Fenster auf Desktop 1, `--verstecken` schickt es
zurück; auch ein Aufruf bei laufender Session schickt es zurück.
"""
import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

KONFIG = Path.home() / ".config" / "playwright-extension"
DBUS = ["gdbus", "call", "--session", "--dest", "org.gnome.Shell", "--object-path", "/org/gnome/Shell/Extensions/Windows",
        "--method"]

# Windows: scoop-Chrome (playwright-cli sucht nur unter Program Files und LOCALAPPDATA), VirtualDesktop-Werkzeug
CHROME_EXE = r"C:\Users\g.strainovic\scoop\apps\googlechrome\current\chrome.exe"
VD_EXE = Path(os.environ.get("LOCALAPPDATA", ".")) / "virtualdesktop" / "vd.exe"
VD_QUELLE = Path(__file__).resolve().with_name("vendor") / "virtualdesktop" / "VirtualDesktop11-24H2.cs"
CSC = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
ARBEITSDESKTOP = 1  # nullbasiert: «Desktop 2»
WARTEN_FENSTER_S = 10
WARTEN_TITEL_S = 5


def cli_lauf(args, env=None, timeout=None):
    """playwright-cli aufrufen; unter Windows heisst das Programm playwright-cli.cmd, darum über shutil.which."""
    cmd = shutil.which("playwright-cli") or "playwright-cli"
    return subprocess.run([cmd, *args], env=env, capture_output=True, text=True, timeout=timeout)


def session_laeuft(session: str) -> bool:
    r = cli_lauf([f"-s={session}", "tab-list"])
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

    def verschieben(self, fenster_id: int, arbeitsflaeche: int):
        """Fenster auf eine Arbeitsfläche (nullbasiert) schieben; Mutter tut nichts, wenn es sie nicht gibt."""
        subprocess.run([*DBUS, "org.gnome.Shell.Extensions.Windows.MoveToWorkspace", str(fenster_id),
                        str(arbeitsflaeche)], capture_output=True)

    def verstecken(self, fenster_id: int):
        arbeitsflaechen_sichern()
        self.verschieben(fenster_id, ARBEITSDESKTOP)

    def herholen(self, fenster_id: int):
        """Erst auf Gorans Arbeitsfläche holen, dann aktivieren: Aktivieren auf Arbeitsfläche 2 würde seine Ansicht
        dorthin wechseln."""
        self.verschieben(fenster_id, 0)
        self.aktivieren(fenster_id)

    def id_mit_titel(self, anfang: str):
        for w in self.liste() or []:
            if w.get("wm_class") == "google-chrome" and w.get("title", "").startswith(anfang):
                return w["id"]
        return None


def arbeitsflaechen_sichern():
    """Bei fester Zahl Arbeitsflächen mindestens zwei einstellen. Über dconf, nicht gsettings: das gsettings aus
    Linuxbrew steht im PATH vor /usr/bin und hat kein dconf-Backend, liest und schreibt also ins Leere."""
    if not shutil.which("dconf"):
        return
    def lesen(schluessel):
        return subprocess.run(["dconf", "read", schluessel], capture_output=True, text=True).stdout.strip()
    if lesen("/org/gnome/mutter/dynamic-workspaces") == "true":
        return
    anzahl = lesen("/org/gnome/desktop/wm/preferences/num-workspaces")
    if anzahl.isdigit() and int(anzahl) >= ARBEITSDESKTOP + 1:
        return
    subprocess.run(["dconf", "write", "/org/gnome/desktop/wm/preferences/num-workspaces", str(ARBEITSDESKTOP + 1)],
                   capture_output=True)
    time.sleep(0.5)


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
            fenster.herholen(bekannt)
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


def eigenes_fenster_sichern(fenster: Fenster, arbeits_id: int):
    """Ist das Arbeitsfenster das einzige Chrome-Fenster, öffnet Chrome Links aus anderen Apps darin, also unsichtbar,
    und ein Klick auf Chrome im Dock holt es hervor. Darum Goran ein eigenes Fenster öffnen; der Fokus geht zurück
    an das Fenster, in dem er gerade arbeitet."""
    liste = fenster.liste() or []
    if any(w.get("wm_class") == "google-chrome" and w["id"] != arbeits_id for w in liste):
        return
    fokus = next((w["id"] for w in liste if w.get("focus")), None)
    vorher = {w["id"] for w in liste}
    subprocess.Popen(["google-chrome", "--new-window"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    for _ in range(20):
        time.sleep(0.5)
        if {w["id"] for w in fenster.liste() or []} - vorher:
            break
    if fokus is not None:
        fenster.aktivieren(fokus)
    print("eigenes Chrome-Fenster für Goran geöffnet (Links aus anderen Apps landen dort)")


def titel_setzen(session: str) -> str:
    """Setzt im Session-Tab einen eindeutigen Titel; der Fenstertitel folgt dem aktiven Tab."""
    titel = f"Arbeitsfenster {session}"
    cli_lauf([f"-s={session}", "run-code",
              f"async page => page.evaluate(() => {{ document.title = '{titel}'; return document.title; }})"])
    time.sleep(0.5)
    return titel


def tab_im_fenster(session: str, fenster: Fenster, fenster_id: int) -> bool:
    return fenster.id_mit_titel(titel_setzen(session)) == fenster_id


class WindowsDesktop:
    """Chrome-Fenster und virtuelle Desktops unter Windows: Fenster per Win32 (EnumWindows), Desktops per vd.exe."""

    def vd(self, *args):
        return subprocess.run([str(VD_EXE), *args], capture_output=True, text=True)

    def bereitstellen(self):
        if VD_EXE.is_file():
            return
        if not Path(CSC).is_file() or not VD_QUELLE.is_file():
            raise RuntimeError(f"vd.exe fehlt und lässt sich nicht bauen: {CSC} oder {VD_QUELLE} fehlt")
        VD_EXE.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([CSC, "/nologo", f"/out:{VD_EXE}", str(VD_QUELLE)], capture_output=True, text=True)
        if r.returncode != 0 or not VD_EXE.is_file():
            raise RuntimeError(f"vd.exe bauen gescheitert:\n{r.stdout[-800:]}{r.stderr[-800:]}")

    def anzahl_desktops(self) -> int:
        zahlen = [int(w) for w in self.vd("/Count").stdout.split() if w.isdigit()]
        return zahlen[-1] if zahlen else 1

    def desktop_anlegen(self):
        self.vd("/New")

    def chrome_fenster(self) -> set:
        """Sichtbare Hauptfenster von chrome.exe (Klasse Chrome_WidgetWin_1 mit Titel) als Handles."""
        import ctypes
        import ctypes.wintypes as w
        u, k = ctypes.windll.user32, ctypes.windll.kernel32
        handles = set()

        @ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        def cb(h, _):
            if not u.IsWindowVisible(h) or not u.GetWindowTextLengthW(h):
                return True
            klasse = ctypes.create_unicode_buffer(64)
            u.GetClassNameW(h, klasse, 64)
            if klasse.value != "Chrome_WidgetWin_1":
                return True
            pid = w.DWORD()
            u.GetWindowThreadProcessId(h, ctypes.byref(pid))
            p = k.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not p:
                return True
            pfad = ctypes.create_unicode_buffer(1024)
            n = w.DWORD(1024)
            ok = k.QueryFullProcessImageNameW(p, 0, pfad, ctypes.byref(n))
            k.CloseHandle(p)
            if ok and pfad.value.lower().endswith("\\chrome.exe"):
                handles.add(int(h))
            return True

        u.EnumWindows(cb, 0)
        return handles

    def chrome_starten(self):
        subprocess.Popen([CHROME_EXE, "--new-window", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def verschieben(self, hwnd: int, desktop: int):
        self.vd(f"/GetDesktop:{desktop}", f"/MoveWindowHandle:{hwnd}")

    def auf_desktop(self, hwnd: int, desktop: int) -> bool:
        return " is on desktop" in self.vd(f"/GetDesktop:{desktop}", f"/IsWindowHandleOnDesktop:{hwnd}").stdout

    def schliessen(self, hwnd: int):
        import ctypes
        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        for _ in range(20):
            if hwnd not in self.chrome_fenster():
                return
            time.sleep(0.25)

    def fenstertitel(self, hwnd: int) -> str:
        import ctypes
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
        return buf.value


def main_windows() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--session", default="gchrome")
    ap.add_argument("--zeigen", action="store_true", help="Arbeitsfenster auf Desktop 1 holen (Goran soll etwas klicken)")
    ap.add_argument("--verstecken", action="store_true", help="Arbeitsfenster zurück auf Desktop 2")
    args = ap.parse_args()
    s = args.session
    desktop = WindowsDesktop()
    datei = KONFIG / f"fenster-{s}"
    inhalt = datei.read_text().strip() if datei.is_file() else ""
    bekannt = int(inhalt) if inhalt.isdigit() else None
    vorhanden = desktop.chrome_fenster()
    if args.zeigen or args.verstecken:
        if bekannt is None or bekannt not in vorhanden:
            print(f"FEHLER: kein Arbeitsfenster für Session {s} bekannt (erst chrome-anhaengen)", file=sys.stderr)
            return 1
        desktop.bereitstellen()
        ziel = 0 if args.zeigen else ARBEITSDESKTOP
        desktop.verschieben(bekannt, ziel)
        print(f"Arbeitsfenster {bekannt} auf Desktop {ziel + 1} verschoben")
        return 0
    if session_laeuft(s):
        if bekannt in vorhanden and not desktop.auf_desktop(bekannt, ARBEITSDESKTOP):
            desktop.bereitstellen()
            desktop.verschieben(bekannt, ARBEITSDESKTOP)
            print(f"Session {s} läuft schon, Arbeitsfenster {bekannt} zurück auf Desktop {ARBEITSDESKTOP + 1}")
        else:
            print(f"Session {s} läuft schon")
        return 0
    token = KONFIG / "token"
    if not token.is_file():
        print(f"FEHLER: kein token in {token} (Skill browser-wahl, «Gorans Chrome anhängen»)", file=sys.stderr)
        return 1
    desktop.bereitstellen()
    if desktop.anzahl_desktops() < ARBEITSDESKTOP + 1:
        desktop.desktop_anlegen()
    if bekannt in vorhanden:
        desktop.schliessen(bekannt)
        vorhanden = desktop.chrome_fenster()
    desktop.chrome_starten()
    hwnd = None
    frist = time.monotonic() + WARTEN_FENSTER_S
    while True:
        neu = desktop.chrome_fenster() - vorhanden
        if neu:
            hwnd = min(neu)
            break
        if time.monotonic() > frist:
            break
        time.sleep(0.2)
    if hwnd is None:
        print("FEHLER: kein neues Chrome-Fenster erschienen, nicht angehängt", file=sys.stderr)
        return 1
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(f"{hwnd}\n")
    desktop.verschieben(hwnd, ARBEITSDESKTOP)
    if not desktop.auf_desktop(hwnd, ARBEITSDESKTOP):
        desktop.schliessen(hwnd)
        print(f"FEHLER: Fenster {hwnd} liess sich nicht auf Desktop {ARBEITSDESKTOP + 1} verschieben; geschlossen, "
              "nicht angehängt", file=sys.stderr)
        return 1
    env = {**os.environ, "PLAYWRIGHT_MCP_EXTENSION_TOKEN": token.read_text().strip(),
           "PLAYWRIGHT_MCP_EXECUTABLE_PATH": CHROME_EXE}
    r = cli_lauf(["attach", "--extension=chrome", f"--session={s}"], env=env, timeout=120)
    if r.returncode != 0 or not session_laeuft(s):
        print(f"FEHLER: Anhängen gescheitert\n{r.stdout[-500:]}{r.stderr[-500:]}", file=sys.stderr)
        return 1
    titel = titel_setzen(s)
    frist = time.monotonic() + WARTEN_TITEL_S  # der Fenstertitel folgt dem Tab erst nach einigen Sekunden
    while not desktop.fenstertitel(hwnd).startswith(titel) and time.monotonic() < frist:
        time.sleep(0.3)
    if desktop.fenstertitel(hwnd).startswith(titel):
        print(f"Session {s} angehängt, Arbeitsfenster {hwnd} auf Desktop {ARBEITSDESKTOP + 1}")
    else:
        print(f"Session {s} angehängt, aber der Session-Tab liegt nicht im Arbeitsfenster {hwnd} auf Desktop "
              f"{ARBEITSDESKTOP + 1} (Goran hat wohl dazwischen geklickt)")
    return 0


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
            fenster.herholen(bekannt)
            print(f"Arbeitsfenster {bekannt} hervorgeholt")
        else:
            fenster.verstecken(bekannt)
            print(f"Arbeitsfenster {bekannt} auf Arbeitsfläche {ARBEITSDESKTOP + 1}")
        return 0
    if session_laeuft(s):
        # Ein früherer Lauf oder --zeigen kann das Arbeitsfenster offen gelassen haben: wieder verstecken.
        fenster = Fenster()
        datei = KONFIG / f"fenster-{s}"
        bekannt = int(datei.read_text().strip()) if datei.is_file() else None
        if bekannt is not None and bekannt in (fenster.chrome_ids() or set()):
            fenster.verstecken(bekannt)
            print(f"Session {s} läuft schon, Arbeitsfenster {bekannt} auf Arbeitsfläche {ARBEITSDESKTOP + 1}")
            eigenes_fenster_sichern(fenster, bekannt)
        else:
            print(f"Session {s} läuft schon")
        return 0
    datei = KONFIG / "token"
    if not datei.is_file():
        print(f"FEHLER: kein token in {datei} (Skill browser-wahl, «Gorans Chrome anhängen»)", file=sys.stderr)
        return 1
    fenster = Fenster()
    fenster_id = arbeitsfenster_bereitstellen(s, fenster)
    env = {**os.environ, "PLAYWRIGHT_MCP_EXTENSION_TOKEN": datei.read_text().strip()}
    r = cli_lauf(["attach", "--extension=chrome", f"--session={s}"], env=env, timeout=120)
    if r.returncode != 0 or not session_laeuft(s):
        print(f"FEHLER: Anhängen gescheitert\n{r.stdout[-500:]}{r.stderr[-500:]}", file=sys.stderr)
        return 1
    if fenster_id is None:
        print(f"Session {s} angehängt (ohne Window Calls kein eigenes Arbeitsfenster; Tabs liegen in Gorans Fenster)")
        return 0
    if tab_im_fenster(s, fenster, fenster_id):
        fenster.verstecken(fenster_id)
        print(f"Session {s} angehängt, Arbeitsfenster {fenster_id} auf Arbeitsfläche {ARBEITSDESKTOP + 1}")
        eigenes_fenster_sichern(fenster, fenster_id)
    else:
        print(f"Session {s} angehängt, aber der Session-Tab liegt nicht im Arbeitsfenster {fenster_id} "
              f"(Goran hat wohl dazwischen geklickt); nichts versteckt")
    return 0


if __name__ == "__main__":
    sys.exit(main_windows() if sys.platform == "win32" else main())
