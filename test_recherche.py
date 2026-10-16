import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
