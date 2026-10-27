#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12,<3.15"
# dependencies = ["faster-whisper>=1.2", "av<19"]
# ///
"""
sprachnachricht: Telegram-Sprachnachricht lokal mit faster-whisper umschreiben, nur Deutsch (Goran) oder Serbisch
(Vesna). Gibt «de: …» oder «sr: …» aus.

  sprachnachricht.py ~/.claude/channels/telegram/inbox/<datei>.oga [--genau]

Standard ist SCHNELL (rund 3 s); --genau nimmt GENAU (rund 12 s), wenn der Text aus dem Zusammenhang nicht klar
wird. Whisper hält Serbisch oft für Kroatisch oder Bosnisch, das zählt als Serbisch; jede andere erkannte Sprache wird
der wahrscheinlicheren von beiden zugeschlagen. `av<19`, weil faster-whisper 1.2.1 `metadata_errors` übergibt, das
av 19 nicht mehr kennt (behoben in SYSTRAN/faster-whisper#1589, noch nicht veröffentlicht).
"""
import argparse

SCHNELL = "Systran/faster-whisper-small"
GENAU = "Systran/faster-whisper-large-v3"
SERBISCH = {"sr", "hr", "bs"}


def laden(name):
    from faster_whisper import WhisperModel

    return WhisperModel(name, device="cpu", compute_type="int8")


def dekodieren(pfad):
    from faster_whisper import decode_audio

    return decode_audio(pfad)


def sprache_waehlen(wahrscheinlichkeiten):
    de = sum(p for s, p in wahrscheinlichkeiten if s == "de")
    sr = sum(p for s, p in wahrscheinlichkeiten if s in SERBISCH)
    return "sr" if sr > de else "de"


def umschreiben(pfad, genau=False, laden=laden, dekodieren=dekodieren):
    modell = laden(GENAU if genau else SCHNELL)
    audio = dekodieren(pfad)
    _, _, alle = modell.detect_language(audio)
    sprache = sprache_waehlen(alle)
    segmente, _ = modell.transcribe(audio, language=sprache)
    return sprache, " ".join(s.text.strip() for s in segmente)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("datei")
    p.add_argument("--genau", action="store_true", help=f"{GENAU} statt {SCHNELL}")
    a = p.parse_args()
    sprache, text = umschreiben(a.datei, genau=a.genau)
    print(f"{sprache}: {text}")


if __name__ == "__main__":
    main()
