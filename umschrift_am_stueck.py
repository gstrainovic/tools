#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["httpx>=0.28"]
# ///
"""
umschrift-am-stueck: Tondatei eines Meetings je Kanal am Stück mit Voxtral umschreiben (trifft mehr als die
Live-Umschrift von mithoeren, Skill meeting-hilfe). Erwartet einen Ordner mit Stücken `<seite>-NN.ogg` (Seite
etwa goran, christoph; NN ab 00, je STUECK_S Sekunden), wie ffmpeg sie mit `-f segment -segment_time 600` schreibt:

  ffmpeg -i aufnahme.ogg -filter_complex "[0:a]pan=mono|c0=c0[g];[0:a]pan=mono|c0=c1[c]" \\
    -map "[g]" -c:a libopus -b:a 32k -f segment -segment_time 600 kanal/goran-%02d.ogg \\
    -map "[c]" -c:a libopus -b:a 32k -f segment -segment_time 600 kanal/kunde-%02d.ogg
  umschrift-am-stueck kanal transkript-batch.txt --begriffe <Firma>,<Produkte>,<Namen>

Ausgabe: Zeilen `[mm:ss] Seite: Text`, beide Seiten nach Zeit sortiert. Kundennamen nur per --begriffe, nie hier.
Schlüssel: MISTRAL_API_KEY oder ~/projects/ki-tel/.secrets/mistral.env.
"""
import argparse
import os
import re
import sys
from pathlib import Path

import httpx

URL = "https://api.mistral.ai/v1/audio/transcriptions"
MODELL = "voxtral-mini-2602"
BEGRIFFE = "Strainovic,bexio,HubSpot,Make,n8n,QR-Rechnung,Marketplace"
STUECK_S = 600
NAME = re.compile(r"([^-]+)-(\d+)\.ogg$")


def schluessel():
    if os.environ.get("MISTRAL_API_KEY"):
        return os.environ["MISTRAL_API_KEY"]
    for zeile in (Path.home() / "projects/ki-tel/.secrets/mistral.env").read_text().splitlines():
        if zeile.startswith("MISTRAL_API_KEY="):
            return zeile.split("=", 1)[1].strip().strip('"')
    raise SystemExit("kein Mistral-Schlüssel")


def zeilen_aus(antwort, seite, versatz):
    segmente = antwort.get("segments") or [{"start": 0, "text": antwort.get("text", "")}]
    for s in segmente:
        text = s.get("text", "").strip()
        if text:
            t = versatz + float(s.get("start", 0))
            yield t, f"[{int(t) // 60:02d}:{int(t) % 60:02d}] {seite.capitalize()}: {text}"


def main(argv=None):
    p = argparse.ArgumentParser(description="Tondatei je Kanal am Stück mit Voxtral umschreiben")
    p.add_argument("ordner", help="Ordner mit <seite>-NN.ogg")
    p.add_argument("ausgabe", help="Transkriptdatei")
    p.add_argument("--begriffe", default="", help="Kommaliste ohne Leerzeichen, ergänzt die festen Begriffe")
    a = p.parse_args(argv)
    begriffe = ",".join(filter(None, [BEGRIFFE, a.begriffe]))
    client = httpx.Client(timeout=300, headers={"Authorization": f"Bearer {schluessel()}"})
    zeilen = []
    for pfad in sorted(Path(a.ordner).glob("*.ogg")):
        m = NAME.match(pfad.name)
        if not m:
            continue
        seite, nr = m.groups()
        r = client.post(URL, data={"model": MODELL, "language": "de", "context_bias": begriffe,
                                   "timestamp_granularities": "segment"},
                        files={"file": (pfad.name, pfad.read_bytes(), "audio/ogg")})
        r.raise_for_status()
        neu = list(zeilen_aus(r.json(), seite, int(nr) * STUECK_S))
        zeilen.extend(neu)
        print(pfad.name, len(neu), "Zeilen", file=sys.stderr)
    zeilen.sort(key=lambda z: z[0])
    Path(a.ausgabe).write_text("\n".join(z for _, z in zeilen) + "\n")


if __name__ == "__main__":
    main()
