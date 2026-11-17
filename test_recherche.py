import importlib.util
import io
import sys
import unittest
from unittest import mock
from pathlib import Path

spec = importlib.util.spec_from_file_location("recherche", Path(__file__).with_name("recherche.py"))
recherche = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recherche)

HTML = """<html><head><title>Beauty Studio Sonne</title><style>p{x:1}</style></head><body>
<script>var a = "CHF 999";</script>
<h1>Spray Tanning</h1><p>Ganzkörper&nbsp;CHF 45.&ndash; / Gesicht Fr. 20.00</p>
<p>Bahnhofstrasse 3, 9000 St. Gallen</p><p>Aktion: 2 für CHF 80</p>
<footer>Tel 071 222 33 44</footer></body></html>"""


class Auswertung(unittest.TestCase):
    def test_titel_ort_und_preise_aus_seite(self):
        a = recherche.auswerten("https://x.ch/preise", HTML, muster=None)
        self.assertEqual(a["titel"], "Beauty Studio Sonne")
        self.assertEqual(a["orte"], ["9000 St. Gallen"])
        self.assertEqual(a["preise"], ["CHF 45.–", "Fr. 20.00", "CHF 80"])

    def test_stichwort_mit_umfeld_ohne_script(self):
        a = recherche.auswerten("https://x.ch", HTML, muster=r"spray tanning")
        self.assertEqual(len(a["stellen"]), 1)
        self.assertIn("Spray Tanning", a["stellen"][0])
        self.assertIn("Ganzkörper", a["stellen"][0])
        self.assertNotIn("var a", a["stellen"][0])

    def test_tabelle_zeigt_quelle_ort_und_preis(self):
        zeile = recherche.tabellenzeile(
            {"url": "https://x.ch/p", "titel": "Beauty Studio Sonne", "orte": ["9000 St. Gallen"],
             "preise": ["CHF 45.–"], "stellen": ["… Spray Tanning Ganzkörper …"], "quelle": "exa"})
        self.assertEqual(zeile, "| exa | Beauty Studio Sonne | 9000 St. Gallen | CHF 45.– | … Spray Tanning Ganzkörper … | https://x.ch/p |")


class Exa(unittest.TestCase):
    def test_exa_treffer_und_kosten(self):
        antwort = {"results": [{"url": "https://a.ch", "title": "A", "highlights": ["h1"]}],
                   "costDollars": {"total": 0.007}}
        urls, kosten = recherche.exa_auslesen(antwort)
        self.assertEqual(urls, [("https://a.ch", "A", "h1")])
        self.assertEqual(kosten, 0.007)


GEMINI = {
    "candidates": [{
        "content": {"parts": [{"text": "Anbieter A in 9000 St. Gallen bietet es an [1]."}]},
        "groundingMetadata": {
            "webSearchQueries": ["spray tanning st. gallen", "sprühbräune ostschweiz"],
            "groundingChunks": [{"web": {"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/x",
                                         "title": "anbieter-a.ch"}}]}}],
    "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 400, "thoughtsTokenCount": 600}}


class Gegenprobe(unittest.TestCase):
    """Stufe 3 im Skill recherche: Gemini mit Google-Suche statt Codex (Gorans Entscheid 1007a)."""

    def test_anfrage_sucht_bei_google_und_verlangt_quellen(self):
        a = recherche.gemini_anfrage("Gibt es Spray-Tanning in St. Gallen?")
        self.assertEqual(a["tools"], [{"google_search": {}}])
        text = a["contents"][0]["parts"][0]["text"]
        self.assertIn("Gibt es Spray-Tanning in St. Gallen?", text)
        self.assertIn("Quelle", text)

    def test_antwort_quellen_suchanfragen_und_kosten(self):
        g = recherche.gemini_auslesen(GEMINI)
        self.assertEqual(g["text"], "Anbieter A in 9000 St. Gallen bietet es an [1].")
        self.assertEqual(g["quellen"], [("anbieter-a.ch", "https://vertexaisearch.cloud.google.com/grounding-api-redirect/x")])
        self.assertEqual(g["suchen"], 2)
        # 1000 × 0.75 + (400 + 600) × 3.75, je pro Million Tokens (Gemini 3.8 Flash bis 31.12.2026)
        self.assertAlmostEqual(g["kosten"], 0.00075 + 0.00375)

    def test_gegenprobe_allein_ohne_ddgs_und_exa(self):
        roh = io.BytesIO()
        aus = io.TextIOWrapper(roh, encoding="utf-8")
        with mock.patch.object(recherche, "gemini_gegenprobe", return_value=recherche.gemini_auslesen(GEMINI)) as gp, \
                mock.patch.object(recherche, "exa_suche", side_effect=AssertionError("Exa aufgerufen")), \
                mock.patch.object(recherche, "ddgs_suche", side_effect=AssertionError("ddgs aufgerufen")), \
                mock.patch.object(sys, "argv", ["recherche.py", "--gegenprobe", "Gibt es X?"]), \
                mock.patch.object(sys, "stdout", aus), \
                mock.patch.object(sys, "stderr", io.StringIO()):
            recherche.main()
            aus.flush()
        gp.assert_called_once_with("Gibt es X?")
        ausgabe = roh.getvalue().decode("utf-8")
        self.assertIn("Anbieter A", ausgabe)
        self.assertIn("[1] anbieter-a.ch https://vertexaisearch", ausgabe)


class WindowsKonsole(unittest.TestCase):
    def test_tabelle_auf_cp1252_konsole_bricht_nicht_ab(self):
        # Windows-Konsole ohne PYTHONUTF8: stdout kodiert cp1252, «→» und «ć» gibt es dort nicht
        roh = io.BytesIO()
        konsole = io.TextIOWrapper(roh, encoding="cp1252")
        treffer = [("https://x.ch", "Ana Đurić → Studio", "Auszug")]
        with mock.patch.object(recherche, "exa_suche", return_value=(treffer, 0.0)), \
                mock.patch.object(recherche, "seite_holen", return_value=""), \
                mock.patch.object(sys, "argv", ["recherche.py", "-q", "x", "--ohne-ddgs"]), \
                mock.patch.object(sys, "stdout", konsole), \
                mock.patch.object(sys, "stderr", io.StringIO()):
            recherche.main()
            sys.stdout.flush()
        self.assertIn("https://x.ch", roh.getvalue().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
