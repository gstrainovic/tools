"""Tests für chrome_anhaengen.py mit einem falschen playwright-cli im PATH: python3 -m unittest test_chrome_anhaengen.py"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SKRIPT = Path(__file__).with_name("chrome_anhaengen.py")

FALSCH = """#!/bin/bash
echo "$* TOKEN=${PLAYWRIGHT_MCP_EXTENSION_TOKEN:-}" >> "$AUFRUFE"
if [[ "$*" == *tab-list* ]]; then
  [[ -f "$OFFEN" ]] && { echo "- 0: (current) [Seite](https://example.com)"; exit 0; }
  echo "The browser 'gchrome' is not open, please run open first"; exit 1
fi
if [[ "$*" == attach* ]]; then touch "$OFFEN"; echo "- Page URL: about:blank"; fi
"""


class ChromeAnhaengen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "bin").mkdir()
        cli = self.tmp / "bin" / "playwright-cli"
        cli.write_text(FALSCH)
        cli.chmod(0o755)
        (self.tmp / ".config" / "playwright-extension").mkdir(parents=True)
        (self.tmp / ".config" / "playwright-extension" / "token").write_text("geheim123\n")
        self.env = {**os.environ, "PATH": f"{self.tmp / 'bin'}:{os.environ['PATH']}", "HOME": str(self.tmp),
                    "AUFRUFE": str(self.tmp / "aufrufe"), "OFFEN": str(self.tmp / "offen")}

    def lauf(self, *args):
        return subprocess.run([str(SKRIPT), *args], env=self.env, capture_output=True, text=True)

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
        self.assertFalse(any(z.startswith("attach") for z in self.aufrufe()))
        self.assertIn("läuft schon", r.stdout)

    def test_andere_session(self):
        self.lauf("--session", "test")
        self.assertIn("attach --extension=chrome --session=test TOKEN=geheim123", self.aufrufe())

    def test_ohne_token_klare_meldung(self):
        (self.tmp / ".config" / "playwright-extension" / "token").unlink()
        r = self.lauf()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("token", r.stderr)
        self.assertFalse((self.tmp / "aufrufe").exists() and any(z.startswith("attach") for z in self.aufrufe()))


if __name__ == "__main__":
    unittest.main()
