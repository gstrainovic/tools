import importlib.util
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
