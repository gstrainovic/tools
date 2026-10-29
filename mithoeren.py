#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["httpx>=0.28"]
# ///
"""
mithoeren: Live-Umschrift eines Online-Meetings (Teams, Zoom, Meet) in eine wachsende Textdatei, die Claude Code per
Monitor (`tail -f`) mitliest und daraus Hinweise gibt. Mikrofon = Goran, Lautsprecher-Monitor = Gegenüber.

  mithoeren.py ~/projects/<repo>/meeting-live.txt --ton ~/Dokumente/aufnahme-kunde.ogg --gegenueber Kunde \
    --begriffe Firmenname,Produkt

ffmpeg schneidet beide Seiten in Stücke von SEGMENT_S Sekunden, die zu Sätzen bis zur nächsten Sprechpause (höchstens
MAX_S) zusammenkommen; Voxtral Mini Transcribe (Mistral, EU, USD 0.003 je Minute) schreibt jeden Satz mit Sprache «de»
und Begriffsliste um; Stille geht nicht an Voxtral. Erfahrungen aus
ki-tel (plan-sprachbot.md, Schritt 1): Voxtral Batch mit `context_bias` trifft Schweizerdeutsch und Produktnamen,
faster-whisper `small` nicht. Die Stücke werden nach der Umschrift gelöscht; mit --ton bleibt das ganze Gespräch als
Stereo-Opus (links Goran, rechts Gegenüber), damit sich Hörfehler später an der Stelle nachhören lassen (Zeit wie im
Transkript). Die Tondatei nicht ins Repo legen. Ende mit Strg+C.

Optionen: --ton Pfad der Tondatei, --begriffe Kommaliste ohne Leerzeichen (ergänzt BEGRIFFE), --mikrofon und --lautsprecher als
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

# Stücke von 0.5 s, zu Sätzen gesammelt: Ein Satz endet nach PAUSE_S ohne Sprache, ab MIN_S schon an der ersten
# kurzen Pause, spätestens nach MAX_S. Stimmtest (Skill meeting-hilfe, «Umschrift: was gilt»):
# feste 8-s-Stücke trennten Wörter, Schnitte nach 0.5 s Pause ergaben Schnipsel, aus denen Voxtral Englisch erfand
SEGMENT_S = 0.5
PAUSE_S = 1
MIN_S = 5
MAX_S = 15
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
    s = int(index * SEGMENT_S)
    return f"{s // 60:02d}:{s % 60:02d}"


class Zustand:
    """Was zwischen zwei Durchläufen bleibt: die Stücke des angefangenen Satzes je Seite und die schon gesehenen."""

    def __init__(self):
        self.puffer = {"goran": [], "gegenueber": []}
        self.stille = {"goran": 0, "gegenueber": 0}  # Stücke ohne Sprache am Ende des Satzes
        self.erledigt = set()


def satz_senden(ordner, seite, stuecke, umschreiben):
    """Hängt die Stücke eines Satzes zu einer WAV zusammen, lässt sie umschreiben und löscht allen Ton."""
    start = int(NAME.match(stuecke[0].name)[2])
    satz = ordner / f"satz-{seite}-{start:05d}.wav"
    with wave.open(str(satz), "wb") as aus:
        aus.setnchannels(1)
        aus.setsampwidth(2)
        aus.setframerate(16000)
        for pfad in stuecke:
            try:
                with wave.open(str(pfad)) as w:
                    aus.writeframes(w.readframes(w.getnframes()))
            except (EOFError, wave.Error):  # leeres Stück vom Beenden
                pass
    try:
        text = umschreiben(satz)
    except Exception as e:
        text = f"[Umschrift fehlgeschlagen: {e}]"
    for pfad in [*stuecke, satz]:
        pfad.unlink()
    stuecke.clear()
    # eine Zeile je Satz: Gesagtes darf keine weitere Sprecherzeile vortäuschen
    return start, seite, " ".join(text.split())


def abarbeiten(ordner, ausgabe, umschreiben, zustand, gegenueber="Gegenüber", ende=False):
    """Sammelt die fertigen Stücke jeder Seite zu Sätzen und schreibt jeden Satz als «[mm:ss] Sprecher: Text» ans Ende
    von `ausgabe`, geordnet nach Zeit, Goran vor Gegenüber. Ein Satz endet mit dem ersten Stück ohne Sprache (Pause von
    mindestens SEGMENT_S), spätestens nach MAX_S, und mit `ende`. Fertig ist ein Stück, wenn dieselbe Seite schon ein
    späteres hat oder `ende` gilt; Stücke ohne Sprache ausserhalb eines Satzes gehen nie an die Umschrift."""
    teile = {}
    for pfad in ordner.iterdir():
        if m := NAME.match(pfad.name):
            teile.setdefault(m[1], []).append((int(m[2]), pfad))
    saetze = []
    max_stuecke = round(MAX_S / SEGMENT_S)
    for seite, liste in teile.items():
        letzter = max(i for i, _ in liste)
        puffer = zustand.puffer[seite]
        for index, pfad in sorted(liste):
            if pfad.name in zustand.erledigt or not (ende or index < letzter):
                continue
            zustand.erledigt.add(pfad.name)
            sprache = ist_sprache(pfad)
            if not (sprache or puffer):
                pfad.unlink()
                continue
            puffer.append(pfad)
            zustand.stille[seite] = 0 if sprache else zustand.stille[seite] + 1
            pause = zustand.stille[seite] * SEGMENT_S
            if (len(puffer) >= max_stuecke or pause >= PAUSE_S
                    or (pause and len(puffer) * SEGMENT_S >= MIN_S + SEGMENT_S)):
                saetze.append(satz_senden(ordner, seite, puffer, umschreiben))
                zustand.stille[seite] = 0
    if ende:
        saetze += [satz_senden(ordner, seite, puffer, umschreiben)
                   for seite, puffer in zustand.puffer.items() if puffer]
    with ausgabe.open("a") as aus:
        for index, seite, text in sorted(saetze, key=lambda s: (s[0], s[1] != "goran")):
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


def aufnahme(ordner, mikrofon, lautsprecher, ton=None, eingabe="pulse"):
    """Stücke beider Seiten für die Umschrift; mit `ton` dazu das ganze Gespräch als Opus, links Goran, rechts
    Gegenüber, Zeit gleich wie im Transkript (wie die Aufnahme vom 05.10.)."""
    stueck = ["-f", "segment", "-segment_time", str(SEGMENT_S), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le"]
    befehl = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", eingabe, "-i", mikrofon, "-f", eingabe, "-i",
              lautsprecher, "-filter_complex",
              "[0:a]aformat=channel_layouts=mono,asplit[g][g2];[1:a]aformat=channel_layouts=mono,asplit[c][c2];"
              "[g2][c2]join=inputs=2:channel_layout=stereo[st]",
              "-map", "[g]", *stueck, str(ordner / "goran-%05d.wav"),
              "-map", "[c]", *stueck, str(ordner / "gegenueber-%05d.wav")]
    if ton:
        befehl += ["-map", "[st]", "-c:a", "libopus", "-b:a", "64k", str(ton)]
    else:
        befehl += ["-map", "[st]", "-f", "null", "-"]
    return subprocess.Popen(befehl, stdin=subprocess.DEVNULL)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ausgabe", type=Path)
    p.add_argument("--gegenueber", default="Gegenüber")
    p.add_argument("--begriffe", default="")
    p.add_argument("--ton", type=Path)
    p.add_argument("--mikrofon", default="@DEFAULT_SOURCE@")
    p.add_argument("--lautsprecher", default="@DEFAULT_MONITOR@")
    a = p.parse_args()
    ordner = a.ausgabe.with_name(a.ausgabe.name + ".teile")
    ordner.mkdir(parents=True, exist_ok=True)
    umschreiben = voxtral(",".join(filter(None, [BEGRIFFE, a.begriffe])))
    ffmpeg = aufnahme(ordner, a.mikrofon, a.lautsprecher, a.ton)
    print(f"Umschrift läuft nach {a.ausgabe}, Ende mit Strg+C", file=sys.stderr)
    zustand = Zustand()
    # kill ohne -INT soll ebenso sauber enden wie Strg+C
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        while ffmpeg.poll() is None:
            abarbeiten(ordner, a.ausgabe, umschreiben, zustand, a.gegenueber)
            time.sleep(0.25)
        print(f"ffmpeg beendet (Code {ffmpeg.returncode})", file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        ffmpeg.terminate()
        ffmpeg.wait()
    abarbeiten(ordner, a.ausgabe, umschreiben, zustand, a.gegenueber, ende=True)
    for rest in ordner.iterdir():  # leere Stücke, die ffmpeg beim Beenden noch angelegt hat
        rest.unlink()
    ordner.rmdir()


if __name__ == "__main__":
    main()
