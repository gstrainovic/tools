#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["google-api-python-client>=2.150", "google-auth-oauthlib>=1.2"]
# ///
"""
gsc: Google Search Console aus der Kommandozeile (Search Console API v1).

Zugang: derselbe OAuth-Client (Typ Desktop) wie `ads`, Datei ~/.config/google-ads/client_secret.json.
Der Refresh-Token von `ads` gilt nur für die Ads API, darum eigener Login mit den Scopes `webmasters`
und `siteverification`; gespeichert in ~/.config/google-search-console/token.json (Modus 600, nie in ein Repo).
Search Console API und Site Verification API müssen im Cloud-Projekt des OAuth-Clients eingeschaltet sein.
`add-domain` setzt den TXT-Eintrag per Infomaniak-API (Token ~/.config/infomaniak/token) in der Zone der Domain.

Befehle:
    gsc login [--no-browser]                       OAuth im Browser, speichert den Refresh-Token
    gsc sites                                      Properties mit Berechtigung
    gsc sitemaps [--site wartungsheft.ch]          gemeldete Sitemaps mit Status
    gsc submit SITEMAP-URL [--site ...]            Sitemap (erneut) einreichen
    gsc inspect URL [URL ...] [--site ...] [--json]   URL-Prüfung: Urteil, Abdeckung, Kanonisch, letzter Crawl
    gsc coverage [--sitemap URL] [--site ...]      alle URLs der Sitemap prüfen, eine Zeile pro URL
    gsc queries [--days 28] [--site ...]           Suchanfragen mit Klicks und Impressionen
    gsc add-domain DOMAIN [--sitemap URL]          Domain-Property anlegen: TXT-Token holen, DNS-Eintrag bei
                                                   Infomaniak setzen, bestätigen, Property und Sitemap hinzufügen
Property: --site wartungsheft.ch (Domain-Property) oder Umgebungsvariable GSC_SITE.
Die API kennt keinen Indexierungsantrag; der geht nur in der Oberfläche (URL-Prüfung → Indexierung beantragen).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

CLIENT_SECRET = Path.home() / ".config" / "google-ads" / "client_secret.json"
CONFIG_DIR = Path.home() / ".config" / "google-search-console"
TOKEN = CONFIG_DIR / "token.json"
SCOPE = "https://www.googleapis.com/auth/webmasters"
SCOPE_VERIFICATION = "https://www.googleapis.com/auth/siteverification"
SCOPES = [SCOPE, SCOPE_VERIFICATION]
INFOMANIAK_TOKEN = Path.home() / ".config" / "infomaniak" / "token"
INFOMANIAK_NS = "ns11.infomaniak.ch"
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
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), scopes=SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline", open_browser=not args.no_browser)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    old = os.umask(0o077)
    try:
        TOKEN.write_text(creds.to_json())
    finally:
        os.umask(old)
    print(f"gespeichert: {TOKEN}")


def service(api: str = "searchconsole", version: str = "v1"):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    if not TOKEN.exists():
        sys.exit(f"kein Token, zuerst `gsc login` ({TOKEN})")
    # Scopes aus dem Token selbst (nach `gsc login` webmasters und siteverification); eine feste Liste
    # liesse ältere Tokens beim Erneuern mit «invalid_scope» scheitern.
    creds = Credentials.from_authorized_user_file(str(TOKEN))
    if api == "siteVerification" and not creds.has_scopes([SCOPE_VERIFICATION]):
        sys.exit("Token ohne Scope siteverification, einmal neu anmelden: gsc login")
    return build(api, version, credentials=creds, cache_discovery=False)


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


class Infomaniak:
    """DNS-Einträge per Infomaniak-API v2 (Zone = Domain, Wurzel = Quelle «.»)."""

    def __init__(self, token: str, oeffne=urllib.request.urlopen):
        self.token, self.oeffne = token, oeffne

    def txt_anlegen(self, zone: str, wert: str) -> int:
        body = json.dumps({"type": "TXT", "source": ".", "target": wert, "ttl": 300}).encode()
        req = urllib.request.Request(f"https://api.infomaniak.com/2/zones/{zone}/records", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {self.token}",
                                              "Content-Type": "application/json"})
        with self.oeffne(req, timeout=30) as resp:
            antwort = json.loads(resp.read())
        if antwort.get("result") != "success":
            raise RuntimeError(f"Infomaniak: {antwort}")
        return antwort["data"]["id"]


def dig_txt(domain: str, ns: str) -> str:
    return subprocess.run(["dig", "+short", "TXT", domain, f"@{ns}"], capture_output=True, text=True).stdout


def lies_url(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read().decode()
    except OSError:
        return None


def sitemap_aus_robots(robots: str | None) -> str | None:
    for zeile in (robots or "").splitlines():
        name, _, wert = zeile.partition(":")
        if name.strip().lower() == "sitemap" and wert.strip():
            return wert.strip()
    return None


def domain_anlegen(domain: str, *, verification, searchconsole, dns, dig, lies_url, sitemap: str | None = None,
                   schlaf=time.sleep, wartezeit: int = 600, intervall: int = 10, ausgabe=print) -> None:
    site = {"type": "INET_DOMAIN", "identifier": domain}
    wert = verification.webResource().getToken(body={"site": site, "verificationMethod": "DNS_TXT"}).execute()["token"]
    ausgabe(f"TXT-Wert: {wert}")
    if wert in dig(domain, INFOMANIAK_NS):
        ausgabe(f"TXT schon vorhanden bei {INFOMANIAK_NS}")
    else:
        record_id = dns.txt_anlegen(domain, wert)
        ausgabe(f"TXT angelegt in Zone {domain}, Infomaniak-Record-ID {record_id}")
        for _ in range(max(1, wartezeit // intervall)):
            schlaf(intervall)
            if wert in dig(domain, INFOMANIAK_NS):
                break
        else:
            raise TimeoutError(f"TXT nach {wartezeit} s bei {INFOMANIAK_NS} nicht sichtbar (Record-ID {record_id})")
        ausgabe(f"TXT sichtbar bei {INFOMANIAK_NS}")
    verification.webResource().insert(verificationMethod="DNS_TXT", body={"site": site}).execute()
    ausgabe(f"bestätigt: {domain}")
    prop = site_url(domain)
    searchconsole.sites().add(siteUrl=prop).execute()
    ausgabe(f"Property hinzugefügt: {prop}")
    sitemap = sitemap or sitemap_aus_robots(lies_url(f"https://www.{domain}/robots.txt")) \
        or f"https://www.{domain}/sitemap.xml"
    searchconsole.sitemaps().submit(siteUrl=prop, feedpath=sitemap).execute()
    ausgabe(f"Sitemap eingereicht: {sitemap}")


def cmd_add_domain(args) -> None:
    verification = service("siteVerification", "v1")
    try:
        domain_anlegen(args.domain, verification=verification, searchconsole=service(),
                       dns=Infomaniak(INFOMANIAK_TOKEN.read_text().strip()), dig=dig_txt, lies_url=lies_url,
                       sitemap=args.sitemap, wartezeit=args.wartezeit)
    except TimeoutError as e:
        sys.exit(f"Abbruch: {e}")


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
    s = sub.add_parser("add-domain")
    s.add_argument("domain")
    s.add_argument("--sitemap", help="Standard: Sitemap aus https://www.DOMAIN/robots.txt, sonst /sitemap.xml")
    s.add_argument("--wartezeit", type=int, default=600, help="Sekunden, bis der TXT-Eintrag sichtbar sein muss")
    s.set_defaults(fn=cmd_add_domain)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
