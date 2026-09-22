#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["google-ads>=32", "google-auth-oauthlib>=1.2"]
# ///
"""
ads: Google-Ads-Konto aus der Kommandozeile, über die Google Ads API (Python-Bibliothek von Google).

Zugang: OAuth-Client vom Typ Desktop im Cloud-Projekt, dessen Zugriffsebene für die Ads API mindestens
«Explorer» ist (seit 09.09.2026 gibt es keine Developer-Tokens mehr, der Zugang hängt am Projekt).
Dateien in ~/.config/google-ads/ (Modus 600, nie in ein Repo):
    client_secret.json   heruntergeladener OAuth-Client
    google-ads.yaml      schreibt `ads login` (Refresh-Token)

Befehle:
    ads login [--no-browser]                     OAuth im Browser, speichert den Refresh-Token
    ads customers                                erreichbare Konten
    ads campaigns [--all]                        Kampagnen (ohne --all ohne entfernte)
    ads query "SELECT ... FROM ..."              beliebige GAQL-Abfrage, eine Zeile pro Ergebnis
    ads remove ID [ID ...] [--dry-run]           Kampagnen entfernen (endgültig, Statistik bleibt)
Konto: --customer 8173987962 oder Umgebungsvariable GOOGLE_ADS_CUSTOMER_ID.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "google-ads"
CLIENT_SECRET = CONFIG_DIR / "client_secret.json"
YAML = CONFIG_DIR / "google-ads.yaml"
SCOPE = "https://www.googleapis.com/auth/adwords"


def yaml_text(client_id: str, client_secret: str, refresh_token: str) -> str:
    return (
        f"client_id: {client_id}\n"
        f"client_secret: {client_secret}\n"
        f"refresh_token: {refresh_token}\n"
        "use_proto_plus: True\n"
    )


def campaign_line(row) -> str:
    c = row.campaign
    budget = row.campaign_budget.amount_micros / 1_000_000 if row.campaign_budget.amount_micros else 0
    return f"{c.id}\t{c.status.name}\t{c.advertising_channel_type.name}\t{budget:.2f}/Tag\t{c.name}"


def remove_operations(client, customer_id: str, ids: list[str]):
    service = client.get_service("CampaignService")
    ops = []
    for cid in ids:
        op = client.get_type("CampaignOperation")
        op.remove = service.campaign_path(customer_id, cid)
        ops.append(op)
    return ops


def cmd_login(args) -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), scopes=[SCOPE])
    # Ohne Browserstart druckt die Bibliothek die Adresse; so kann ein Agent sie im eigenen Tab öffnen
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline", open_browser=not args.no_browser)
    secret = json.loads(CLIENT_SECRET.read_text())["installed"]
    old = os.umask(0o077)
    try:
        YAML.write_text(yaml_text(secret["client_id"], secret["client_secret"], creds.refresh_token))
    finally:
        os.umask(old)
    print(f"gespeichert: {YAML}")


def client():
    from google.ads.googleads.client import GoogleAdsClient
    return GoogleAdsClient.load_from_storage(str(YAML))


def search(customer_id: str, query: str):
    return client().get_service("GoogleAdsService").search(customer_id=customer_id, query=query)


def cmd_customers(_args) -> None:
    for name in client().get_service("CustomerService").list_accessible_customers().resource_names:
        print(name.split("/")[-1])


def cmd_campaigns(args) -> None:
    where = "" if args.all else " WHERE campaign.status != 'REMOVED'"
    q = ("SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, "
         "campaign_budget.amount_micros FROM campaign" + where + " ORDER BY campaign.id")
    rows = list(search(args.customer, q))
    for row in rows:
        print(campaign_line(row))
    print(f"{len(rows)} Kampagnen", file=sys.stderr)


def cmd_query(args) -> None:
    for row in search(args.customer, args.gaql):
        print(type(row).to_json(row, indent=None) if hasattr(type(row), "to_json") else row)


def cmd_remove(args) -> None:
    c = client()
    ops = remove_operations(c, args.customer, args.ids)
    if args.dry_run:
        for op in ops:
            print(f"würde entfernen: {op.remove}")
        return
    response = c.get_service("CampaignService").mutate_campaigns(customer_id=args.customer, operations=ops)
    for result in response.results:
        print(f"entfernt: {result.resource_name}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="ads", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--customer", default=os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", ""))
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("login")
    s.add_argument("--no-browser", action="store_true", help="Adresse nur ausgeben, keinen Browser starten")
    s.set_defaults(fn=cmd_login)
    sub.add_parser("customers").set_defaults(fn=cmd_customers)
    s = sub.add_parser("campaigns")
    s.add_argument("--all", action="store_true")
    s.set_defaults(fn=cmd_campaigns)
    s = sub.add_parser("query")
    s.add_argument("gaql")
    s.set_defaults(fn=cmd_query)
    s = sub.add_parser("remove")
    s.add_argument("ids", nargs="+")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_remove)
    args = p.parse_args(argv)
    if args.cmd in ("campaigns", "query", "remove") and not args.customer:
        p.error("--customer fehlt (oder GOOGLE_ADS_CUSTOMER_ID setzen)")
    args.fn(args)


if __name__ == "__main__":
    main()
