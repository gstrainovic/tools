"""Tests für chrome_anhaengen.py mit falschen playwright-cli, gdbus und google-chrome im PATH:
python3 -m unittest test_chrome_anhaengen.py"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SKRIPT = Path(__file__).with_name("chrome_anhaengen.py")

FALSCH_CLI = """#!/bin/bash
echo "$* TOKEN=${PLAYWRIGHT_MCP_EXTENSION_TOKEN:-}" >> "$AUFRUFE"
if [[ "$*" == *tab-list* ]]; then
  [[ -f "$OFFEN" ]] && { echo "- 0: (current) [Seite](https://example.com)"; exit 0; }
  echo "The browser 'gchrome' is not open, please run open first"; exit 1
fi
if [[ "$*" == attach* ]]; then
  touch "$OFFEN"
  # Die Erweiterung legt den Session-Tab im zuletzt fokussierten Chrome-Fenster an.
  python3 - "$FENSTER" <<'EOF'
import json, sys
p = sys.argv[1]; f = json.load(open(p))
for w in f:
    if w["wm_class"] == "google-chrome" and w["focus"]:
        w["title"] = "Session-Tab - Google Chrome"
json.dump(f, open(p, "w"))
EOF
  echo "- Page URL: about:blank"
fi
if [[ "$*" == *run-code* ]]; then
  # document.title = 'Arbeitsfenster <session>' im Session-Tab: Fenstertitel folgt dem Tab.
  python3 - "$FENSTER" "$*" <<'EOF'
import json, re, sys
p = sys.argv[1]; f = json.load(open(p))
titel = re.search(r"document.title = '([^']+)'", sys.argv[2]).group(1)
for w in f:
    if w["title"].startswith("Session-Tab"):
        w["title"] = titel + " - Google Chrome"
json.dump(f, open(p, "w"))
EOF
  echo "### Result"; echo "ok"
fi
"""

FALSCH_GDBUS = """#!/bin/bash
echo "gdbus $*" >> "$AUFRUFE"
[[ -f "$OHNE_WINDOW_CALLS" ]] && { echo "Fehler: GDBus.Error:org.freedesktop.DBus.Error.UnknownMethod: Das Objekt existiert nicht" >&2; exit 1; }
methode="${@: -1}"; [[ "$*" == *Minimize* || "$*" == *Activate* ]] && methode="${@: -2:1}"
python3 - "$FENSTER" "$*" <<'EOF'
import json, sys
p = sys.argv[1]; f = json.load(open(p)); args = sys.argv[2].split()
if "Windows.List" in args[-1]:
    print("('" + json.dumps(f) + "',)")
elif "Windows.Minimize" in sys.argv[2]:
    for w in f:
        if w["id"] == int(args[-1]): w["minimized"] = True; w["focus"] = False
    print("()")
elif "Windows.Activate" in sys.argv[2]:
    for w in f:
        w["focus"] = w["id"] == int(args[-1])
        if w["focus"]: w["minimized"] = False
    print("()")
