import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("ads", Path(__file__).with_name("ads.py"))
ads = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ads)


class YamlText(unittest.TestCase):
    def test_ohne_developer_token(self):
        text = ads.yaml_text("id", "secret", "refresh")
        self.assertIn("client_id: id\n", text)
        self.assertIn("refresh_token: refresh\n", text)
        self.assertNotIn("developer_token", text)


class Customer(unittest.TestCase):
    def test_befehl_mit_konto_verlangt_customer(self):
        with self.assertRaises(SystemExit):
            ads.main(["--customer", "", "campaigns"])


SPEC = {
    "campaign": "Test", "start": "2026-09-24 00:00:00", "end": "2026-10-23 23:59:59",
    "total_budget_chf": 100, "max_cpc_chf": 2, "ad_group": "G", "final_url": "https://wartungsheft.ch/google",
    "geo_target_constant": "geoTargetConstants/2756", "language_constant": "languageConstants/1001",
    "keywords_phrase": ["fuhrpark app"], "headlines": ["A", "B", "C"], "descriptions": ["x", "y"],
}


class CheckSpec(unittest.TestCase):
    def test_gueltig(self):
        self.assertEqual(ads.check_spec(SPEC), [])

    def test_titel_zu_lang(self):
        errors = ads.check_spec({**SPEC, "headlines": ["A" * 31, "B", "C"]})
        self.assertTrue(any("30" in e for e in errors))

    def test_beschreibung_zu_lang(self):
        errors = ads.check_spec({**SPEC, "descriptions": ["x" * 91, "y"]})
        self.assertTrue(any("90" in e for e in errors))

    def test_zu_wenige_titel(self):
        self.assertTrue(ads.check_spec({**SPEC, "headlines": ["A", "B"]}))

    def test_pflichtfeld_fehlt(self):
        spec = dict(SPEC)
        del spec["total_budget_chf"]
        self.assertTrue(any("total_budget_chf" in e for e in ads.check_spec(spec)))

    def test_ausschliessende_keywords_sind_liste(self):
        self.assertTrue(ads.check_spec({**SPEC, "negative_keywords": "gps"}))
        self.assertEqual(ads.check_spec({**SPEC, "negative_keywords": ["gps", "fahrtenbuch"]}), [])

    def test_startet_nie_aktiv(self):
        self.assertTrue(ads.check_spec({**SPEC, "status": "ENABLED"}))


if __name__ == "__main__":
    unittest.main()
