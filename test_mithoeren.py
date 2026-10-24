import importlib.util
import math
import random
import struct
import tempfile
import unittest
import wave
from pathlib import Path

spec = importlib.util.spec_from_file_location("mithoeren", Path(__file__).with_name("mithoeren.py"))
mithoeren = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mithoeren)


def wav(pfad, laut, rauschen=0):
    """1 s Mono 16 kHz mit gleichmässigem Rauschen (Amplitude `rauschen`); `laut` legt Silben darüber: 300 ms Sinus mit
    −20 dBFS, 200 ms Pause, wie Sprache mit grossem Abstand zwischen leisen und lauten Stellen."""
    zufall = random.Random(1)
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(
            struct.pack("<h", int((3277 if laut and i % 8000 < 4800 else 0) * math.sin(2 * math.pi * 440 * i / 16000)
                                  + zufall.uniform(-rauschen, rauschen)))
            for i in range(16000)))


class Abarbeiten(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp())
        self.ausgabe = self.ordner / "transkript.txt"
        self.gesendet = []

    def umschreiben(self, pfad):
        self.gesendet.append(pfad.name)
        return f"Text aus {pfad.name}"

    def test_fertige_segmente_beider_seiten_landen_zeitlich_geordnet_im_transkript(self):
        for name in ("gegenueber-00000.wav", "goran-00000.wav", "goran-00001.wav", "gegenueber-00001.wav"):
            wav(self.ordner / name, laut=True)
        erledigt = set()
        mithoeren.abarbeiten(self.ordner, self.ausgabe, self.umschreiben, erledigt, gegenueber="Kunde")
        # Das jeweils letzte Segment schreibt ffmpeg noch, es bleibt liegen
        self.assertEqual(self.ausgabe.read_text().splitlines(), [
            "[00:00] Goran: Text aus goran-00000.wav",
            "[00:00] Kunde: Text aus gegenueber-00000.wav",
        ])
        for name in ("goran-00002.wav", "gegenueber-00002.wav"):
            wav(self.ordner / name, laut=True)
        mithoeren.abarbeiten(self.ordner, self.ausgabe, self.umschreiben, erledigt, gegenueber="Kunde")
        self.assertEqual(self.ausgabe.read_text().splitlines()[2:], [
            f"[00:{mithoeren.SEGMENT_S:02d}] Goran: Text aus goran-00001.wav",
            f"[00:{mithoeren.SEGMENT_S:02d}] Kunde: Text aus gegenueber-00001.wav",
        ])
        self.assertEqual(len(self.gesendet), 4, "kein Segment doppelt an Voxtral")

    def test_stille_geht_nicht_an_voxtral_und_nicht_ins_transkript(self):
        wav(self.ordner / "goran-00000.wav", laut=False)
        wav(self.ordner / "goran-00001.wav", laut=True)
        mithoeren.abarbeiten(self.ordner, self.ausgabe, self.umschreiben, set(), ende=True)
        self.assertEqual(self.gesendet, ["goran-00001.wav"])
        self.assertEqual(self.ausgabe.read_text().splitlines(),
                         [f"[00:{mithoeren.SEGMENT_S:02d}] Goran: Text aus goran-00001.wav"])

    def test_rauschen_des_laptop_mikrofons_gilt_als_stille(self):
        # Gemessen 24.10.: internes Mikrofon ohne Sprache um −43 dBFS, Voxtral macht daraus russische Fantasiesätze
        wav(self.ordner / "goran-00000.wav", laut=False, rauschen=400)
        wav(self.ordner / "goran-00001.wav", laut=True, rauschen=400)
        mithoeren.abarbeiten(self.ordner, self.ausgabe, self.umschreiben, set(), ende=True)
        self.assertEqual(self.gesendet, ["goran-00001.wav"])

    def test_leeres_stueck_vom_beenden_bricht_nicht_ab(self):
        (self.ordner / "goran-00000.wav").write_bytes(b"")
        mithoeren.abarbeiten(self.ordner, self.ausgabe, self.umschreiben, set(), ende=True)
        self.assertEqual(self.gesendet, [])

    def test_am_ende_kommt_auch_das_letzte_segment_dran(self):
        wav(self.ordner / "gegenueber-00000.wav", laut=True)
        mithoeren.abarbeiten(self.ordner, self.ausgabe, self.umschreiben, set(), ende=True)
        self.assertEqual(self.ausgabe.read_text().splitlines(), ["[00:00] Gegenüber: Text aus gegenueber-00000.wav"])

    def test_fehler_der_umschrift_steht_im_transkript_statt_abzubrechen(self):
        wav(self.ordner / "goran-00000.wav", laut=True)

        def kaputt(pfad):
            raise RuntimeError("Voxtral 503")

        mithoeren.abarbeiten(self.ordner, self.ausgabe, kaputt, set(), ende=True)
        self.assertEqual(self.ausgabe.read_text().splitlines(), ["[00:00] Goran: [Umschrift fehlgeschlagen: Voxtral 503]"])


if __name__ == "__main__":
    unittest.main()
