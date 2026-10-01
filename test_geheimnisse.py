"""Tests für geheimnisse.py mit einem Tresor im Speicher statt bws: python3 -m unittest test_geheimnisse.py"""
import json
import pathlib
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import geheimnisse  # noqa: E402


class FalschesBws:
    """Versteht die Aufrufe, die geheimnisse.py an bws richtet, und merkt sich die Geheimnisse."""

    def __init__(self):
        self.geheimnisse = {}  # id -> {key, value, note}
        self.aufrufe = []

    def __call__(self, args):
        self.aufrufe.append(list(args))
        if args[:2] == ["project", "list"]:
            return json.dumps([{"id": "p-1", "name": "anderes"}, {"id": "p-2", "name": "strainovic"}])
        if args[:2] == ["secret", "list"]:
            assert args[2] == "p-2"
            return json.dumps([{"id": i, **g} for i, g in self.geheimnisse.items()])
        if args[:2] == ["secret", "create"]:
            # Wie bws: Was mit «-» beginnt und vor «--» steht, gilt als Option, nicht als Wert.
            trenner = args.index("--")
            assert args[2] == "--note" and trenner == 4, "Optionen vor «--», Name und Wert dahinter"
            key, value, projekt = args[trenner + 1:]
            assert projekt == "p-2"
            i = f"s-{len(self.geheimnisse) + 1}"
            self.geheimnisse[i] = {"key": key, "value": value, "note": args[3]}
            return json.dumps({"id": i, "key": key})
        if args[:2] == ["secret", "edit"]:
            assert args[2].startswith("--value=") and args[3] == "--", "Wert als --value=…, ID hinter «--»"
            self.geheimnisse[args[4]]["value"] = args[2][len("--value="):]
            return json.dumps({"id": args[4]})
        raise AssertionError(f"unerwarteter Aufruf: {args[:3]}")

    def wert(self, key):
        return next(g["value"] for g in self.geheimnisse.values() if g["key"] == key)


class GeheimnisseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.basis = pathlib.Path(self.tmp.name)
        self.bws = FalschesBws()
        self.tresor = geheimnisse.Tresor(self.bws)

    def tearDown(self):
        self.tmp.cleanup()

    def datei(self, pfad, inhalt):
        p = self.basis / pfad
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inhalt, encoding="utf-8")
        return p

    def test_hochladen_legt_an_mit_pfad_als_name_und_unveraendertem_inhalt(self):
        p = self.datei("dms/apps/dms/.env", "A=1\nB=zwei wörter\n")

        self.assertEqual([("dms/apps/dms/.env", "neu")], self.tresor.hochladen(self.basis, [p]))
        self.assertEqual("A=1\nB=zwei wörter\n", self.bws.wert("dms/apps/dms/.env"))

    def test_hochladen_aendert_vorhandenes_und_laesst_gleiches_in_ruhe(self):
        p = self.datei("find-jobs/.env", "X=1\n")
        self.tresor.hochladen(self.basis, [p])
        self.assertEqual([("find-jobs/.env", "gleich")], self.tresor.hochladen(self.basis, [p]))

        p.write_text("X=2\n", encoding="utf-8")
        self.assertEqual([("find-jobs/.env", "geändert")], self.tresor.hochladen(self.basis, [p]))
        self.assertEqual("X=2\n", self.bws.wert("find-jobs/.env"))
        self.assertEqual(1, len(self.bws.geheimnisse))

    def test_hochladen_lehnt_dateien_ausserhalb_der_basis_ab(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env") as fremd:
            with self.assertRaises(ValueError):
                self.tresor.hochladen(self.basis, [pathlib.Path(fremd.name)])
        self.assertEqual({}, self.bws.geheimnisse)

    def test_holen_schreibt_fehlende_dateien_nur_fuer_den_besitzer_lesbar(self):
        self.tresor.hochladen(self.basis, [self.datei("wartungsheft/.env", "K=geheim\n")])
        (self.basis / "wartungsheft/.env").unlink()
        (self.basis / "wartungsheft").rmdir()

        self.assertEqual([("wartungsheft/.env", "geschrieben")], self.tresor.holen(self.basis))
        ziel = self.basis / "wartungsheft/.env"
        self.assertEqual("K=geheim\n", ziel.read_text(encoding="utf-8"))
        if sys.platform != "win32":
            self.assertEqual(0o600, stat.S_IMODE(ziel.stat().st_mode))

    def test_holen_ueberschreibt_abweichende_dateien_nur_auf_wunsch(self):
        p = self.datei("dms/.env", "ALT=1\n")
        self.tresor.hochladen(self.basis, [p])
        p.write_text("LOKAL=2\n", encoding="utf-8")

        self.assertEqual([("dms/.env", "abweichend")], self.tresor.holen(self.basis))
        self.assertEqual("LOKAL=2\n", p.read_text(encoding="utf-8"))

        self.assertEqual([("dms/.env", "geschrieben")], self.tresor.holen(self.basis, ueberschreiben=True))
        self.assertEqual("ALT=1\n", p.read_text(encoding="utf-8"))

    def test_holen_uebergeht_geheimnisse_ohne_pfad_und_solche_die_aus_der_basis_zeigen(self):
        self.bws.geheimnisse = {
            "s-1": {"key": "EINZELWERT", "value": "x", "note": ""},
            "s-2": {"key": "../ausserhalb/.env", "value": "x", "note": ""},
            "s-3": {"key": "/etc/passwd", "value": "x", "note": ""},
            "s-4": {"key": "repo/.env", "value": "ok\n", "note": ""},
        }

        self.assertEqual([("repo/.env", "geschrieben")], self.tresor.holen(self.basis))
        self.assertFalse((self.basis.parent / "ausserhalb").exists())

    def test_dateien_aus_dem_home_heissen_mit_tilde_und_kommen_dorthin_zurueck(self):
        heim = self.basis / "heim"
        projekte = heim / "projects"
        p = heim / ".config/jina/key"
        p.parent.mkdir(parents=True)
        p.write_text("jina-geheim\n", encoding="utf-8")
        q = projekte / "repo/.env"
        q.parent.mkdir(parents=True)
        q.write_text("R=1\n", encoding="utf-8")

        self.assertEqual([("~/.config/jina/key", "neu"), ("repo/.env", "neu")],
                         self.tresor.hochladen(projekte, [p, q], heim=heim))
        p.unlink()
        self.assertEqual([("repo/.env", "gleich"), ("~/.config/jina/key", "fehlt lokal")],
                         self.tresor.status(projekte, heim=heim))
        self.assertEqual([("~/.config/jina/key", "geschrieben")], self.tresor.holen(projekte, heim=heim))
        self.assertEqual("jina-geheim\n", p.read_text(encoding="utf-8"))

    def test_tilde_pfade_die_aus_dem_home_zeigen_und_fehlendes_home_werden_uebergangen(self):
        heim = self.basis / "heim"
        heim.mkdir()
        self.bws.geheimnisse = {
            "s-1": {"key": "~/../fremd/.env", "value": "x", "note": ""},
            "s-2": {"key": "~/.ssh/id_ed25519", "value": "schluessel\n", "note": ""},
        }

        self.assertEqual([], self.tresor.holen(self.basis / "projekte"))
        self.assertEqual([("~/.ssh/id_ed25519", "geschrieben")], self.tresor.holen(self.basis / "projekte", heim=heim))
        self.assertFalse((self.basis / "fremd").exists())

    def test_status_nennt_gleich_abweichend_und_fehlend_ohne_werte(self):
        a = self.datei("a/.env", "1\n")
        b = self.datei("b/.env", "2\n")
        c = self.datei("c/.env", "3\n")
        self.tresor.hochladen(self.basis, [a, b, c])
        b.write_text("anders\n", encoding="utf-8")
        c.unlink()

        self.assertEqual([("a/.env", "gleich"), ("b/.env", "abweichend"), ("c/.env", "fehlt lokal")],
                         self.tresor.status(self.basis))


if __name__ == "__main__":
    unittest.main()
