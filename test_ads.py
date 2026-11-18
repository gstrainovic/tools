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


class SuchOperationen(unittest.TestCase):
    """Suchkampagne ohne Netz: mehrere Orte und «nur Personen am Ort» (Gorans Entscheid 1098a)."""

    @classmethod
    def setUpClass(cls):
        from google.ads.googleads.client import GoogleAdsClient
        cls.c = GoogleAdsClient(credentials=None, developer_token="test", use_proto_plus=True)

    def kampagne_und_orte(self, spec):
        ops = ads.create_operations(self.c, "123", spec)
        (k,) = [o.campaign_operation.create for o in ops if o._pb.HasField("campaign_operation")]
        kriterien = [o.campaign_criterion_operation.create for o in ops if o._pb.HasField("campaign_criterion_operation")]
        orte = [kr.location.geo_target_constant for kr in kriterien if kr.location.geo_target_constant]
        return k, orte

    def test_jeder_ort_einzeln(self):
        _, orte = self.kampagne_und_orte({**SPEC, "geo_target_constant": ["geoTargetConstants/1", "geoTargetConstants/2"]})
        self.assertEqual(orte, ["geoTargetConstants/1", "geoTargetConstants/2"])

    def test_einzelner_ort_geht_weiter(self):
        _, orte = self.kampagne_und_orte(SPEC)
        self.assertEqual(orte, ["geoTargetConstants/2756"])

    def test_nur_personen_am_ort(self):
        k, _ = self.kampagne_und_orte({**SPEC, "nur_am_ort": True})
        self.assertEqual(k.geo_target_type_setting.positive_geo_target_type,
                         self.c.enums.PositiveGeoTargetTypeEnum.PRESENCE)

    def test_ohne_angabe_googles_standard(self):
        k, _ = self.kampagne_und_orte(SPEC)
        self.assertFalse(k._pb.HasField("geo_target_type_setting"))


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

    def test_ohne_klickpreis_bietet_google_selbst(self):
        # max_cpc_chf null: Klicks maximieren ohne Ziel, nur das Gesamtbudget begrenzt (Gorans Entscheid 1097a)
        self.assertEqual(ads.check_demand_gen({**DG, "max_cpc_chf": None}), [])
        ops = ads.demand_gen_operations(self.c, "123", {**DG, "max_cpc_chf": None}, b"PNG")
        (k,) = [o.campaign_operation.create for o in ops if o._pb.HasField("campaign_operation")]
        self.assertTrue(k._pb.HasField("target_spend"))
        self.assertFalse(k._pb.HasField("target_cpc"))
        self.assertEqual(k.target_spend.cpc_bid_ceiling_micros, 0)

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


DISPLAY = {
    "campaign": "D", "start": "2026-11-18 00:00:00", "end": "2026-12-31 23:59:59", "total_budget_chf": 30,
    "max_cpc_chf": None, "ad_group": "G", "final_url": "https://pink-deko.ch/?utm_source=google-display",
    "geo_target_constant": ["geoTargetConstants/1", "geoTargetConstants/2"], "nur_am_ort": True,
    "language_constant": "languageConstants/1001", "business_name": "Pink Deko",
    "marketing_image": "quer.jpg", "square_image": "quadrat.jpg",
    "headlines": ["Geschenksets ab CHF 9.90"], "long_headline": "Weihnachtsgeschenke aus Steinach",
    "descriptions": ["Gratis abholen in 9323 Steinach"],
}


class CheckDisplay(unittest.TestCase):
    def test_gueltig(self):
        self.assertEqual(ads.check_display(DISPLAY), [])

    def test_titel_hoechstens_30(self):
        self.assertTrue(any("30" in e for e in ads.check_display({**DISPLAY, "headlines": ["x" * 31]})))

    def test_langer_titel_hoechstens_90(self):
        self.assertTrue(any("90" in e for e in ads.check_display({**DISPLAY, "long_headline": "x" * 91})))

    def test_bilder_pflicht(self):
        spec = dict(DISPLAY)
        del spec["square_image"]
        self.assertTrue(any("square_image" in e for e in ads.check_display(spec)))

    def test_startet_nie_aktiv(self):
        self.assertTrue(ads.check_display({**DISPLAY, "status": "ENABLED"}))


