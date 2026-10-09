"""Tests für fr_po_pruefen.py: uv run --with regex python3 -m unittest test_fr_po_pruefen.py

Die Typografie-Fälle stammen aus SPTE (github.com/Association-WPFR/SPTE, utils/regex.test.js, Version 3.1.1, GPL-2.0+).
Je Regel: ein Verstoss wird gemeldet, korrekter Text nicht. Abweichungen von SPTE stehen beim Testfall.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fr_po_pruefen", HIER / "fr_po_pruefen.py")
fr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fr)

NB = " "   # geschütztes Leerzeichen
NNB = " "  # schmales geschütztes Leerzeichen


def regeln(msgstr, msgid=None, ausnahmen=None):
    """Regeln, die für einen Eintrag anschlagen; ohne msgid gilt der Text selbst als Original."""
    return {f.regel for f in fr.pruefe(msgstr if msgid is None else msgid, msgstr, ausnahmen)}


class SpteRegeln(unittest.TestCase):
    """Je Regel die Fälle aus SPTEs regex.test.js."""

    def meldet(self, regel, *texte):
        for t in texte:
            with self.subTest(text=t):
                self.assertIn(regel, regeln(t))

    def meldet_nicht(self, regel, *texte):
        for t in texte:
            with self.subTest(text=t):
                self.assertNotIn(regel, regeln(t))

    def test_badWords(self):
        self.meldet("badWords", "Le fichier est un plug-in.", "test,plugin,fin", "Titre:plugin suite",
                    "suite plugin:info", "a;plugin;b", '"plugin"', "'plugin'", "plugin est utile", "Voici un plugin")
        for mot in ["plugin", "greffon", "uploader", "downloader", "customiser", "updater", "mr", "sidebar",
                    "shortcode", "tooltip", "breadcrumb", "changelog", "thumbnail", "addon", "add-on", "back-end",
                    "front-end", "capabilities", "en-tête", "et/ou", "customizer", "template", "templates",
                    "add-ons", "événement"]:
            self.meldet("badWords", f"Un mot ici{NB}: {mot} et la suite.")
        self.meldet_nicht("badWords", "Ceci est une extension WordPress.", f"On dit «{NB}responsif{NB}» par erreur.",
                          "Un évènement important arrive.", "Cliquez sur l’entête du tableau.")

    def test_quotes(self):
        self.meldet("quotes", "l'extension")
        self.meldet_nicht("quotes", "<a href='example.com'>lien</a>", "l‘extension", "l’extension")

    def test_quotes_neben_platzhalter_abweichung_von_spte(self):
        # SPTE lässt ' neben %s durch; hier gilt ein Platzhalter als Wort, ein gerader Apostroph ist auch dort falsch
        self.meldet("quotes", "%s'appelle", "'%s")

    def test_reversedQuote(self):
        self.meldet("reversedQuote", "l‘extension")
        self.meldet_nicht("reversedQuote", "l’extension", "l'extension")

    def test_doubleQuotes(self):
        self.assertEqual(2, sum(f.regel == "doubleQuotes" for f in fr.pruefe("x", 'Il a dit "bonjour"')))
        self.meldet_nicht("doubleQuotes", '<a href="https://example.com">lien</a>',
                          '<a href="https://example.com" title="Mon titre">lien</a>')

    def test_slash(self):
        self.meldet("slash", "oui / non", "https:/ ")
        self.meldet_nicht("slash", "https://example.com", "{{rule /}}", "[[filter /]]", "Oui/Non")

    def test_openHook(self):
        self.meldet("openHook", "texte[note]", "un mot [ contenu]")
        self.meldet_nicht("openHook", "[[note]]", "[[valeur", "[valeur")

    def test_openBrace(self):
        self.meldet("openBrace", "texte{note}", "{ name }", "{  name}", "texte { deux mots }")
        self.meldet_nicht("openBrace", "{{note}}", "{ name}", "{valeur")

    def test_openParenthesis(self):
        self.meldet("openParenthesis", "texte(suite)", "texte ( suite", "Van Gogh(Néerlandais, 1853-1890)")
        self.meldet_nicht("openParenthesis", "un ou plusieurs mot(s)", "(valeur", '<span class="count">(%s',
                          "<code>get_flexible()", "validé(e)", "soldé(es)", "réside(nt)", "écrit(vent)",
                          "Vincent Van Gogh<br>(Néerlandais, 1853-1890)", "registerBlockType( name, settings );")

    def test_ellipsis(self):
        self.meldet("ellipsis", "et…puis", "mot …!", "et… ", "et…" + NB, "et…×trois")
        self.meldet_nicht("ellipsis", "et… puis", "et...puis")

    def test_asciiEllipsis(self):
        self.meldet("asciiEllipsis", "et...puis", "Chargement...")
        self.meldet_nicht("asciiEllipsis", "Chargement…", "Copiez le fichier dans ../wp-content/")

    def test_period(self):
        self.meldet("period", "Voir ceci .vraiment", "Fin de phrase. ", "Fin de phrase." + NB)
        self.meldet_nicht("period", "phrase.suite", "lire le fichier readme.txt",
                          f"Formats pris en charge{NB}: .ttf, .otf, .woff et .woff2.")

    def test_comma(self):
        self.meldet("comma", "un,deux", "[a,b]", "un,×deux")
        self.meldet_nicht("comma", "un, deux", "Noto Serif:400,400i,700,700i", "3,5 grammes")

    def test_closeHook(self):
        self.meldet("closeHook", "[note]suite")
        self.meldet_nicht("closeHook", "[note] suite", "[[valeur]]texte")

    def test_closeParenthesis(self):
        self.meldet("closeParenthesis", "texte (a) suite", "texte )", "texte ) suite")
        self.meldet_nicht("closeParenthesis", "affiché(e)", "animé(e)s", "registerBlockType( name, settings );")

    def test_closeBrace(self):
        self.meldet("closeBrace", "{note}suite")
        self.meldet_nicht("closeBrace", "{note} suite", "{{valeur}}")

    def test_exclamationPoint(self):
        self.meldet("exclamationPoint", "Bravo!", "Bravo !")
        self.meldet_nicht("exclamationPoint", f"Bravo{NB}!", f"Bravo{NNB}!", "width: 100px !important;",
                          "! Bravo", f"Bravo{NB}!)")

    def test_plusSign(self):
        self.meldet("plusSign", "2+2")
        self.meldet_nicht("plusSign", "google+", "+ 2", f"2{NB}+")

    def test_questionMark(self):
        self.meldet("questionMark", "Pourquoi?", "Pourquoi ?")
        self.meldet_nicht("questionMark", "fichier.php?param=1", "/?var", "/page?name", "? texte",
                          f"Pourquoi{NB}?", f"Pourquoi{NB}?)", f"Pourquoi{NNB}?")

    def test_colon(self):
        self.meldet("colon", "Titre: texte", "Titre : texte", "{foo:bar}")
        self.meldet_nicht("colon", f"Titre{NB}: texte", "http://example.com", "https://", " hh:mm",
                          "Y/m/d g:s:i A")

    def test_colon_verlangt_u00a0_entscheid_64b(self):
        # SPTE nimmt vor «:» auch U+202F; Gorans Entscheid 64b verlangt dort U+00A0
        self.meldet("colon", f"Titre{NNB}: texte")

    def test_semiColon(self):
        self.meldet("semiColon", "un;deux", "un ; deux")
        self.meldet_nicht("semiColon", "&nbsp;texte", "item de liste;", f"un{NNB}; deux", f"un{NB}; deux")

    def test_closingFrQuote(self):
        self.meldet("closingFrQuote", "texte»", f"«{NB}texte »")
        self.meldet_nicht("closingFrQuote", f"texte{NB}»", f"mot{NB}».", f"mot{NB}»,", f"mot{NB}»{NB}?",
                          f"mot{NB}»{NB}!", f"mot{NB}»{NB}:", f"mot{NB}»{NB};",
                          f"«{NB}La Berceuse (femme balançant un berceau){NB}» par Vincent Van Gogh (1889)",
                          f"Pro{NB}»</strong> suite")

    def test_closingFrQuote_verlangt_u00a0_entscheid_64b(self):
        # SPTE nimmt vor «»» auch U+202F; Gorans Entscheid 64b verlangt dort U+00A0
        self.meldet("closingFrQuote", f"texte{NNB}»")

    def test_openFrQuote(self):
        self.meldet("openFrQuote", "«texte", "texte « texte")
        self.meldet_nicht("openFrQuote", f"texte «{NB}texte", f"«{NB}texte", f"texte <strong>«{NB}texte")

    def test_epicenePunctuation(self):
        self.meldet("epicenePunctuation", "Les administrateur.rice sont invités.",
                    "Les utilisateur-rice peuvent se connecter.", "Bienvenue aux abonné*e*s du site.")
        self.meldet_nicht("epicenePunctuation", "Les administrateur·rice sont invités.",
                          "La 2e édition est disponible.", "Envoyer un e-mail de confirmation.")

    def test_prozent_aus_dem_handbuch(self):
        # Nicht in SPTE: das Handbuch verlangt ein geschütztes Leerzeichen vor %
        self.meldet("prozent", "Remise de 10%", "Remise de 10 %%")
        self.meldet_nicht("prozent", f"Remise de 10{NB}%%", "Remise de %s")


class Glossar(unittest.TestCase):
    def test_glossarbegriff_ohne_franzoesische_entsprechung_wird_gemeldet(self):
        self.assertIn("glossar:API key", regeln("Saisissez votre clé API.", "Enter your API key."))
        self.assertIn("glossar:token", regeln("Le token est invalide.", "The token is invalid."))

    def test_glossarbegriff_mit_entsprechung_ist_gruen(self):
        self.assertFalse({r for r in regeln("Saisissez votre clé de l’API.", "Enter your API key.")
                          if r.startswith("glossar:")})
        self.assertNotIn("glossar:token", regeln("Les jetons sont invalides.", "The tokens are invalid."))

    def test_eine_von_mehreren_entsprechungen_genuegt(self):
        # order: commande, commander, trier, ordre
        self.assertNotIn("glossar:order", regeln("Commande introuvable.", "Order not found."))
        self.assertNotIn("glossar:order", regeln("Trier par date.", "Order by date."))

    def test_schraegstrich_varianten_einzeln(self):
        # administrator: administrateur/administratrice, im Satz einzeln oder kombiniert
        self.assertNotIn("glossar:administrator", regeln("Contactez l’administrateur.", "Contact the administrator."))

    def test_konjugiertes_verb_zaehlt(self):
        # Abweichung von GlotDict: Hilfetexte stehen im Imperativ (Handbuch), «Sélectionnez» erfüllt «Sélectionner»
        self.assertNotIn("glossar:select", regeln("Sélectionnez une option.", "Select an option."))

    def test_anzahl_wie_glotdict(self):
        self.assertIn("glossar:token", regeln("Le jeton et l’autre token.", "The token and the other token."))

    def test_begriff_nur_als_ganzes_wort(self):
        self.assertNotIn("glossar:token", regeln("Mots", "Tokenizer words"))

    def test_platzhalter_html_und_urls_im_original_zaehlen_nicht(self):
        self.assertNotIn("glossar:plugin", regeln("Voir X.", 'See <a href="https://example.com/plugin">X</a>.'))


class PlatzhalterUndHtml(unittest.TestCase):
    def test_platzhalter_muessen_gleich_bleiben(self):
        self.assertIn("platzhalter", regeln("Commande %d", "Order %s"))
        self.assertIn("platzhalter", regeln("Commande", "Order %s"))
        self.assertNotIn("platzhalter", regeln("Commande %2$s de %1$s", "Order %1$s by %2$s"))

    def test_verdoppeltes_prozent_bleibt(self):
        self.assertIn("platzhalter", regeln(f"10{NB}%", "10%%"))

    def test_html_muss_gleich_bleiben(self):
        self.assertIn("html", regeln("Commande <b>X</b>", "Order <strong>X</strong>"))
        self.assertNotIn("html", regeln("Commande <strong>X</strong>", "Order <strong>X</strong>"))


class Ausnahmen(unittest.TestCase):
    def test_unveraenderte_texte_werden_nicht_geprueft(self):
        a = fr.Ausnahmen(unveraendert=["Shop Invoices for KLARA", "Paramètres → Automation → API Tokens"])
        self.assertEqual(set(), regeln("Shop Invoices for KLARA", "Shop Invoices for KLARA", a))
        self.assertNotIn("glossar:token", regeln(f"Ouvrez Paramètres → Automation → API Tokens.",
                                                 "Open Settings → Automation → API Tokens.",
                                                 fr.Ausnahmen(unveraendert=["Settings → Automation → API Tokens",
                                                                            "Paramètres → Automation → API Tokens"])))

    def test_ausnahme_fuer_eine_regel_und_einen_eintrag(self):
        a = fr.Ausnahmen(regeln=[{"regel": "glossar:token", "msgid": "The token is invalid.", "grund": "Test"}])
        self.assertNotIn("glossar:token", regeln("Le token est invalide.", "The token is invalid.", a))
        self.assertIn("glossar:token", regeln("Un token.", "A token.", a))

    def test_ausnahme_ohne_grund_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            fr.Ausnahmen(regeln=[{"regel": "glossar:token"}])


PO_KOPF = 'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'


class Kommandozeile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def aufruf(self, *args):
        return subprocess.run([sys.executable, str(HIER / "fr_po_pruefen.py"), *args],
                              capture_output=True, text=True, env={**os.environ, "NO_COLOR": "1"})

    def po(self, inhalt):
        datei = self.ordner / "x-fr_FR.po"
        datei.write_text(PO_KOPF + inhalt, encoding="utf-8")
        return datei

    def test_verstoss_gibt_zeile_msgid_regel_und_exit_ungleich_null(self):
        datei = self.po('#: a.php:1\nmsgid "Settings"\nmsgstr "Réglages"\n\n'
                        '#: a.php:2\nmsgid "Install the plugin"\nmsgstr "Installez le plugin"\n')
        r = self.aufruf(str(datei))
        self.assertNotEqual(0, r.returncode)
        self.assertIn(f"{datei}:11:", r.stdout)  # Zeile des msgstr
        self.assertIn("Install the plugin", r.stdout)
        self.assertIn("badWords", r.stdout)
        self.assertNotIn("Settings", r.stdout)

    def test_korrekte_datei_ist_gruen(self):
        datei = self.po(f'msgid "Settings: %s"\nmsgstr "Réglages{NB}: %s"\n\n'
                        'msgid "Install the plugin"\nmsgstr "Installez l’extension"\n')
        r = self.aufruf(str(datei))
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_mehrzeilige_eintraege_mehrzahl_und_kontext(self):
        datei = self.po('msgctxt "x"\nmsgid ""\n"One "\n"token"\nmsgid_plural "%d tokens"\n'
                        'msgstr[0] "Un jeton"\nmsgstr[1] "%d tokens"\n')
        r = self.aufruf(str(datei))
        self.assertNotEqual(0, r.returncode)
        self.assertIn(":11:", r.stdout)  # msgstr[1] gegen msgid_plural
        self.assertNotIn(":10:", r.stdout)  # msgstr[0] gegen msgid

    def test_ausnahmendatei(self):
        datei = self.po('msgid "Install the plugin"\nmsgstr "Installez le plugin"\n')
        ausnahmen = self.ordner / "fr-ausnahmen.toml"
        ausnahmen.write_text('[[ausnahme]]\nregel = "badWords"\nmsgid = "Install the plugin"\ngrund = "Test"\n'
                             '[[ausnahme]]\nregel = "glossar:plugin"\nmsgid = "Install the plugin"\ngrund = "Test"\n',
                             encoding="utf-8")
        r = self.aufruf(str(datei), "--ausnahmen", str(ausnahmen))
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_ungenutzte_ausnahme_wird_gemeldet(self):
        datei = self.po('msgid "Settings"\nmsgstr "Réglages"\n')
        ausnahmen = self.ordner / "fr-ausnahmen.toml"
        ausnahmen.write_text('[[ausnahme]]\nregel = "badWords"\nmsgid = "Weg"\ngrund = "Test"\n', encoding="utf-8")
        r = self.aufruf(str(datei), "--ausnahmen", str(ausnahmen))
        self.assertNotEqual(0, r.returncode)
        self.assertIn("ungenutzte Ausnahme", r.stdout)

    def test_veraltete_eintraege_zaehlen_nicht(self):
        datei = self.po('#~ msgid "Install the plugin"\n#~ msgstr "Installez le plugin"\n')
        self.assertEqual(0, self.aufruf(str(datei)).returncode)

    def test_glossar_aktualisieren_schreibt_csv_und_abrufdatum(self):
        quelle = self.ordner / "export.csv"
        quelle.write_text('en,fr,pos,description\ntoken,jeton,noun,\n', encoding="utf-8")
        ziel = self.ordner / "glossar"
        fr.glossar_aktualisieren(quelle.as_uri(), ziel)
        self.assertEqual(quelle.read_text(encoding="utf-8"), (ziel / "glossar-fr.csv").read_text(encoding="utf-8"))
        stand = (ziel / "glossar-fr.quelle").read_text(encoding="utf-8")
        self.assertIn(quelle.as_uri(), stand)
        self.assertRegex(stand, r"abgerufen \d{4}-\d{2}-\d{2}")


if __name__ == "__main__":
    unittest.main()
