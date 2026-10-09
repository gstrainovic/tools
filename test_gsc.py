import argparse
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location("gsc", Path(__file__).with_name("gsc.py"))
gsc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gsc)

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://wartungsheft.ch/</loc><lastmod>2026-09-01</lastmod></url>
  <url><loc>https://wartungsheft.ch/betrieb</loc></url>
</urlset>"""

INSPECTION = {
    "inspectionResult": {
        "inspectionResultLink": "https://search.google.com/search-console/inspect?resource_id=sc-domain:wartungsheft.ch&id=x",
        "indexStatusResult": {
            "verdict": "NEUTRAL",
            "coverageState": "Gecrawlt – zurzeit nicht indexiert",
            "robotsTxtState": "ALLOWED",
            "indexingState": "INDEXING_ALLOWED",
            "lastCrawlTime": "2026-09-20T03:11:00Z",
            "pageFetchState": "SUCCESSFUL",
            "googleCanonical": "https://wartungsheft.ch/betrieb",
            "userCanonical": "https://wartungsheft.ch/betrieb",
        },
    }
}


class SitemapUrls(unittest.TestCase):
    def test_liest_loc(self):
        self.assertEqual(gsc.sitemap_urls(SITEMAP), ["https://wartungsheft.ch/", "https://wartungsheft.ch/betrieb"])


class Summarize(unittest.TestCase):
    def test_zeile_mit_zustand(self):
        row = gsc.summarize("https://wartungsheft.ch/betrieb", INSPECTION)
        self.assertEqual(row["url"], "https://wartungsheft.ch/betrieb")
        self.assertEqual(row["verdict"], "NEUTRAL")
        self.assertEqual(row["coverage"], "Gecrawlt – zurzeit nicht indexiert")
        self.assertEqual(row["crawled"], "2026-09-20")
        self.assertEqual(row["canonical"], "https://wartungsheft.ch/betrieb")

    def test_fehlende_felder(self):
        row = gsc.summarize("https://x/", {"inspectionResult": {}})
        self.assertEqual(row["verdict"], "")
        self.assertEqual(row["coverage"], "")


class SiteUrl(unittest.TestCase):
    def test_domain_property(self):
        self.assertEqual(gsc.site_url("wartungsheft.ch"), "sc-domain:wartungsheft.ch")
        self.assertEqual(gsc.site_url("sc-domain:x.ch"), "sc-domain:x.ch")
        self.assertEqual(gsc.site_url("https://x.ch/"), "https://x.ch/")


class Aufruf:
    def __init__(self, log, name, result):
        self.log, self.name, self.result = log, name, result

    def execute(self):
        self.log.append(self.name)
        return self.result


class FakeVerification:
    def __init__(self, log):
        self.log, self.calls = log, {}

    def webResource(self):
        return self

    def getToken(self, body):
        self.calls["getToken"] = body
        return Aufruf(self.log, "token", {"method": "DNS_TXT", "token": "google-site-verification=abc"})

    def insert(self, verificationMethod, body):
        self.calls["insert"] = (verificationMethod, body)
        return Aufruf(self.log, "verify", {"id": "dns://kmu-plugins.ch"})


class FakeSearchConsole:
    def __init__(self, log):
        self.log, self.calls = log, {}

    def sites(self):
        return self

    def sitemaps(self):
        return self

    def add(self, siteUrl):
        self.calls["add"] = siteUrl
        return Aufruf(self.log, "add", {})

    def submit(self, siteUrl, feedpath):
        self.calls["submit"] = (siteUrl, feedpath)
        return Aufruf(self.log, "sitemap", {})


class FakeDns:
    def __init__(self, log):
        self.log, self.calls = log, []

    def txt_anlegen(self, zone, wert):
        self.calls.append((zone, wert))
        self.log.append("dns")
        return 4711


class DomainAnlegen(unittest.TestCase):
    def setUp(self):
        self.log, self.ausgabe = [], []
        self.verification = FakeVerification(self.log)
        self.searchconsole = FakeSearchConsole(self.log)
        self.dns = FakeDns(self.log)
        self.robots = "User-agent: *\nAllow: /\nSitemap: https://www.kmu-plugins.ch/sitemap-index.xml\n"

    def lauf(self, dig=None, **kw):
        if dig is None:
            dig = lambda domain, ns: '"google-site-verification=abc"\n' if "dns" in self.log else ""
        gsc.domain_anlegen("kmu-plugins.ch", verification=self.verification, searchconsole=self.searchconsole,
                           dns=self.dns, dig=dig, lies_url=lambda url: self.robots if url.endswith("/robots.txt") else None,
                           schlaf=lambda s: None, ausgabe=self.ausgabe.append, **kw)

    def test_reihenfolge_token_dns_verify_add_sitemap(self):
        self.lauf()
        self.assertEqual(self.log, ["token", "dns", "verify", "add", "sitemap"])
        self.assertEqual(self.verification.calls["getToken"],
                         {"site": {"type": "INET_DOMAIN", "identifier": "kmu-plugins.ch"}, "verificationMethod": "DNS_TXT"})
        self.assertEqual(self.dns.calls, [("kmu-plugins.ch", "google-site-verification=abc")])
        self.assertEqual(self.verification.calls["insert"],
                         ("DNS_TXT", {"site": {"type": "INET_DOMAIN", "identifier": "kmu-plugins.ch"}}))
        self.assertEqual(self.searchconsole.calls["add"], "sc-domain:kmu-plugins.ch")
        self.assertEqual(self.searchconsole.calls["submit"],
                         ("sc-domain:kmu-plugins.ch", "https://www.kmu-plugins.ch/sitemap-index.xml"))

    def test_record_id_wird_ausgegeben(self):
        self.lauf()
        self.assertTrue(any("4711" in zeile for zeile in self.ausgabe), self.ausgabe)

    def test_dns_zeitueberschreitung_bricht_vor_verify_und_add_ab(self):
        with self.assertRaises(TimeoutError):
            self.lauf(dig=lambda domain, ns: "", wartezeit=30, intervall=10)
        self.assertEqual(self.log, ["token", "dns"])
        self.assertNotIn("add", self.searchconsole.calls)

    def test_vorhandener_txt_wird_nicht_doppelt_angelegt(self):
        self.lauf(dig=lambda domain, ns: '"v=spf1 -all"\n"google-site-verification=abc"\n')
        self.assertEqual(self.log, ["token", "verify", "add", "sitemap"])
        self.assertEqual(self.dns.calls, [])

    def test_ohne_sitemap_in_robots_www_sitemap_xml(self):
        self.robots = "User-agent: *\nAllow: /\n"
        self.lauf()
        self.assertEqual(self.searchconsole.calls["submit"][1], "https://www.kmu-plugins.ch/sitemap.xml")


class Infomaniak(unittest.TestCase):
    def test_txt_auf_der_wurzel_anlegen_liefert_id(self):
        gesendet = []

        class Antwort:
            def __init__(self, body):
                self.body = body

            def read(self):
                return self.body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def oeffne(req, timeout=None):
            gesendet.append(req)
            return Antwort(b'{"result":"success","data":{"id":4711,"source":".","type":"TXT"}}')

        record_id = gsc.Infomaniak("geheim", oeffne=oeffne).txt_anlegen("kmu-plugins.ch", "google-site-verification=abc")
        self.assertEqual(record_id, 4711)
        req = gesendet[0]
        self.assertEqual(req.full_url, "https://api.infomaniak.com/2/zones/kmu-plugins.ch/records")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Authorization"), "Bearer geheim")
        self.assertEqual(json.loads(req.data),
                         {"type": "TXT", "source": ".", "target": "google-site-verification=abc", "ttl": 300})


class Login(unittest.TestCase):
    def test_fordert_webmasters_und_siteverification_an(self):
        angefordert = {}

        class Flow:
            @staticmethod
            def from_client_secrets_file(path, scopes):
                angefordert["scopes"] = scopes
                return Flow()

            def run_local_server(self, **kw):
                return type("Creds", (), {"to_json": lambda self: "{}"})()

        modul = types.ModuleType("google_auth_oauthlib.flow")
        modul.InstalledAppFlow = Flow
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(sys.modules, {"google_auth_oauthlib": types.ModuleType("google_auth_oauthlib"),
                                              "google_auth_oauthlib.flow": modul}), \
                mock.patch.object(gsc, "CONFIG_DIR", Path(tmp)), mock.patch.object(gsc, "TOKEN", Path(tmp) / "t.json"), \
                mock.patch("builtins.print"):
            gsc.cmd_login(argparse.Namespace(no_browser=True))
        self.assertEqual(set(angefordert["scopes"]), {"https://www.googleapis.com/auth/webmasters",
                                                      "https://www.googleapis.com/auth/siteverification"})


if __name__ == "__main__":
    unittest.main()
