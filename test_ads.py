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


class DemandGenOperationen(unittest.TestCase):
    """Operationen ohne Netz: GoogleAdsClient baut die Typen auch ohne Zugangsdaten."""

    @classmethod
    def setUpClass(cls):
        from google.ads.googleads.client import GoogleAdsClient
        cls.c = GoogleAdsClient(credentials=None, developer_token="test", use_proto_plus=True)
        spec = {**DG, "geo_target_constant": ["geoTargetConstants/1", "geoTargetConstants/2"]}
        cls.ops = ads.demand_gen_operations(cls.c, "123", spec, b"PNG")

    def teil(self, art):
        return [getattr(o, art).create for o in self.ops if o._pb.HasField(art)]

    def test_kampagne_demand_gen_pausiert_mit_klickgebot(self):
        (k,) = self.teil("campaign_operation")
        self.assertEqual(k.advertising_channel_type, self.c.enums.AdvertisingChannelTypeEnum.DEMAND_GEN)
        self.assertEqual(k.status, self.c.enums.CampaignStatusEnum.PAUSED)
        # Demand Gen nimmt bei target_spend keine Obergrenze an; max_cpc_chf wird zum Ziel-CPC
        self.assertEqual(k.target_cpc.target_cpc_micros, 1_000_000)

    def test_gesamtbudget_ueber_den_zeitraum(self):
        (b,) = self.teil("campaign_budget_operation")
        self.assertEqual(b.total_amount_micros, 50_000_000)
        self.assertFalse(b.explicitly_shared)

    def test_nur_youtube_ohne_discover_gmail_display_maps(self):
        (g,) = self.teil("ad_group_operation")
        kanaele = g.demand_gen_ad_group_settings.channel_controls.selected_channels
        self.assertTrue(kanaele.youtube_in_stream and kanaele.youtube_in_feed and kanaele.youtube_shorts)
        self.assertFalse(kanaele.discover or kanaele.gmail or kanaele.display or kanaele.maps)

    def test_jeder_ort_und_die_sprache_auf_der_anzeigengruppe(self):
        kriterien = self.teil("ad_group_criterion_operation")
        orte = [k.location.geo_target_constant for k in kriterien if k.location.geo_target_constant]
        self.assertEqual(orte, ["geoTargetConstants/1", "geoTargetConstants/2"])
        self.assertIn("languageConstants/1001", [k.language.language_constant for k in kriterien])

    def test_videoanzeige_mit_video_logo_und_texten(self):
        assets = self.teil("asset_operation")
        self.assertIn("abc123", [a.youtube_video_asset.youtube_video_id for a in assets])
        self.assertIn(b"PNG", [a.image_asset.data for a in assets])
        (ad,) = self.teil("ad_group_ad_operation")
        v = ad.ad.demand_gen_video_responsive_ad
        self.assertEqual(v.business_name.text, "Wartungsheft")
        self.assertEqual([h.text for h in v.headlines], ["Rechnung fotografieren"])
        self.assertEqual(ad.ad.final_urls[0], "https://wartungsheft.ch/youtube")


class KeywordLines(unittest.TestCase):
    def test_leere_zeilen_und_kommentare_fallen_weg(self):
        self.assertEqual(ads.keyword_lines(["serviceheft app\n", "\n", "# Kommentar\n", "  mfk app  \n"]),
                         ["serviceheft app", "mfk app"])

    def test_doppelte_nur_einmal(self):
        self.assertEqual(ads.keyword_lines(["a", "A", "a"]), ["a"])


def ergebnis(text, monate):
    """Antwort des Keyword-Planers wie von der API: month ist der Enum-Wert (JANUARY = 2)."""
    from types import SimpleNamespace as N
    volumen = [N(year=j, month=m + 1, monthly_searches=s) for j, m, s in monate]
    return N(text=text, keyword_metrics=N(monthly_search_volumes=volumen))


class Verlauf(unittest.TestCase):
    def test_zeitraum_endet_mit_dem_letzten_vollen_monat(self):
        import datetime
        self.assertEqual(ads.verlauf_zeitraum(datetime.date(2026, 10, 9), 24), ((2024, 10), (2026, 9)))
        self.assertEqual(ads.verlauf_zeitraum(datetime.date(2026, 1, 15), 12), ((2025, 1), (2025, 12)))

    def test_jahresvergleich_je_keyword_sortiert_nach_letzten_zwoelf_monaten(self):
        alt = [(2024, m, 100) for m in range(10, 13)] + [(2025, m, 100) for m in range(1, 10)]
        neu = [(2025, m, 80) for m in range(10, 13)] + [(2026, m, 80) for m in range(1, 10)]
        steigt = [(j, m, 10) for j, m, _ in alt] + [(j, m, 20) for j, m, _ in neu]
        text = ads.verlauf_text([ergebnis("klara login", alt + neu), ergebnis("abaninja", steigt)])
        zeilen = text.splitlines()
        self.assertEqual(zeilen[0], "Letzte 12 Mt\tVorjahr\tÄnderung\tKeyword\tMonate 2024-10 bis 2026-09")
        self.assertTrue(zeilen[1].startswith("960\t1200\t-20 %\tklara login\t"))
        self.assertTrue(zeilen[2].startswith("240\t120\t+100 %\tabaninja\t"))

    def test_fehlende_monate_ergeben_keine_aenderung(self):
        nur_neu = [(2025, m, 50) for m in range(10, 13)] + [(2026, m, 50) for m in range(1, 10)]
        zeile = ads.verlauf_text([ergebnis("neu", [(2024, 10, None)] + nur_neu)]).splitlines()[1]
        self.assertTrue(zeile.startswith("600\t–\t–\tneu\t"))


if __name__ == "__main__":
    unittest.main()
