#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["google-api-python-client>=2.150", "google-auth-oauthlib>=1.2"]
# ///
"""
gsc: Google Search Console aus der Kommandozeile (Search Console API v1).

Zugang: derselbe OAuth-Client (Typ Desktop) wie `ads`, Datei ~/.config/google-ads/client_secret.json.
Der Refresh-Token von `ads` gilt nur für die Ads API, darum eigener Login mit dem Scope `webmasters`;
gespeichert in ~/.config/google-search-console/token.json (Modus 600, nie in ein Repo).
Die Search Console API muss im Cloud-Projekt des OAuth-Clients eingeschaltet sein.

Befehle:
    gsc login [--no-browser]                       OAuth im Browser, speichert den Refresh-Token
    gsc sites                                      Properties mit Berechtigung
    gsc sitemaps [--site wartungsheft.ch]          gemeldete Sitemaps mit Status
    gsc submit SITEMAP-URL [--site ...]            Sitemap (erneut) einreichen
    gsc inspect URL [URL ...] [--site ...] [--json]   URL-Prüfung: Urteil, Abdeckung, Kanonisch, letzter Crawl
    gsc coverage [--sitemap URL] [--site ...]      alle URLs der Sitemap prüfen, eine Zeile pro URL
    gsc queries [--days 28] [--site ...]           Suchanfragen mit Klicks und Impressionen
Property: --site wartungsheft.ch (Domain-Property) oder Umgebungsvariable GSC_SITE.
Die API kennt keinen Indexierungsantrag; der geht nur in der Oberfläche (URL-Prüfung → Indexierung beantragen).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

CLIENT_SECRET = Path.home() / ".config" / "google-ads" / "client_secret.json"
CONFIG_DIR = Path.home() / ".config" / "google-search-console"
TOKEN = CONFIG_DIR / "token.json"
SCOPE = "https://www.googleapis.com/auth/webmasters"
DEFAULT_SITE = os.environ.get("GSC_SITE", "wartungsheft.ch")
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def site_url(site: str) -> str:
    if site.startswith("sc-domain:") or site.startswith("http"):
        return site
    return f"sc-domain:{site}"


def sitemap_urls(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    return [loc.text.strip() for loc in root.iter(f"{SITEMAP_NS}loc") if loc.text]


def summarize(url: str, response: dict) -> dict:
    result = response.get("inspectionResult", {})
    index = result.get("indexStatusResult", {})
    return {
        "url": url,
        "verdict": index.get("verdict", ""),
        "coverage": index.get("coverageState", ""),
        "robots": index.get("robotsTxtState", ""),
        "indexing": index.get("indexingState", ""),
        "fetch": index.get("pageFetchState", ""),
        "crawled": index.get("lastCrawlTime", "")[:10],
        "canonical": index.get("googleCanonical", ""),
        "user_canonical": index.get("userCanonical", ""),
        "link": result.get("inspectionResultLink", ""),
    }


def cmd_login(args) -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), scopes=[SCOPE])
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline", open_browser=not args.no_browser)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    old = os.umask(0o077)
    try:
        TOKEN.write_text(creds.to_json())
    finally:
        os.umask(old)
    print(f"gespeichert: {TOKEN}")


def service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    if not TOKEN.exists():
        sys.exit(f"kein Token, zuerst `gsc login` ({TOKEN})")
    creds = Credentials.from_authorized_user_file(str(TOKEN), [SCOPE])
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def cmd_sites(_args) -> None:
    for s in service().sites().list().execute().get("siteEntry", []):
        print(f"{s['permissionLevel']}\t{s['siteUrl']}")


def cmd_sitemaps(args) -> None:
    for s in service().sitemaps().list(siteUrl=site_url(args.site)).execute().get("sitemap", []):
        contents = s.get("contents", [{}])[0]
        print(f"{s.get('lastSubmitted', '')[:10]}\t{s.get('lastDownloaded', '')[:10]}\t"
              f"errors={s.get('errors', 0)}\twarnings={s.get('warnings', 0)}\t"
              f"submitted={contents.get('submitted', '?')}\t{s['path']}")


def cmd_submit(args) -> None:
    service().sitemaps().submit(siteUrl=site_url(args.site), feedpath=args.sitemap).execute()
    print(f"eingereicht: {args.sitemap}")


def inspect(svc, site: str, url: str) -> dict:
    body = {"inspectionUrl": url, "siteUrl": site_url(site), "languageCode": "de-CH"}
    return svc.urlInspection().index().inspect(body=body).execute()


def print_rows(rows: list[dict]) -> None:
    print("Urteil\tAbdeckung\tCrawl\tKanonisch\tURL")
    for r in rows:
        canonical = "" if r["canonical"] in ("", r["url"]) else r["canonical"]
        print(f"{r['verdict']}\t{r['coverage']}\t{r['crawled']}\t{canonical}\t{r['url']}")


def cmd_inspect(args) -> None:
    svc = service()
    responses = [(u, inspect(svc, args.site, u)) for u in args.urls]
    if args.json:
        print(json.dumps([r for _, r in responses], ensure_ascii=False, indent=2))
        return
    print_rows([summarize(u, r) for u, r in responses])


def cmd_coverage(args) -> None:
    sitemap = args.sitemap or f"https://{args.site.removeprefix('sc-domain:')}/sitemap.xml"
    with urllib.request.urlopen(sitemap, timeout=30) as resp:
        urls = sitemap_urls(resp.read().decode())
    svc = service()
    print_rows([summarize(u, inspect(svc, args.site, u)) for u in urls])


def cmd_queries(args) -> None:
    end = date.today() - timedelta(days=2)
    body = {"startDate": str(end - timedelta(days=args.days)), "endDate": str(end),
            "dimensions": ["query"], "rowLimit": 100}
    rows = service().searchanalytics().query(siteUrl=site_url(args.site), body=body).execute().get("rows", [])
    print("Klicks\tImpressionen\tPosition\tAnfrage")
    for r in rows:
        print(f"{r['clicks']:.0f}\t{r['impressions']:.0f}\t{r['position']:.1f}\t{r['keys'][0]}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="gsc", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", default=DEFAULT_SITE)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("login")
    s.add_argument("--no-browser", action="store_true")
    s.set_defaults(fn=cmd_login)
    sub.add_parser("sites").set_defaults(fn=cmd_sites)
    sub.add_parser("sitemaps").set_defaults(fn=cmd_sitemaps)
    s = sub.add_parser("submit")
    s.add_argument("sitemap")
    s.set_defaults(fn=cmd_submit)
    s = sub.add_parser("inspect")
    s.add_argument("urls", nargs="+")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_inspect)
    s = sub.add_parser("coverage")
    s.add_argument("--sitemap")
    s.set_defaults(fn=cmd_coverage)
    s = sub.add_parser("queries")
    s.add_argument("--days", type=int, default=28)
    s.set_defaults(fn=cmd_queries)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
