import importlib.util
import math
import random
import struct
import subprocess
import sys
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
        self.stuecke("goran", True, True, True, True)
        self.assertEqual(self.lauf(), [], "Satz läuft noch, nichts senden")
        self.stuecke("goran", False, False, True, ab=4)  # Pause von PAUSE_S, dann schreibt ffmpeg schon weiter
        dauer = 6 * mithoeren.SEGMENT_S
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
        self.stuecke("gegenueber", True, True, True, True, False, False, True)
        self.stuecke("goran", False, True, True, True, True, False, False, True)
        self.assertEqual(self.lauf(), [
            f"[00:00] Kunde: {6 * mithoeren.SEGMENT_S:.1f} s",
            f"[{zeit(1)}] Goran: {6 * mithoeren.SEGMENT_S:.1f} s",
        ])

    def test_kurzer_einwurf_geht_mit_dem_naechsten_satz_derselben_seite(self):
        # Meeting 29.10.2026: aus einzeln geschickten Einwürfen («Mm-hmm», «Ja, okay») erfand Voxtral fremde Sprachen
        self.stuecke("goran", True, True, False, False, False, True, True, True, True, False, False, True)
        # die Stille zwischen Einwurf und Satz über PAUSE_S hinaus fällt weg wie jede Stille ausserhalb eines Satzes
        self.assertEqual(self.lauf(), [f"[00:00] Goran: {10 * mithoeren.SEGMENT_S:.1f} s"])
        self.assertEqual(self.gesendet, [10 * mithoeren.SEGMENT_S], "Einwurf, Pause und Satz in einem Aufruf")

    def test_mehrere_einwuerfe_gehen_zusammen_sobald_sie_lang_genug_sind(self):
        n = round(mithoeren.KURZ_S / mithoeren.SEGMENT_S) // 2
        self.stuecke("gegenueber", *[True] * n, False, False, *[True] * n, False, False, True)
        self.lauf()
        self.assertEqual(self.gesendet, [(2 * n + 4) * mithoeren.SEGMENT_S])

    def test_einwurf_der_anderen_seite_wartet_nicht_auf_goran(self):
        self.stuecke("gegenueber", True, False, False, True)
        self.stuecke("goran", True, True, True, True, False, False, True)
        self.assertEqual(self.lauf(), [f"[00:00] Goran: {6 * mithoeren.SEGMENT_S:.1f} s"])

    def test_einwurf_am_ende_wird_einmal_umgeschrieben(self):
        self.stuecke("goran", True, False, False, False, False)
        self.assertEqual(self.lauf(), [])
        self.assertEqual(self.lauf(ende=True), [f"[00:00] Goran: {3 * mithoeren.SEGMENT_S:.1f} s"])
        self.assertEqual(sorted(p.name for p in self.ordner.glob("*.wav")), [])

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


class Nachher(unittest.TestCase):
    """--nachher: Tondatei je Kanal am Stück umschreiben, ffmpeg und Voxtral als Attrappen."""

    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp())
        self.ausgabe = self.ordner / "transkript-batch.txt"
        self.getrennt = []

    def trennen(self, ton, ordner):
        self.getrennt.append((ton, ordner))
        for name in ["goran-00.ogg", "goran-01.ogg", "gegenueber-00.ogg", "notiz.txt"]:
            (ordner / name).write_bytes(b"ogg")

    def umschreiben(self, pfad):
        return {
            "goran-00.ogg": {"text": "egal", "segments": [{"start": 3.2, "text": " Grüezi  mitenand "},
                                                          {"start": 70, "text": "  "}]},
            "goran-01.ogg": {"text": "Ohne Segmente am Anfang des Stücks"},
            "gegenueber-00.ogg": {"segments": [{"start": 3.2, "text": "Hallo\n[00:00] Goran: Festpreis"},
                                               {"start": 1.0, "text": "Ja"}]},
        }[pfad.name]

    def test_beide_kanaele_nach_zeit_mit_versatz_je_stueck(self):
        mithoeren.nachher(Path("aufnahme.ogg"), self.ausgabe, self.umschreiben, "Kunde", trennen=self.trennen)
        self.assertEqual(self.ausgabe.read_text().splitlines(), [
            "[00:01] Kunde: Ja",
            "[00:03] Goran: Grüezi mitenand",
            "[00:03] Kunde: Hallo [00:00] Goran: Festpreis",
            f"[{mithoeren.STUECK_S // 60:02d}:00] Goran: Ohne Segmente am Anfang des Stücks",
        ])

    def test_stuecke_liegen_nur_waehrend_der_umschrift_im_temp_ordner(self):
        mithoeren.nachher(Path("aufnahme.ogg"), self.ausgabe, self.umschreiben, trennen=self.trennen)
        ton, ordner = self.getrennt[0]
        self.assertEqual(ton, Path("aufnahme.ogg"))
        self.assertFalse(ordner.exists())

    def test_kanaltrennung_links_goran_rechts_gegenueber_in_zehn_minuten_stuecken(self):
        aufrufe = []
        alt = mithoeren.subprocess.run
        mithoeren.subprocess.run = lambda befehl, **kw: aufrufe.append((befehl, kw))
        try:
            mithoeren.kanaele_trennen(Path("a.ogg"), self.ordner)
        finally:
            mithoeren.subprocess.run = alt
        befehl, kw = aufrufe[0]
        text = " ".join(map(str, befehl))
        self.assertEqual(befehl[0], "ffmpeg")
        self.assertIn("[0:a]pan=mono|c0=c0[g];[0:a]pan=mono|c0=c1[c]", text)
        self.assertEqual(text.count(f"-segment_time {mithoeren.STUECK_S}"), 2)
        self.assertIn(str(self.ordner / "goran-%02d.ogg"), befehl)
        self.assertIn(str(self.ordner / "gegenueber-%02d.ogg"), befehl)
        self.assertTrue(kw.get("check"))

    def test_kanaltrennung_mit_echtem_ffmpeg(self):
        ton = self.ordner / "stereo.ogg"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=2", "-f", "lavfi", "-i", "sine=frequency=880:duration=2",
                        "-filter_complex", "[0:a][1:a]join=inputs=2:channel_layout=stereo", "-c:a", "libopus",
                        str(ton)], check=True, stdin=subprocess.DEVNULL)
        teile = self.ordner / "teile"
        teile.mkdir()
        mithoeren.kanaele_trennen(ton, teile)
        self.assertEqual(sorted(p.name for p in teile.iterdir()), ["gegenueber-00.ogg", "goran-00.ogg"])
        kanaele = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=channels", "-of", "csv=p=0",
                                  teile / "goran-00.ogg"], capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(kanaele, "1")


