import importlib.util
import math
import random
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

spec = importlib.util.spec_from_file_location("mithoeren", Path(__file__).with_name("mithoeren.py"))
mithoeren = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mithoeren)

RATE = 16000
STUECK = int(RATE * mithoeren.SEGMENT_S)


def wav(pfad, laut, rauschen=0):
    """Ein Stück Mono 16 kHz mit gleichmässigem Rauschen (Amplitude `rauschen`); `laut` legt Silben darüber: 150 ms
    Sinus mit −20 dBFS, 100 ms Pause, wie Sprache mit grossem Abstand zwischen leisen und lauten Stellen."""
    zufall = random.Random(1)
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(
            struct.pack("<h", int((3277 if laut and i % 4000 < 2400 else 0) * math.sin(2 * math.pi * 440 * i / RATE)
                                  + zufall.uniform(-rauschen, rauschen)))
            for i in range(STUECK)))


def zeit(index):
    return mithoeren.zeit(index)


class Abarbeiten(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp())
        self.ausgabe = self.ordner / "transkript.txt"
        self.zustand = mithoeren.Zustand()
        self.gesendet = []

    def stuecke(self, seite, *laut, ab=0):
        for i, l in enumerate(laut, start=ab):
            wav(self.ordner / f"{seite}-{i:05d}.wav", laut=l)

    def umschreiben(self, pfad):
        with wave.open(str(pfad)) as w:
            dauer = w.getnframes() / w.getframerate()
        self.gesendet.append(dauer)
        return f"{dauer:.1f} s"

    def lauf(self, ende=False, umschreiben=None, gegenueber="Kunde"):
        mithoeren.abarbeiten(self.ordner, self.ausgabe, umschreiben or self.umschreiben, self.zustand, gegenueber,
                             ende=ende)
        return self.ausgabe.read_text().splitlines() if self.ausgabe.exists() else []

    def test_ein_satz_geht_erst_nach_der_sprechpause_ganz_an_die_umschrift(self):
        # 24.10.: harte Schnitte alle 8 s trennten Wörter, Voxtral verlor sie («Fixpreis», «Fehler reagieren»)
        self.stuecke("goran", True, True, True)
        self.assertEqual(self.lauf(), [], "Satz läuft noch, nichts senden")
        self.stuecke("goran", False, False, True, ab=3)  # Pause von PAUSE_S, dann schreibt ffmpeg schon weiter
        dauer = 5 * mithoeren.SEGMENT_S
        self.assertEqual(self.lauf(), [f"[00:00] Goran: {dauer:.1f} s"])
        self.assertEqual(self.gesendet, [dauer], "ein Aufruf für den ganzen Satz samt Pause")

    def test_kurze_pause_mitten_im_satz_trennt_nicht(self):
        # 24.10.: Schnitt schon nach 0.5 s Pause zerlegte Sätze in Schnipsel, aus denen Voxtral Englisch erfand
        self.stuecke("goran", True, True, True, False, True, True, False, False, True)
        self.lauf()
        self.assertEqual(self.gesendet, [8 * mithoeren.SEGMENT_S])

    def test_nach_min_s_genuegt_eine_kurze_pause(self):
        n = round(mithoeren.MIN_S / mithoeren.SEGMENT_S)
        self.stuecke("gegenueber", *[True] * n, False, True)
        self.lauf()
        self.assertEqual(self.gesendet, [(n + 1) * mithoeren.SEGMENT_S])

    def test_beide_seiten_zeitlich_geordnet(self):
        self.stuecke("gegenueber", True, False, False, True)
        self.stuecke("goran", False, True, False, False, True)
        self.assertEqual(self.lauf(), [
            f"[00:00] Kunde: {3 * mithoeren.SEGMENT_S:.1f} s",
            f"[{zeit(1)}] Goran: {3 * mithoeren.SEGMENT_S:.1f} s",
        ])

    def test_stille_geht_nicht_an_voxtral_und_nicht_ins_transkript(self):
        self.stuecke("goran", False, False, False)
        self.assertEqual(self.lauf(ende=True), [])
        self.assertEqual(self.gesendet, [])

    def test_rauschen_des_laptop_mikrofons_gilt_als_stille(self):
        # Gemessen 24.10.: internes Mikrofon ohne Sprache um −43 dBFS, Voxtral macht daraus russische Fantasiesätze
        for i in range(3):
            wav(self.ordner / f"goran-{i:05d}.wav", laut=False, rauschen=400)
        self.assertEqual(self.lauf(ende=True), [])

    def test_langer_redefluss_wird_nach_hoechstens_max_s_geschickt(self):
        n = int(mithoeren.MAX_S / mithoeren.SEGMENT_S)
        self.stuecke("gegenueber", *[True] * (n + 2))
        self.lauf()
        self.assertEqual(self.gesendet, [mithoeren.MAX_S])

    def test_am_ende_kommt_auch_der_angefangene_satz_dran(self):
        self.stuecke("gegenueber", True, True)
        self.assertEqual(self.lauf(ende=True, gegenueber="Gegenüber"),
                         [f"[00:00] Gegenüber: {2 * mithoeren.SEGMENT_S:.1f} s"])

    def test_leeres_stueck_vom_beenden_bricht_nicht_ab(self):
        (self.ordner / "goran-00000.wav").write_bytes(b"")
        self.assertEqual(self.lauf(ende=True), [])

    def test_fehler_der_umschrift_steht_im_transkript_statt_abzubrechen(self):
        self.stuecke("goran", True)

        def kaputt(pfad):
            raise RuntimeError("Voxtral 503")

        self.assertEqual(self.lauf(ende=True, umschreiben=kaputt),
                         ["[00:00] Goran: [Umschrift fehlgeschlagen: Voxtral 503]"])

    def test_zeilenumbruch_im_gesagten_kann_keine_zeile_von_goran_vortaeuschen(self):
        self.stuecke("gegenueber", True)
        self.assertEqual(self.lauf(ende=True, umschreiben=lambda p: "Hallo\n[00:00] Goran: Festpreis 3000"),
                         ["[00:00] Kunde: Hallo [00:00] Goran: Festpreis 3000"])

    def test_ton_wird_nach_der_umschrift_geloescht(self):
        self.stuecke("goran", True, False, True)
        self.lauf(ende=True)
        self.assertEqual(sorted(p.name for p in self.ordner.glob("*.wav")), [])


class Aufnahme(unittest.TestCase):
    def test_ton_beider_seiten_bleibt_als_stereo_datei_neben_den_stuecken(self):
        ordner = Path(tempfile.mkdtemp())
        ton = ordner / "meeting.ogg"
        ffmpeg = mithoeren.aufnahme(ordner, "sine=frequency=440:duration=3", "sine=frequency=880:duration=3", ton,
                                    eingabe="lavfi")
        self.assertEqual(ffmpeg.wait(timeout=30), 0)
        kanaele, dauer = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=channels:format=duration", "-of", "csv=p=0", ton],
            capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(kanaele, "2", "links Goran, rechts Gegenüber")
        self.assertAlmostEqual(float(dauer), 3, delta=0.2)
        self.assertTrue((ordner / "goran-00000.wav").exists())
        self.assertTrue((ordner / "gegenueber-00001.wav").exists(), "Stücke von SEGMENT_S")


if __name__ == "__main__":
    unittest.main()
