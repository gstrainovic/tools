#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["bingads>=13.0.29"]
# ///
"""
bing: Microsoft-Advertising-Konto aus der Kommandozeile, über die offizielle Bibliothek `bingads`.

Anmeldung mit Google (das Konto ist per Google angelegt), OAuth-Client wie bei `ads`:
~/.config/google-ads/client_secret.json. Dateien in ~/.config/bing-ads/ (Modus 600, nie in ein Repo):
    config.toml      developer_token, customer_id, account_id (Developer-Token aus den Entwicklereinstellungen)
    refresh_token    schreibt `bing login`

Befehle:
    bing login                             Google-Anmeldung im Browser, speichert den Refresh-Token
    bing campaigns                         ID, Status, Budget pro Tag, Name
    bing ads                               Anzeigen mit Ziel-URLs
    bing replace-url ALT NEU [--dry-run]   Ziel-URL in allen Anzeigen ersetzen (exakter Treffer)
    bing budget ID CHF                     Tagesbudget einer Kampagne setzen
    bing pause ID ... | bing enable ID ... Kampagnen anhalten oder einschalten
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import sys
import threading
import tomllib
import webbrowser
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "bing-ads"
CONFIG = CONFIG_DIR / "config.toml"
REFRESH = CONFIG_DIR / "refresh_token"
GOOGLE_CLIENT = Path.home() / ".config" / "google-ads" / "client_secret.json"


def load_config(path: Path = CONFIG) -> dict:
    return tomllib.loads(path.read_text())


def replace_urls(urls: list[str], old: str, new: str) -> list[str]:
    return [new if url == old else url for url in urls]


def oauth(port: int | None = None):
    from bingads.authorization import GoogleOAuthDesktopMobileAuthCodeGrant
    secret = json.loads(GOOGLE_CLIENT.read_text())["installed"]
    auth = GoogleOAuthDesktopMobileAuthCodeGrant(client_id=secret["client_id"], client_secret=secret["client_secret"])
    if port:
        auth.redirection_uri = f"http://localhost:{port}"
    return auth


def cmd_login(args) -> None:
    captured = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            captured["path"] = self.path
            self.send_response(200)
            self.end_headers()
            self.wfile.write("Angemeldet, das Fenster kann zu.".encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("localhost", 0), Handler)
    port = server.server_address[1]
    auth = oauth(port)
    url = auth.get_authorization_endpoint()
    print(f"Anmelden: {url}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    thread.join()
    auth.request_oauth_tokens_by_response_uri(f"http://localhost:{port}{captured['path']}")
    old = os.umask(0o077)
    try:
        REFRESH.write_text(auth.oauth_tokens.refresh_token)
    finally:
        os.umask(old)
    print(f"gespeichert: {REFRESH}")


def service():
    from bingads.authorization import AuthorizationData
    from bingads.service_client import ServiceClient
    cfg = load_config()
    auth = oauth()
    auth.request_oauth_tokens_by_refresh_token(REFRESH.read_text().strip())
    data = AuthorizationData(account_id=cfg["account_id"], customer_id=cfg["customer_id"],
                             developer_token=cfg["developer_token"], authentication=auth)
    return ServiceClient("CampaignManagementService", version=13, authorization_data=data), cfg


def blank(obj):
    """suds schickt nicht gesetzte Felder als leeren Wert mit, die API lehnt leere Enums ab: alles auf None."""
    for key in obj.__keylist__:
        setattr(obj, key, None)
    return obj


def campaigns(svc, cfg):
    result = svc.GetCampaignsByAccountId(AccountId=cfg["account_id"], CampaignType="Search")
    return result.Campaign if result else []


def ad_groups(svc, campaign_id):
    result = svc.GetAdGroupsByCampaignId(CampaignId=campaign_id)
    return result.AdGroup if result else []


def ads(svc, ad_group_id):
    types = svc.factory.create("ArrayOfAdType")
    types.AdType.append("ResponsiveSearch")
    result = svc.GetAdsByAdGroupId(AdGroupId=ad_group_id, AdTypes=types)
    return result.Ad if result else []


def cmd_campaigns(_args) -> None:
    svc, cfg = service()
    for c in campaigns(svc, cfg):
        print(f"{c.Id}\t{c.Status}\t{c.DailyBudget}/Tag\t{c.BudgetType}\t{c.Name}")


def cmd_ads(_args) -> None:
    svc, cfg = service()
    for c in campaigns(svc, cfg):
        for g in ad_groups(svc, c.Id):
            for ad in ads(svc, g.Id):
                urls = list(ad.FinalUrls.string) if ad.FinalUrls else []
                print(f"{c.Name}\t{g.Id}\t{ad.Id}\t{ad.Status}\t{' '.join(urls)}")


def cmd_replace_url(args) -> None:
    svc, cfg = service()
    for c in campaigns(svc, cfg):
        for g in ad_groups(svc, c.Id):
            for ad in ads(svc, g.Id):
                urls = list(ad.FinalUrls.string) if ad.FinalUrls else []
                new = replace_urls(urls, args.old, args.new)
                if new == urls:
                    continue
                print(f"{c.Name}: {' '.join(urls)} -> {' '.join(new)}")
                if args.dry_run:
                    continue
                update = blank(svc.factory.create("ResponsiveSearchAd"))
                update.Id = ad.Id
                update.Type = "ResponsiveSearch"
                final_urls = svc.factory.create("ns3:ArrayOfstring")
                final_urls.string = new
                update.FinalUrls = final_urls
                batch = svc.factory.create("ArrayOfAd")
                batch.Ad.append(update)
                svc.UpdateAds(AdGroupId=g.Id, Ads=batch)


def update_campaign(campaign_id: int, **fields) -> None:
    svc, cfg = service()
    c = blank(svc.factory.create("Campaign"))
    c.Id = campaign_id
    for key, value in fields.items():
        setattr(c, key, value)
    batch = svc.factory.create("ArrayOfCampaign")
    batch.Campaign.append(c)
    svc.UpdateCampaigns(AccountId=cfg["account_id"], Campaigns=batch)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="bing", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("login")
    s.add_argument("--no-browser", action="store_true")
    s.set_defaults(fn=cmd_login)
    sub.add_parser("campaigns").set_defaults(fn=cmd_campaigns)
    sub.add_parser("ads").set_defaults(fn=cmd_ads)
    s = sub.add_parser("replace-url")
    s.add_argument("old")
    s.add_argument("new")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_replace_url)
    s = sub.add_parser("budget")
    s.add_argument("id", type=int)
    s.add_argument("chf", type=float)
    s.set_defaults(fn=lambda a: update_campaign(a.id, DailyBudget=a.chf, BudgetType="DailyBudgetStandard"))
    for name, status in (("pause", "Paused"), ("enable", "Active")):
        s = sub.add_parser(name)
        s.add_argument("ids", nargs="+", type=int)
        s.set_defaults(fn=lambda a, st=status: [update_campaign(i, Status=st) for i in a.ids])
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
