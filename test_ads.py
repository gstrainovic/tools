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


DG = {
    "campaign": "T", "start": "2026-09-24 00:00:00", "end": "2026-10-23 23:59:59", "total_budget_chf": 50,
    "max_cpc_chf": 1, "ad_group": "G", "final_url": "https://wartungsheft.ch/youtube",
    "geo_target_constant": "geoTargetConstants/2756", "language_constant": "languageConstants/1001",
    "video_id": "abc123", "logo": "logo.png", "business_name": "Wartungsheft",
    "headlines": ["Rechnung fotografieren"], "long_headlines": ["Dein Servicebuch auf dem Handy"],
    "descriptions": ["30 Tage gratis testen"],
}


class CheckDemandGen(unittest.TestCase):
    def test_gueltig(self):
        self.assertEqual(ads.check_demand_gen(DG), [])

    def test_titel_hoechstens_40(self):
        self.assertTrue(any("40" in e for e in ads.check_demand_gen({**DG, "headlines": ["x" * 41]})))

    def test_firmenname_hoechstens_25(self):
        self.assertTrue(any("25" in e for e in ads.check_demand_gen({**DG, "business_name": "x" * 26})))

    def test_video_pflicht(self):
        spec = dict(DG)
        del spec["video_id"]
        self.assertTrue(any("video_id" in e for e in ads.check_demand_gen(spec)))

    def test_startet_nie_aktiv(self):
        self.assertTrue(ads.check_demand_gen({**DG, "status": "ENABLED"}))


class KeywordLines(unittest.TestCase):
    def test_leere_zeilen_und_kommentare_fallen_weg(self):
        self.assertEqual(ads.keyword_lines(["serviceheft app\n", "\n", "# Kommentar\n", "  mfk app  \n"]),
                         ["serviceheft app", "mfk app"])

    def test_doppelte_nur_einmal(self):
        self.assertEqual(ads.keyword_lines(["a", "A", "a"]), ["a"])


if __name__ == "__main__":
    unittest.main()