json.dump(f, open(p, "w"))
EOF
"""

FALSCH_CHROME = """#!/bin/bash
echo "google-chrome $*" >> "$AUFRUFE"
python3 - "$FENSTER" <<'EOF'
import json, sys
p = sys.argv[1]; f = json.load(open(p))
for w in f: w["focus"] = False
f.append({"id": 900, "wm_class": "google-chrome", "title": "about:blank - Google Chrome", "focus": True, "minimized": False})
json.dump(f, open(p, "w"))
EOF
"""


def fenster(id_, wm_class, titel, fokus=False, minimiert=False):
    return {"id": id_, "wm_class": wm_class, "title": titel, "focus": fokus, "minimized": minimiert}


class ChromeAnhaengen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "bin").mkdir()
        for name, inhalt in [("playwright-cli", FALSCH_CLI), ("gdbus", FALSCH_GDBUS), ("google-chrome", FALSCH_CHROME)]:
            p = self.tmp / "bin" / name
            p.write_text(inhalt)
            p.chmod(0o755)
        self.konfig = self.tmp / ".config" / "playwright-extension"
        self.konfig.mkdir(parents=True)
        (self.konfig / "token").write_text("geheim123\n")
        self.fenster_datei = self.tmp / "fenster.json"
        self.setze_fenster([fenster(1, "org.gnome.Ptyxis", "Terminal", fokus=True),
                            fenster(2, "google-chrome", "Gorans Seite - Google Chrome")])
        self.env = {**os.environ, "PATH": f"{self.tmp / 'bin'}:{os.environ['PATH']}", "HOME": str(self.tmp),
                    "AUFRUFE": str(self.tmp / "aufrufe"), "OFFEN": str(self.tmp / "offen"),
                    "FENSTER": str(self.fenster_datei), "OHNE_WINDOW_CALLS": str(self.tmp / "ohne-wc")}

    def setze_fenster(self, liste):
        self.fenster_datei.write_text(json.dumps(liste))

    def fenster(self):
        return {w["id"]: w for w in json.loads(self.fenster_datei.read_text())}

    def lauf(self, *args):
        return subprocess.run([str(SKRIPT), *args], env=self.env, capture_output=True, text=True, timeout=60)

    def aufrufe(self):
        return (self.tmp / "aufrufe").read_text().splitlines()

    def test_haengt_ueber_erweiterung_mit_token_an(self):
        r = self.lauf()
        self.assertEqual(r.returncode, 0, r.stderr)
        attach = [z for z in self.aufrufe() if z.startswith("attach")]
        self.assertEqual(attach, ["attach --extension=chrome --session=gchrome TOKEN=geheim123"])
        self.assertIn("angehängt", r.stdout)

    def test_laufende_session_bleibt_unberuehrt(self):
        (self.tmp / "offen").touch()
        r = self.lauf()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(any(z.startswith("attach") or z.startswith("google-chrome") for z in self.aufrufe()))
        self.assertIn("läuft schon", r.stdout)

    def test_andere_session(self):
        self.lauf("--session", "test")
        self.assertIn("attach --extension=chrome --session=test TOKEN=geheim123", self.aufrufe())

    def test_ohne_token_klare_meldung(self):
        (self.konfig / "token").unlink()
        r = self.lauf()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("token", r.stderr)
        self.assertFalse((self.tmp / "aufrufe").exists() and any(z.startswith("attach") for z in self.aufrufe()))

    def test_neue_session_bekommt_eigenes_minimiertes_arbeitsfenster(self):
        r = self.lauf()
        self.assertEqual(r.returncode, 0, r.stderr)
        a = self.aufrufe()
        self.assertTrue(any(z.startswith("google-chrome --new-window") for z in a))
        self.assertLess(next(i for i, z in enumerate(a) if z.startswith("google-chrome")),
                        next(i for i, z in enumerate(a) if z.startswith("attach")), "Fenster vor dem Anhängen")
        self.assertTrue(self.fenster()[900]["minimized"], "Arbeitsfenster minimiert")
        self.assertFalse(self.fenster()[2]["minimized"], "Gorans Fenster unberührt")
        self.assertEqual("900", (self.konfig / "fenster-gchrome").read_text().strip())
        self.assertIn("Arbeitsfenster", r.stdout)

    def test_bekanntes_arbeitsfenster_wird_aktiviert_statt_neu_geoeffnet(self):
        self.setze_fenster([fenster(1, "org.gnome.Ptyxis", "Terminal", fokus=True),
                            fenster(2, "google-chrome", "Gorans Seite - Google Chrome"),
                            fenster(77, "google-chrome", "Alt - Google Chrome", minimiert=True)])
        (self.konfig / "fenster-gchrome").write_text("77\n")
        r = self.lauf()
        self.assertEqual(r.returncode, 0, r.stderr)
        a = self.aufrufe()
        self.assertFalse(any(z.startswith("google-chrome") for z in a))
        self.assertTrue(any("Windows.Activate 77" in z for z in a))
        self.assertLess(next(i for i, z in enumerate(a) if "Activate" in z), next(i for i, z in enumerate(a) if z.startswith("attach")))
        self.assertTrue(self.fenster()[77]["minimized"])
        self.assertFalse(self.fenster()[2]["minimized"])

    def test_verschwundenes_arbeitsfenster_wird_ersetzt(self):
        (self.konfig / "fenster-gchrome").write_text("77\n")
        r = self.lauf()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(any(z.startswith("google-chrome --new-window") for z in self.aufrufe()))
        self.assertEqual("900", (self.konfig / "fenster-gchrome").read_text().strip())

    def test_tab_in_fremdem_fenster_wird_nicht_minimiert_sondern_gemeldet(self):
        # Goran klickt nach dem Öffnen des Arbeitsfensters in sein eigenes Fenster: der Session-Tab entsteht dort.
        (self.tmp / "bin" / "google-chrome").write_text(FALSCH_CHROME.replace('f.append(', 'f[1]["focus"] = True; f.append(')
                                                          .replace('"focus": True, "minimized"', '"focus": False, "minimized"'))
        r = self.lauf()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(any("Minimize" in z for z in self.aufrufe()))
        self.assertFalse(self.fenster()[2]["minimized"])
        self.assertIn("nicht im Arbeitsfenster", r.stdout)

    def test_zeigen_holt_das_arbeitsfenster_hervor_und_verstecken_minimiert_es(self):
        self.setze_fenster([fenster(1, "org.gnome.Ptyxis", "Terminal", fokus=True),
                            fenster(77, "google-chrome", "Arbeitsfenster gchrome - Google Chrome", minimiert=True)])
        (self.konfig / "fenster-gchrome").write_text("77\n")
        r = self.lauf("--zeigen")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.fenster()[77]["minimized"])
        self.assertTrue(self.fenster()[77]["focus"])
        self.assertFalse((self.tmp / "offen").exists(), "zeigen hängt nicht an")
        r = self.lauf("--verstecken")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.fenster()[77]["minimized"])

    def test_zeigen_ohne_bekanntes_fenster_meldet_es(self):
        r = self.lauf("--zeigen")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("kein Arbeitsfenster", r.stderr)

    def test_ohne_window_calls_nur_anhaengen(self):
        (self.tmp / "ohne-wc").touch()
        r = self.lauf()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(any(z.startswith("attach") for z in self.aufrufe()))
        self.assertFalse(any(z.startswith("google-chrome") for z in self.aufrufe()))
        self.assertIn("Window Calls", r.stdout)


if __name__ == "__main__":
    unittest.main()