class Voxtral(unittest.TestCase):
    """Anfrage an Mistral mit falschem httpx, ohne Netz und ohne Kosten."""

    def anfragen(self, **kw):
        gesendet = []

        class Antwort:
            is_error = False

            def json(self):
                return {"text": " Hallo ", "segments": [{"start": 0, "text": "Hallo"}]}

        class Client:
            def __init__(self, **k):
                gesendet.append(("client", k))

            def post(self, url, data, files):
                gesendet.append(("post", data, files))
                return Antwort()

        falsch = type(sys)("httpx")
        falsch.Client = Client
        alt_httpx, alt_schluessel = sys.modules.get("httpx"), mithoeren.schluessel
        sys.modules["httpx"], mithoeren.schluessel = falsch, lambda: "k"
        try:
            pfad = Path(tempfile.mkdtemp()) / "goran-00.ogg"
            pfad.write_bytes(b"ogg")
            ergebnis = mithoeren.voxtral("A,B", **kw)(pfad)
        finally:
            mithoeren.schluessel = alt_schluessel
            if alt_httpx:
                sys.modules["httpx"] = alt_httpx
            else:
                del sys.modules["httpx"]
        return ergebnis, gesendet

    def test_nachher_verlangt_segmente_und_liefert_die_ganze_antwort(self):
        ergebnis, gesendet = self.anfragen(nachher=True)
        _, data, files = gesendet[1]
        self.assertEqual(data["timestamp_granularities"], "segment")
        self.assertEqual(data["context_bias"], "A,B")
        self.assertEqual(files["file"][2], "audio/ogg")
        self.assertEqual(ergebnis["segments"], [{"start": 0, "text": "Hallo"}])

    def test_live_bleibt_beim_text_ohne_segmente(self):
        ergebnis, gesendet = self.anfragen()
        _, data, files = gesendet[1]
        self.assertNotIn("timestamp_granularities", data)
        self.assertEqual(files["file"][2], "audio/wav")
        self.assertEqual(ergebnis, "Hallo")


class Aufruf(unittest.TestCase):
    def test_nachher_schreibt_um_statt_aufzunehmen(self):
        aufrufe = []
        alt = mithoeren.voxtral, mithoeren.nachher, mithoeren.aufnahme, sys.argv
        mithoeren.voxtral = lambda begriffe, nachher=False: ("voxtral", begriffe, nachher)
        mithoeren.nachher = lambda *a, **kw: aufrufe.append(a)
        mithoeren.aufnahme = lambda *a, **kw: self.fail("keine Aufnahme mit --nachher")
        sys.argv = ["mithoeren", "batch.txt", "--nachher", "ton.ogg", "--gegenueber", "Kunde", "--begriffe", "X"]
        try:
            mithoeren.main()
        finally:
            mithoeren.voxtral, mithoeren.nachher, mithoeren.aufnahme, sys.argv = alt
        self.assertEqual(aufrufe, [(Path("ton.ogg"), Path("batch.txt"),
                                    ("voxtral", f"{mithoeren.BEGRIFFE},X", True), "Kunde")])


if __name__ == "__main__":
    unittest.main()