class DisplayOperationen(unittest.TestCase):
    """Bildanzeigen auf fremden Websites (Gorans Entscheid 1100b): nur Displaynetzwerk, nur Personen am Ort."""

    @classmethod
    def setUpClass(cls):
        from google.ads.googleads.client import GoogleAdsClient
        cls.c = GoogleAdsClient(credentials=None, developer_token="test", use_proto_plus=True)
        cls.ops = ads.display_operations(cls.c, "123", DISPLAY, b"QUER", b"QUADRAT")

    def teil(self, art):
        return [getattr(o, art).create for o in self.ops if o._pb.HasField(art)]

    def test_kampagne_nur_im_displaynetzwerk_pausiert(self):
        (k,) = self.teil("campaign_operation")
        self.assertEqual(k.advertising_channel_type, self.c.enums.AdvertisingChannelTypeEnum.DISPLAY)
        self.assertEqual(k.status, self.c.enums.CampaignStatusEnum.PAUSED)
        self.assertTrue(k.network_settings.target_content_network)
        self.assertFalse(k.network_settings.target_google_search or k.network_settings.target_search_network)

    def test_klicks_maximieren_ohne_obergrenze(self):
        (k,) = self.teil("campaign_operation")
        self.assertTrue(k._pb.HasField("target_spend"))
        self.assertEqual(k.target_spend.cpc_bid_ceiling_micros, 0)

    def test_gesamtbudget_als_tagesbudget_ueber_die_laufzeit(self):
        # Display lehnt CUSTOM_PERIOD ab (INVALID_PERIOD): 30 CHF auf 44 Tage (18.11.–31.12.) = 0.68 je Tag
        (b,) = self.teil("campaign_budget_operation")
        self.assertEqual(b.period, self.c.enums.BudgetPeriodEnum.DAILY)
        self.assertEqual(b.amount_micros, 680_000)
        self.assertEqual(b.total_amount_micros, 0)

    def test_orte_nur_personen_am_ort(self):
        (k,) = self.teil("campaign_operation")
        self.assertEqual(k.geo_target_type_setting.positive_geo_target_type,
                         self.c.enums.PositiveGeoTargetTypeEnum.PRESENCE)
        orte = [kr.location.geo_target_constant for kr in self.teil("campaign_criterion_operation")
                if kr.location.geo_target_constant]
        self.assertEqual(orte, ["geoTargetConstants/1", "geoTargetConstants/2"])

    def test_anzeige_mit_beiden_bildern_und_texten(self):
        assets = self.teil("asset_operation")
        self.assertEqual(sorted(a.image_asset.data for a in assets), [b"QUADRAT", b"QUER"])
        (ad,) = self.teil("ad_group_ad_operation")
        r = ad.ad.responsive_display_ad
        self.assertEqual(r.business_name, "Pink Deko")
        self.assertEqual(r.long_headline.text, "Weihnachtsgeschenke aus Steinach")
        self.assertEqual(len(r.marketing_images), 1)
        self.assertEqual(len(r.square_marketing_images), 1)
        self.assertEqual(ad.ad.final_urls[0], "https://pink-deko.ch/?utm_source=google-display")


class AppsAusschliessen(unittest.TestCase):
    """Gorans Entscheid 1127a: Display-Anzeigen nicht in Handy-Apps (Fehlklicks in Spielen)."""

    def test_alle_apps_als_ausschluss_der_kampagne(self):
        from google.ads.googleads.client import GoogleAdsClient
        c = GoogleAdsClient(credentials=None, developer_token="test", use_proto_plus=True)
        # 60000 ist «Google Play», 60500 «Apple App Store»: beide nötig für alle Apps
        krs = [o.campaign_criterion_operation.create for o in ads.apps_ausschliessen_operationen(c, "123", "-2")]
        self.assertTrue(all(kr.negative and kr.campaign == "customers/123/campaigns/-2" for kr in krs))
        self.assertEqual(sorted(kr.mobile_app_category.mobile_app_category_constant for kr in krs),
                         ["mobileAppCategoryConstants/60000", "mobileAppCategoryConstants/60500"])

    def test_display_kampagne_schliesst_apps_auf_wunsch_aus(self):
        from google.ads.googleads.client import GoogleAdsClient
        c = GoogleAdsClient(credentials=None, developer_token="test", use_proto_plus=True)
        ops = ads.display_operations(c, "123", {**DISPLAY, "apps_ausschliessen": True}, b"Q", b"Q")
        kat = [o.campaign_criterion_operation.create.mobile_app_category.mobile_app_category_constant
               for o in ops if o._pb.HasField("campaign_criterion_operation")]
        self.assertIn("mobileAppCategoryConstants/60000", kat)
        self.assertIn("mobileAppCategoryConstants/60500", kat)


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
