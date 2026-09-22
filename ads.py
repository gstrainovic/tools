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
    ads create SPEC.json [--validate-only]       Suchkampagne anlegen, immer pausiert, Gesamtbudget mit Enddatum
    ads enable ID [ID ...] | ads pause ID ...    Kampagnen ein- oder ausschalten
    ads keywords DATEI|-                         Suchvolumen und Klickpreise (Schweiz, Deutsch), braucht Basic
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


REQUIRED = ("campaign", "start", "end", "total_budget_chf", "max_cpc_chf", "ad_group", "final_url",
            "geo_target_constant", "language_constant", "keywords_phrase", "headlines", "descriptions")


def check_spec(spec: dict) -> list[str]:
    """Fehler in einer Kampagnenbeschreibung, leer wenn gültig. Neue Kampagnen starten immer pausiert."""
    errors = [f"{key} fehlt" for key in REQUIRED if key not in spec]
    if errors:
        return errors
    if spec.get("status", "PAUSED") != "PAUSED":
        errors.append("status muss PAUSED sein, aktiviert wird erst nach Freigabe mit `ads enable`")
    if not 3 <= len(spec["headlines"]) <= 15:
        errors.append("3 bis 15 Titel nötig")
    if not 2 <= len(spec["descriptions"]) <= 4:
        errors.append("2 bis 4 Beschreibungen nötig")
    errors += [f"Titel über 30 Zeichen: {h}" for h in spec["headlines"] if len(h) > 30]
    errors += [f"Beschreibung über 90 Zeichen: {d}" for d in spec["descriptions"] if len(d) > 90]
    if not spec["keywords_phrase"]:
        errors.append("keine Keywords")
    if not isinstance(spec.get("negative_keywords", []), list):
        errors.append("negative_keywords muss eine Liste sein")
    return errors


def micros(chf: float) -> int:
    return int(round(chf * 1_000_000))


def create_operations(c, customer_id: str, spec: dict) -> list:
    """Budget, Kampagne, Ort, Sprache, Anzeigengruppe, Keywords und Anzeige als eine Transaktion (temporäre IDs)."""
    ops = []

    def op(kind: str):
        o = c.get_type("MutateOperation")
        ops.append(o)
        return getattr(o, kind).create

    budget_rn = c.get_service("CampaignBudgetService").campaign_budget_path(customer_id, "-1")
    campaign_rn = c.get_service("CampaignService").campaign_path(customer_id, "-2")
    group_rn = c.get_service("AdGroupService").ad_group_path(customer_id, "-3")

    b = op("campaign_budget_operation")
    b.resource_name = budget_rn
    b.name = f"{spec['campaign']} Gesamtbudget"
    b.period = c.enums.BudgetPeriodEnum.CUSTOM_PERIOD
    b.total_amount_micros = micros(spec["total_budget_chf"])
    b.explicitly_shared = False

    k = op("campaign_operation")
    k.resource_name = campaign_rn
    k.name = spec["campaign"]
    k.status = c.enums.CampaignStatusEnum.PAUSED
    k.advertising_channel_type = c.enums.AdvertisingChannelTypeEnum.SEARCH
    k.campaign_budget = budget_rn
    k.start_date_time = spec["start"]
    k.end_date_time = spec["end"]
    k.target_spend.cpc_bid_ceiling_micros = micros(spec["max_cpc_chf"])
    k.network_settings.target_google_search = True
    k.network_settings.target_search_network = False
    k.network_settings.target_content_network = False
    k.network_settings.target_partner_search_network = False
    k.contains_eu_political_advertising = c.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING

    for field, value in (("location", spec["geo_target_constant"]), ("language", spec["language_constant"])):
        cc = op("campaign_criterion_operation")
        cc.campaign = campaign_rn
        getattr(cc, field).__setattr__("geo_target_constant" if field == "location" else "language_constant", value)

    # Ausschliessende Keywords auf Kampagnenebene (Wortgruppe): Suchen, die mehr wollen als das Produkt bietet
    for text in spec.get("negative_keywords", []):
        neg = op("campaign_criterion_operation")
        neg.campaign = campaign_rn
        neg.negative = True
        neg.keyword.text = text
        neg.keyword.match_type = c.enums.KeywordMatchTypeEnum.PHRASE

    g = op("ad_group_operation")
    g.resource_name = group_rn
    g.name = spec["ad_group"]
    g.campaign = campaign_rn
    g.status = c.enums.AdGroupStatusEnum.ENABLED
    g.type_ = c.enums.AdGroupTypeEnum.SEARCH_STANDARD
    g.cpc_bid_micros = micros(spec["max_cpc_chf"])

    for text in spec["keywords_phrase"]:
        kw = op("ad_group_criterion_operation")
        kw.ad_group = group_rn
        kw.status = c.enums.AdGroupCriterionStatusEnum.ENABLED
        kw.keyword.text = text
        kw.keyword.match_type = c.enums.KeywordMatchTypeEnum.PHRASE

    ad = op("ad_group_ad_operation")
    ad.ad_group = group_rn
    ad.status = c.enums.AdGroupAdStatusEnum.ENABLED
    ad.ad.final_urls.append(spec["final_url"])
    for text in spec["headlines"]:
        asset = c.get_type("AdTextAsset")
        asset.text = text
        ad.ad.responsive_search_ad.headlines.append(asset)
    for text in spec["descriptions"]:
        asset = c.get_type("AdTextAsset")
        asset.text = text
        ad.ad.responsive_search_ad.descriptions.append(asset)
    return ops


