import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("sprachnachricht", Path(__file__).with_name("sprachnachricht.py"))
sprachnachricht = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sprachnachricht)


class Segment:
    def __init__(self, text):
        self.text = text


class Modell:
    """Attrappe für WhisperModel: meldet Spracherkennung und merkt sich die gewählte Sprache."""

    def __init__(self, sprachen, text="Hallo"):
        self.sprachen = sprachen
        self.text = text
        self.sprache = None

    def detect_language(self, audio):
        beste = max(self.sprachen, key=self.sprachen.get)
        return beste, self.sprachen[beste], list(self.sprachen.items())

    def transcribe(self, audio, language=None):
        self.sprache = language
        return iter([Segment(f" {self.text} ")]), None


class Umschrift(unittest.TestCase):
    def umschreiben(self, sprachen, genau=False):
        geladen = []

        def laden(name):
            geladen.append(name)
            return modell

        modell = Modell(sprachen)
        ergebnis = sprachnachricht.umschreiben("nachricht.oga", genau=genau, laden=laden, dekodieren=lambda p: p)
        return ergebnis, modell, geladen

    def test_goran_spricht_deutsch(self):
        (sprache, text), modell, _ = self.umschreiben({"de": 0.9, "sr": 0.05})
        self.assertEqual((sprache, modell.sprache, text), ("de", "de", "Hallo"))

    def test_vesna_spricht_serbisch_auch_wenn_whisper_kroatisch_meint(self):
        (sprache, _), modell, _ = self.umschreiben({"hr": 0.5, "bs": 0.2, "sr": 0.1, "de": 0.15})
        self.assertEqual((sprache, modell.sprache), ("sr", "sr"))

    def test_fremde_sprache_wird_deutsch_oder_serbisch(self):
        (sprache, _), _, _ = self.umschreiben({"en": 0.8, "de": 0.15, "sr": 0.05})
        self.assertEqual(sprache, "de")

    def test_schnell_ist_standard_genau_nimmt_das_grosse_modell(self):
        _, _, schnell = self.umschreiben({"de": 1.0})
        _, _, genau = self.umschreiben({"de": 1.0}, genau=True)
        self.assertEqual((schnell, genau), ([sprachnachricht.SCHNELL], [sprachnachricht.GENAU]))


if __name__ == "__main__":
    unittest.main()
