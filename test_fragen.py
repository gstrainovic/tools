import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("fragen", Path(__file__).with_name("fragen.py"))
fragen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fragen)


def repo(wurzel: Path, name: str, dateien: dict[str, str]) -> Path:
    """Git-Repo mit committeten Dateien, wie die Repos unter ~/projects."""
    ordner = wurzel / name
    ordner.mkdir(parents=True)
    for pfad, text in dateien.items():
        (ordner / pfad).parent.mkdir(parents=True, exist_ok=True)
        (ordner / pfad).write_text(text)
    git = ["git", "-C", str(ordner), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(git[:3] + ["init", "-q"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "x"], check=True)
    return ordner


class Neu(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.zaehler = self.tmp / "zaehler"

    def test_ohne_fragen_beginnt_die_eindeutige_zaehlung(self):
        repo(self.tmp / "p", "a", {"todo.md": "nichts\n"})
        self.assertEqual(fragen.neu(self.tmp / "p", self.zaehler), [fragen.START])

    def test_naechste_nummer_nach_der_hoechsten_in_allen_repos(self):
        repo(self.tmp / "p", "a", {"todo.md": "- [ ] **Frage 315: x?**\n"})
        repo(self.tmp / "p", "b", {"AGENTS.md": "Gorans Entscheid 318b\n"})
        self.assertEqual(fragen.neu(self.tmp / "p", self.zaehler, 2), [319, 320])

    def test_vergebene_nummern_kommen_nicht_zweimal_auch_wenn_noch_nicht_eingetragen(self):
        repo(self.tmp / "p", "a", {"todo.md": "- [ ] **Frage 315: x?**\n"})
        erste = fragen.neu(self.tmp / "p", self.zaehler)
        self.assertEqual(fragen.neu(self.tmp / "p", self.zaehler), [erste[0] + 1])

    def test_jahreszahlen_und_alte_nummern_zaehlen_nicht(self):
        repo(self.tmp / "p", "a", {"todo.md": "Frage 2020 im Forum, Frage 12 offen\n"})
        self.assertEqual(fragen.neu(self.tmp / "p", self.zaehler), [fragen.START])


class Pruefen(unittest.TestCase):
    def setUp(self):
        self.wurzel = Path(tempfile.mkdtemp())

    def test_verweis_auf_offene_frage_ist_veraltet_wenn_anderswo_entschieden(self):
        # Fall Cecily-Set: Antwort beim Flakon eingetragen, das Set verweist weiter auf «offen in Frage»
        repo(self.wurzel, "vesna", {"action-dupes/todo.md": "- [ ] Set nicht veröffentlichen, offen in Frage 320\n",
                                    "action-dupes/AGENTS.md": "Flakon als Cecily verkaufen (Gorans Entscheid 320b)\n"})
        bericht = fragen.pruefen(self.wurzel)
        self.assertEqual([(b.datei.name, b.zeile, b.nummer) for b in bericht.veraltet], [("todo.md", 1, 320)])

    def test_vorlaeufiges_ist_veraltet_wenn_die_antwort_in_einem_anderen_repo_steht(self):
        repo(self.wurzel, "a", {"inserate.py": "# vorläufig gesperrt bis Frage 321\n"})
        repo(self.wurzel, "b", {"TODO.md": "Antwort 321a umgesetzt\n"})
        self.assertEqual([b.nummer for b in fragen.pruefen(self.wurzel).veraltet], [321])

    def test_unbeantwortete_frage_ist_offen_mit_datum(self):
        repo(self.wurzel, "a", {"todo.md": "- [ ] **Frage 322: Banddrucker kaufen?** 322a ja, 322b nein\n"})
        bericht = fragen.pruefen(self.wurzel)
        self.assertEqual(bericht.veraltet, [])
        self.assertEqual([b.nummer for b in bericht.offen], [322])
        self.assertRegex(bericht.offen[0].datum, r"^\d{4}-\d\d-\d\d$")

    def test_optionen_in_der_frage_selbst_gelten_nicht_als_antwort(self):
        repo(self.wurzel, "a", {"todo.md": "- [ ] **Frage 323 offen:** 323a so, 323b anders (Empfehlung 323a)\n"})
        self.assertEqual([b.nummer for b in fragen.pruefen(self.wurzel).offen], [323])

    def test_alte_mehrdeutige_nummern_nur_als_offen_nie_als_veraltet(self):
        repo(self.wurzel, "a", {"todo.md": "- [ ] **Frage 12 offen: Banddrucker?**\n",
                                "AGENTS.md": "Preise nach Entscheid 12a\n"})
        bericht = fragen.pruefen(self.wurzel)
        self.assertEqual(bericht.veraltet, [])
        self.assertEqual([(b.nummer, b.alt) for b in bericht.offen], [(12, True)])

    def test_ausgabe_nennt_datei_zeile_und_text(self):
        repo(self.wurzel, "a", {"todo.md": "- [ ] Set gesperrt, offen in Frage 320\n", "b.md": "Entscheid 320b\n"})
        text = fragen.ausgabe(fragen.pruefen(self.wurzel))
        self.assertIn("VERALTET", text)
        self.assertIn("a/todo.md:1", text)
        self.assertIn("offen in Frage 320", text)


if __name__ == "__main__":
    unittest.main()
