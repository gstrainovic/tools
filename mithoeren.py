#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["httpx>=0.28"]
# ///
"""
mithoeren: Live-Umschrift eines Online-Meetings (Teams, Zoom, Meet) in eine wachsende Textdatei, die Claude Code per
Monitor (`tail -f`) mitliest und daraus Hinweise gibt. Mikrofon = Goran, Lautsprecher-Monitor = Gegenüber.

  mithoeren.py ~/projects/<repo>/meeting-live.txt --gegenueber Kunde --begriffe Firmenname,Produkt

ffmpeg schneidet beide Seiten in Stücke von SEGMENT_S Sekunden, Voxtral Mini Transcribe (Mistral, EU, USD 0.003 je
Minute) schreibt jedes Stück mit Sprache «de» und Begriffsliste um; Stille geht nicht an Voxtral. Erfahrungen aus
ki-tel (plan-sprachbot.md, Schritt 1): Voxtral Batch mit `context_bias` trifft Schweizerdeutsch und Produktnamen,
faster-whisper `small` nicht. Ton wird nicht aufbewahrt, jedes Stück nach der Umschrift gelöscht. Ende mit Strg+C.

Optionen: --begriffe Kommaliste ohne Leerzeichen (ergänzt BEGRIFFE), --mikrofon und --lautsprecher als
Pulse-Quellen (Standard @DEFAULT_SOURCE@ und @DEFAULT_MONITOR@, Liste mit `pactl list short sources`).
Schlüssel: MISTRAL_API_KEY oder ~/projects/ki-tel/.secrets/mistral.env.
"""
import argparse
import array
import math
import os
import re
import signal
import subprocess
import sys
import time
import wave
from pathlib import Path

SEGMENT_S = 8
STILLE_DBFS = -50
SPRACHE_ABSTAND_DB = 15
URL = "https://api.mistral.ai/v1/audio/transcriptions"
MODELL = "voxtral-mini-2602"
# Mistral lehnt Begriffe mit Leerzeichen oder Komma ab (ki-tel whatsapp_demo/app.py)
BEGRIFFE = "Strainovic,bexio,HubSpot,Make,n8n,QR-Rechnung,Marketplace"
SCHLUESSEL = Path.home() / "projects/ki-tel/.secrets/mistral.env"
NAME = re.compile(r"(goran|gegenueber)-(\d+)\.wav$")


def ist_sprache(pfad):
    """Sprache wechselt zwischen lauten Silben und leisen Pausen, Rauschen bleibt gleichmässig. Gemessen 24.10. in
    20-ms-Fenstern: Abstand 90. zu 10. Perzentil bei Sprache 44–65 dB, beim rauschenden Laptop-Mikrofon 6–7 dB."""
    try:
        with wave.open(str(pfad)) as w:
            proben = array.array("h", w.readframes(w.getnframes()))
    except (EOFError, wave.Error):  # leeres Stück, das ffmpeg beim Beenden noch angelegt hat
        return False
    n = w.getframerate() // 50
    pegel = sorted(20 * math.log10(max(1.0, math.sqrt(sum(p * p for p in proben[i:i + n]) / n)) / 32768)
                   for i in range(0, len(proben) - n + 1, n))
    if not pegel:
        return False
    oben, unten = pegel[int(0.9 * (len(pegel) - 1))], pegel[int(0.1 * (len(pegel) - 1))]
    return oben > STILLE_DBFS and oben - unten >= SPRACHE_ABSTAND_DB


def zeit(index):
    s = index * SEGMENT_S
    return f"{s // 60:02d}:{s % 60:02d}"


