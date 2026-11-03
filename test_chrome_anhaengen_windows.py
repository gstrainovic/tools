"""Tests für den Windows-Zweig von chrome_anhaengen.py (virtueller Desktop 2), ohne echten Chrome und ohne vd.exe:
python3 -m unittest test_chrome_anhaengen_windows.py"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import chrome_anhaengen as ca


class FalscherDesktop:
    """Fenster als {hwnd: desktop}; chrome_starten legt das nächste Fenster auf dem sichtbaren Desktop 0 an."""

    def __init__(self, fenster=None, desktops=2):
        self.fenster = dict(fenster or {})
        self.desktops = desktops
        self.titel = {}
        self.aufrufe = []
        self.naechstes = 900

    def bereitstellen(self):
        self.aufrufe.append("bereitstellen")

    def anzahl_desktops(self):
        return self.desktops

    def desktop_anlegen(self):
        self.desktops += 1
        self.aufrufe.append("new")

    def chrome_fenster(self):
        return set(self.fenster)

    def chrome_starten(self):
        self.aufrufe.append("chrome --new-window")
        self.fenster[self.naechstes] = 0
        self.titel[self.naechstes] = "about:blank - Google Chrome"
        self.naechstes += 1

    def verschieben(self, hwnd, desktop):
        self.aufrufe.append(f"move {hwnd} -> {desktop}")
        self.fenster[hwnd] = desktop

    def auf_desktop(self, hwnd, desktop):
        return self.fenster.get(hwnd) == desktop

    def schliessen(self, hwnd):
        self.aufrufe.append(f"close {hwnd}")
        self.fenster.pop(hwnd, None)

    def fenstertitel(self, hwnd):
        return self.titel.get(hwnd, "")


class ChromeAnhaengenWindows(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.konfig = self.tmp / "playwright-extension"
        self.konfig.mkdir()
        (self.konfig / "token").write_text("geheim123\n")
        self.cli_aufrufe = []
        self.offen = False
        self.tab_fenster = None  # hwnd, in dem die Erweiterung den Session-Tab anlegt
        self.desktop = FalscherDesktop({2: 0})  # Gorans Fenster auf Desktop 1
        patches = [mock.patch.object(ca, "KONFIG", self.konfig), mock.patch.object(ca, "cli_lauf", self.cli),
                   mock.patch.object(ca, "WindowsDesktop", lambda: self.desktop)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def cli(self, args, env=None, timeout=None):
        zusatz = ""
        if env and "PLAYWRIGHT_MCP_EXTENSION_TOKEN" in env:
            zusatz = f" TOKEN={env['PLAYWRIGHT_MCP_EXTENSION_TOKEN']} EXE={env.get('PLAYWRIGHT_MCP_EXECUTABLE_PATH', '')}"
        self.cli_aufrufe.append(" ".join(args) + zusatz)
        if args[0] == "tab-list" or args[1:2] == ["tab-list"]:
            return mock.Mock(returncode=0 if self.offen else 1,
                             stdout="- 0: (current) [x](about:blank)" if self.offen else "The browser 'gchrome' is not open", stderr="")
        if args[0] == "attach":
            self.offen = True
            # Die Erweiterung legt den Session-Tab im zuletzt geöffneten Fenster an
            self.tab_fenster = self.tab_fenster or max(self.desktop.fenster)
            return mock.Mock(returncode=0, stdout="### Session created", stderr="")
        if "run-code" in args:
            import re
            titel = re.search(r"document.title = '([^']+)'", args[-1]).group(1)
            if self.tab_fenster in self.desktop.fenster:
                self.desktop.titel[self.tab_fenster] = titel + " - Google Chrome"
            return mock.Mock(returncode=0, stdout="ok", stderr="")
        return mock.Mock(returncode=0, stdout="", stderr="")

    def lauf(self, *args):
        with mock.patch("sys.argv", ["chrome_anhaengen.py", *args]), mock.patch("sys.stdout") as out, mock.patch("sys.stderr") as err:
            rc = ca.main_windows()
        text = "".join(str(c.args[0]) for c in out.write.call_args_list)
        fehler = "".join(str(c.args[0]) for c in err.write.call_args_list)
        return rc, text, fehler

    def test_neues_fenster_wird_sofort_auf_desktop_2_verschoben_und_dann_angehaengt(self):
        rc, text, fehler = self.lauf()
        self.assertEqual(rc, 0, fehler)
        a = self.desktop.aufrufe
        self.assertEqual(a, ["bereitstellen", "chrome --new-window", "move 900 -> 1"])
        self.assertLess(2, len(self.cli_aufrufe))
        attach = [z for z in self.cli_aufrufe if z.startswith("attach")]
        self.assertEqual(len(attach), 1)
        self.assertTrue(attach[0].startswith("attach --extension=chrome --session=gchrome TOKEN=geheim123"), attach[0])
        self.assertEqual(self.desktop.fenster[900], 1, "Session-Fenster auf Desktop 2")
        self.assertEqual(self.desktop.fenster[2], 0, "Gorans Fenster unberührt")
        self.assertEqual("900", (self.konfig / "fenster-gchrome").read_text().strip())
        self.assertIn("Desktop 2", text)

    def test_attach_setzt_den_chrome_pfad_fuer_playwright(self):
        # Ohne PLAYWRIGHT_MCP_EXECUTABLE_PATH findet playwright-cli den scoop-Chrome nicht («executable not found»).
        self.lauf()
        attach = next(z for z in self.cli_aufrufe if z.startswith("attach"))
        self.assertIn(f"EXE={ca.CHROME_EXE}", attach)

    def test_desktop_2_wird_angelegt_wenn_er_fehlt(self):
        self.desktop.desktops = 1
        rc, text, fehler = self.lauf()
        self.assertEqual(rc, 0, fehler)
        self.assertIn("new", self.desktop.aufrufe)
        self.assertEqual(self.desktop.fenster[900], 1)

    def test_altes_session_fenster_wird_vorher_geschlossen(self):
        self.desktop.fenster[77] = 1
        (self.konfig / "fenster-gchrome").write_text("77\n")
        rc, text, fehler = self.lauf()
        self.assertEqual(rc, 0, fehler)
        self.assertNotIn(77, self.desktop.fenster)
        self.assertIn("close 77", self.desktop.aufrufe)
        self.assertLess(self.desktop.aufrufe.index("close 77"), self.desktop.aufrufe.index("chrome --new-window"))
        self.assertEqual("900", (self.konfig / "fenster-gchrome").read_text().strip())

    def test_laufende_session_bleibt_und_ihr_fenster_kommt_zurueck_auf_desktop_2(self):
        self.offen = True
        self.desktop.fenster[77] = 0  # nach --zeigen liegen geblieben
        (self.konfig / "fenster-gchrome").write_text("77\n")
        rc, text, fehler = self.lauf()
        self.assertEqual(rc, 0, fehler)
        self.assertFalse(any(z.startswith("attach") for z in self.cli_aufrufe))
        self.assertNotIn("chrome --new-window", self.desktop.aufrufe)
        self.assertEqual(self.desktop.fenster[77], 1)
        self.assertIn("läuft schon", text)

    def test_tab_in_fremdem_fenster_wird_gemeldet(self):
        self.tab_fenster = 2  # Goran hat dazwischen geklickt: Tab in seinem Fenster
        with mock.patch.object(ca, "WARTEN_TITEL_S", 0.01):
            rc, text, fehler = self.lauf()
        self.assertEqual(rc, 0, fehler)
        self.assertIn("nicht im Arbeitsfenster", text)

    def test_fenstertitel_kommt_erst_spaeter_und_wird_trotzdem_erkannt(self):
        # Echter Lauf 03.11.2026: der Fenstertitel folgte dem Tab erst nach mehr als 0,5 s.
        echt = self.desktop.fenstertitel
        zaehler = {"n": 0}

        def spaet(hwnd):
            zaehler["n"] += 1
            return echt(hwnd) if zaehler["n"] > 3 else "about:blank - Google Chrome"

        self.desktop.fenstertitel = spaet
        rc, text, fehler = self.lauf()
        self.assertEqual(rc, 0, fehler)
        self.assertNotIn("nicht im Arbeitsfenster", text)
        self.assertIn("Desktop 2", text)

    def test_zeigen_holt_das_fenster_auf_desktop_1_und_verstecken_zurueck(self):
        self.desktop.fenster[77] = 1
        (self.konfig / "fenster-gchrome").write_text("77\n")
        rc, text, fehler = self.lauf("--zeigen")
        self.assertEqual(rc, 0, fehler)
        self.assertEqual(self.desktop.fenster[77], 0)
        self.assertFalse(self.offen, "zeigen hängt nicht an")
        rc, text, fehler = self.lauf("--verstecken")
        self.assertEqual(rc, 0, fehler)
        self.assertEqual(self.desktop.fenster[77], 1)

    def test_zeigen_ohne_bekanntes_fenster_meldet_es(self):
        rc, text, fehler = self.lauf("--zeigen")
        self.assertNotEqual(rc, 0)
        self.assertIn("kein Arbeitsfenster", fehler)

    def test_ohne_token_klare_meldung(self):
        (self.konfig / "token").unlink()
        rc, text, fehler = self.lauf()
        self.assertNotEqual(rc, 0)
        self.assertIn("token", fehler)
        self.assertNotIn("chrome --new-window", self.desktop.aufrufe)

    def test_kein_neues_fenster_erschienen_bricht_ab(self):
        self.desktop.chrome_starten = lambda: self.desktop.aufrufe.append("chrome --new-window")
        with mock.patch.object(ca, "WARTEN_FENSTER_S", 0.01):
            rc, text, fehler = self.lauf()
        self.assertNotEqual(rc, 0)
        self.assertIn("kein neues Chrome-Fenster", fehler)
        self.assertFalse(any(z.startswith("attach") for z in self.cli_aufrufe), "ohne Fenster kein Anhängen")

    def test_fenster_nicht_verschiebbar_bricht_ab_und_schliesst_es(self):
        self.desktop.verschieben = lambda hwnd, d: self.desktop.aufrufe.append(f"move {hwnd} -> {d}")
        rc, text, fehler = self.lauf()
        self.assertNotEqual(rc, 0)
        self.assertIn("Desktop 2", fehler)
        self.assertIn("close 900", self.desktop.aufrufe, "Fenster auf Desktop 1 nicht stehen lassen")
        self.assertFalse(any(z.startswith("attach") for z in self.cli_aufrufe))


if __name__ == "__main__":
    unittest.main()
