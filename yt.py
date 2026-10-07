#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["google-api-python-client>=2.150", "google-auth-oauthlib>=1.2"]
# ///
"""
yt: YouTube-Kanal aus der Kommandozeile (YouTube Data API v3), ohne YouTube Studio.

Zugang: derselbe OAuth-Client (Typ Desktop) wie `gsc` und `ads`, Datei ~/.config/google-ads/client_secret.json;
eigener Login mit dem Scope `youtube.force-ssl`, Refresh-Token in ~/.config/youtube/token.json (Modus 600, nie in ein
Repo). Die YouTube Data API v3 ist im Cloud-Projekt des Clients eingeschaltet (`gcloud services enable
youtube.googleapis.com`). Kontingent 10'000 Einheiten pro Tag: list 1, update 50, upload 1600.

Befehle:
    yt login [--no-browser]                         OAuth im Browser, speichert den Refresh-Token
    yt videos [--channel ID]                        alle Videos des Kanals (auch privat und Entwurf) mit Sichtbarkeit
    yt get VIDEO-ID                                 Titel, Beschreibung, Tags, Sichtbarkeit als JSON
    yt update VIDEO-ID [--title …] [--description-file DATEI] [--tags "a,b,c"] [--language de] [--privacy private|unlisted|public]
    yt upload DATEI --title … [--description-file DATEI] [--tags …] [--language de] [--privacy private] [--thumbnail BILD]
Kanal: --channel oder Umgebungsvariable YT_CHANNEL, Standard strainovic-it (UCejZg-WBrGzth2W-sLYCNzA). Der Login
läuft über Gorans Google-Konto; die API wählt den Kanal über `onBehalfOfContentOwner` nicht, darum beim Hochladen
prüfen, dass der Kanal stimmt (`yt videos` zeigt den Kanal der Liste).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CLIENT_SECRET = Path.home() / ".config" / "google-ads" / "client_secret.json"
CONFIG_DIR = Path.home() / ".config" / "youtube"
TOKEN = CONFIG_DIR / "token.json"
SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
DEFAULT_CHANNEL = os.environ.get("YT_CHANNEL", "UCejZg-WBrGzth2W-sLYCNzA")


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
        sys.exit(f"kein Token, zuerst `yt login` ({TOKEN})")
    creds = Credentials.from_authorized_user_file(str(TOKEN), [SCOPE])
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def uploads_playlist(svc, channel: str) -> str:
    r = svc.channels().list(part="contentDetails,snippet", id=channel).execute()
    items = r.get("items", [])
    if not items:
        sys.exit(f"Kanal {channel} nicht gefunden oder kein Zugriff")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def cmd_videos(args) -> None:
    svc = service()
    playlist = uploads_playlist(svc, args.channel)
    ids: list[str] = []
    token = None
    while True:
        r = svc.playlistItems().list(part="contentDetails", playlistId=playlist, maxResults=50, pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    print("ID\tSichtbarkeit\tStatus\tDatum\tTitel")
    for start in range(0, len(ids), 50):
        r = svc.videos().list(part="snippet,status", id=",".join(ids[start:start + 50])).execute()
        for v in r.get("items", []):
            s, st = v["snippet"], v["status"]
            print(f"{v['id']}\t{st.get('privacyStatus')}\t{st.get('uploadStatus')}\t{s.get('publishedAt', '')[:10]}\t{s.get('title')}")


def cmd_get(args) -> None:
    r = service().videos().list(part="snippet,status", id=args.id).execute()
    items = r.get("items", [])
    if not items:
        sys.exit(f"Video {args.id} nicht gefunden")
    v = items[0]
    out = {k: v["snippet"].get(k) for k in ("title", "description", "tags", "defaultLanguage", "categoryId")}
    out["privacyStatus"] = v["status"].get("privacyStatus")
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_update(args) -> None:
    svc = service()
    r = svc.videos().list(part="snippet,status", id=args.id).execute()
    items = r.get("items", [])
    if not items:
        sys.exit(f"Video {args.id} nicht gefunden")
    v = items[0]
    snippet = {k: v["snippet"][k] for k in ("title", "description", "categoryId") if k in v["snippet"]}
    if "tags" in v["snippet"]:
        snippet["tags"] = v["snippet"]["tags"]
    if "defaultLanguage" in v["snippet"]:
        snippet["defaultLanguage"] = v["snippet"]["defaultLanguage"]
    if args.title:
        snippet["title"] = args.title
    if args.description_file:
        snippet["description"] = Path(args.description_file).read_text().rstrip("\n")
    if args.tags is not None:
        snippet["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.language:
        snippet["defaultLanguage"] = args.language
    if len(snippet["title"]) > 100:
        sys.exit(f"Titel hat {len(snippet['title'])} Zeichen, erlaubt sind 100")
    body = {"id": args.id, "snippet": snippet}
    parts = "snippet"
    if args.privacy:
        body["status"] = {"privacyStatus": args.privacy}
        parts = "snippet,status"
    svc.videos().update(part=parts, body=body).execute()
    print(f"aktualisiert: {args.id} ({snippet['title']})")


def cmd_upload(args) -> None:
    from googleapiclient.http import MediaFileUpload
    svc = service()
    snippet = {"title": args.title, "categoryId": args.category}
    if args.description_file:
        snippet["description"] = Path(args.description_file).read_text().rstrip("\n")
    if args.tags:
        snippet["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.language:
        snippet["defaultLanguage"] = args.language
    if len(snippet["title"]) > 100:
        sys.exit(f"Titel hat {len(snippet['title'])} Zeichen, erlaubt sind 100")
    body = {"snippet": snippet, "status": {"privacyStatus": args.privacy, "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(args.file, chunksize=8 * 1024 * 1024, resumable=True)
    request = svc.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _status, response = request.next_chunk()
    vid = response["id"]
    if args.thumbnail:
        svc.thumbnails().set(videoId=vid, media_body=MediaFileUpload(args.thumbnail)).execute()
    print(f"hochgeladen: {vid} https://youtu.be/{vid} ({args.privacy})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--channel", default=DEFAULT_CHANNEL)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("login"); s.add_argument("--no-browser", action="store_true"); s.set_defaults(fn=cmd_login)
    s = sub.add_parser("videos"); s.set_defaults(fn=cmd_videos)
    s = sub.add_parser("get"); s.add_argument("id"); s.set_defaults(fn=cmd_get)
    s = sub.add_parser("update"); s.add_argument("id"); s.add_argument("--title"); s.add_argument("--description-file")
    s.add_argument("--tags"); s.add_argument("--language"); s.add_argument("--privacy", choices=["private", "unlisted", "public"])
    s.set_defaults(fn=cmd_update)
    s = sub.add_parser("upload"); s.add_argument("file"); s.add_argument("--title", required=True)
    s.add_argument("--description-file"); s.add_argument("--tags"); s.add_argument("--language")
    s.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    s.add_argument("--category", default="28", help="YouTube-Kategorie, 28 = Wissenschaft & Technik")
    s.add_argument("--thumbnail"); s.set_defaults(fn=cmd_upload)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