def abarbeiten(ordner, ausgabe, umschreiben, erledigt, gegenueber="Gegenüber", ende=False):
    """Schreibt jedes fertige, nicht stille Segment als «[mm:ss] Sprecher: Text» ans Ende von `ausgabe`, geordnet nach
    Zeit, Goran vor Gegenüber. Fertig ist ein Segment, wenn dieselbe Seite schon ein späteres hat oder `ende` gilt."""
    teile = {}
    for pfad in ordner.iterdir():
        if m := NAME.match(pfad.name):
            teile.setdefault(m[1], []).append((int(m[2]), pfad))
    fertig = []
    for seite, liste in teile.items():
        letzter = max(i for i, _ in liste)
        fertig += [(i, seite != "goran", seite, p) for i, p in liste
                   if p.name not in erledigt and (ende or i < letzter)]
    with ausgabe.open("a") as aus:
        for index, _, seite, pfad in sorted(fertig):
            erledigt.add(pfad.name)
            if not ist_sprache(pfad):
                pfad.unlink()
                continue
            try:
                text = umschreiben(pfad)
            except Exception as e:
                text = f"[Umschrift fehlgeschlagen: {e}]"
            pfad.unlink()
            # eine Zeile je Stück: Gesagtes darf keine weitere Sprecherzeile vortäuschen
            text = " ".join(text.split())
            if text:
                aus.write(f"[{zeit(index)}] {'Goran' if seite == 'goran' else gegenueber}: {text}\n")
                aus.flush()


def schluessel():
    if k := os.environ.get("MISTRAL_API_KEY"):
        return k
    for zeile in SCHLUESSEL.read_text().splitlines():
        if zeile.startswith("MISTRAL_API_KEY="):
            return zeile.split("=", 1)[1].strip().strip('"')
    sys.exit(f"MISTRAL_API_KEY fehlt (Umgebung oder {SCHLUESSEL})")


def voxtral(begriffe):
    import httpx
    client = httpx.Client(timeout=30, headers={"Authorization": f"Bearer {schluessel()}"})

    def umschreiben(pfad):
        r = client.post(URL, data={"model": MODELL, "language": "de", "context_bias": begriffe},
                        files={"file": (pfad.name, pfad.read_bytes(), "audio/wav")})
        if r.is_error:
            raise RuntimeError(f"Voxtral {r.status_code}: {r.text[:200]}")
        return r.json()["text"].strip()

    return umschreiben


def aufnahme(ordner, mikrofon, lautsprecher):
    stueck = ["-f", "segment", "-segment_time", str(SEGMENT_S), "-ar", "16000", "-ac", "1"]
    return subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "pulse", "-i", mikrofon, "-f", "pulse", "-i",
         lautsprecher, "-map", "0:a", *stueck, str(ordner / "goran-%05d.wav"),
         "-map", "1:a", *stueck, str(ordner / "gegenueber-%05d.wav")],
        stdin=subprocess.DEVNULL)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ausgabe", type=Path)
    p.add_argument("--gegenueber", default="Gegenüber")
    p.add_argument("--begriffe", default="")
    p.add_argument("--mikrofon", default="@DEFAULT_SOURCE@")
    p.add_argument("--lautsprecher", default="@DEFAULT_MONITOR@")
    a = p.parse_args()
    ordner = a.ausgabe.with_name(a.ausgabe.name + ".teile")
    ordner.mkdir(parents=True, exist_ok=True)
    umschreiben = voxtral(",".join(filter(None, [BEGRIFFE, a.begriffe])))
    ffmpeg = aufnahme(ordner, a.mikrofon, a.lautsprecher)
    print(f"Umschrift läuft nach {a.ausgabe}, Ende mit Strg+C", file=sys.stderr)
    erledigt = set()
    # kill ohne -INT soll ebenso sauber enden wie Strg+C
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        while ffmpeg.poll() is None:
            abarbeiten(ordner, a.ausgabe, umschreiben, erledigt, a.gegenueber)
            time.sleep(1)
        print(f"ffmpeg beendet (Code {ffmpeg.returncode})", file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        ffmpeg.terminate()
        ffmpeg.wait()
    abarbeiten(ordner, a.ausgabe, umschreiben, erledigt, a.gegenueber, ende=True)
    for rest in ordner.iterdir():  # leere Stücke, die ffmpeg beim Beenden noch angelegt hat
        rest.unlink()
    ordner.rmdir()


if __name__ == "__main__":
    main()