def cmd_create(args) -> None:
    spec = json.loads(Path(args.spec).read_text())
    errors = check_spec(spec)
    if errors:
        sys.exit("Kampagnenbeschreibung ungültig:\n  " + "\n  ".join(errors))
    c = client()
    request = c.get_type("MutateGoogleAdsRequest")
    request.customer_id = args.customer
    request.mutate_operations.extend(create_operations(c, args.customer, spec))
    request.validate_only = args.validate_only
    response = c.get_service("GoogleAdsService").mutate(request=request)
    if args.validate_only:
        print(f"gültig: {len(request.mutate_operations)} Operationen, nichts angelegt")
        return
    for r in response.mutate_operation_responses:
        for field in ("campaign_result", "ad_group_result", "campaign_budget_result"):
            if r._pb.HasField(field):
                print(f"angelegt: {getattr(r, field).resource_name}")


def set_status(args, status: str) -> None:
    c = client()
    ops = []
    for cid in args.ids:
        o = c.get_type("CampaignOperation")
        o.update.resource_name = c.get_service("CampaignService").campaign_path(args.customer, cid)
        o.update.status = getattr(c.enums.CampaignStatusEnum, status)
        o.update_mask.paths.append("status")
        ops.append(o)
    for r in c.get_service("CampaignService").mutate_campaigns(customer_id=args.customer, operations=ops).results:
        print(f"{status}: {r.resource_name}")


def keyword_lines(lines) -> list[str]:
    """Keywords aus einer Datei: eines pro Zeile, # für Kommentare, Gross/Klein egal, jedes nur einmal."""
    seen, out = set(), []
    for line in lines:
        text = line.strip().lower()
        if text and not text.startswith("#") and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def cmd_keywords(args) -> None:
    """Suchvolumen und Klickpreise aus dem Keyword-Planer (braucht API-Zugriffsebene Basic)."""
    source = sys.stdin if args.file == "-" else open(args.file, encoding="utf-8")
    keywords = keyword_lines(source)
    c = client()
    request = c.get_type("GenerateKeywordHistoricalMetricsRequest")
    request.customer_id = args.customer
    request.keywords.extend(keywords)
    request.language = args.language
    request.geo_target_constants.append(args.geo)
    request.keyword_plan_network = c.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    rows = []
    for r in c.get_service("KeywordPlanIdeaService").generate_keyword_historical_metrics(request=request).results:
        m = r.keyword_metrics
        rows.append((m.avg_monthly_searches, r.text, m.competition.name,
                     m.low_top_of_page_bid_micros / 1e6, m.high_top_of_page_bid_micros / 1e6))
    print("Suchen/Monat\tWettbewerb\tCPC tief-hoch CHF\tKeyword")
    for searches, text, comp, low, high in sorted(rows, reverse=True):
        print(f"{searches}\t{comp}\t{low:.2f}-{high:.2f}\t{text}")


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
    s = sub.add_parser("create")
    s.add_argument("spec", help="JSON-Datei mit Kampagne, Budget, Keywords und Anzeige")
    s.add_argument("--validate-only", action="store_true", help="nur von Google prüfen lassen, nichts anlegen")
    s.set_defaults(fn=cmd_create)
    s = sub.add_parser("keywords")
    s.add_argument("file", help="Datei mit einem Keyword pro Zeile, - für stdin")
    s.add_argument("--geo", default="geoTargetConstants/2756", help="Standard Schweiz")
    s.add_argument("--language", default="languageConstants/1001", help="Standard Deutsch")
    s.set_defaults(fn=cmd_keywords)
    for name, status in (("enable", "ENABLED"), ("pause", "PAUSED")):
        s = sub.add_parser(name)
        s.add_argument("ids", nargs="+")
        s.set_defaults(fn=lambda a, st=status: set_status(a, st))
    args = p.parse_args(argv)
    if args.cmd not in ("login", "customers") and not args.customer:
        p.error("--customer fehlt (oder GOOGLE_ADS_CUSTOMER_ID setzen)")
    args.fn(args)


if __name__ == "__main__":
    main()
