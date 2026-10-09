# Übersetzungsregeln des französischen WordPress-Teams (fr_FR)

Abgerufen am 2026-10-09 per Jina Reader. Nur Regeln, die in den Quellen stehen; wo eine Quelle schweigt, steht nichts.

Geltungsbereich (Gorans Entscheide 61a, 62a): Die Regeln gelten voll für Übersetzungen auf translate.wordpress.org
und die `.po`-Dateien. Für eigene Websites, Werbetexte und Mails gilt nur die Typografie; dort bleiben «plugin» und
«checkout» (Suchbegriffe der Käufer). Zahlen und Beträge in der Wartungsheft-App bleiben in allen Sprachen im
Schweizer Format («CHF 1'234.50», «100'000 km»), weil Eingabefelder davon abhängen.

Quellen:
- Handbuch «Traduire WordPress en français»: https://fr.wordpress.org/team/handbook/polyglots/ (Unterseiten `recommandations/`, `le-glossaire-et-les-erreurs-de-traduction-les-plus-frequentes/`, `les-regles-typographiques-utilisees-pour-la-traduction-de-wp-en-francais/`, `les-outils-utiles-a-la-traduction/spte/` und `/un-clavier-enrichi/`, `organisation-de-lequipe-de-traduction/le-processus-de-validation-des-traductions/` und `/decisions-concernant-la-traduction-de-wordpress/`)
- PTE-Ablauf: https://fr.wordpress.org/2015/12/18/how-french-community-handles-pte-requests/
- Glossar: https://translate.wordpress.org/locale/fr/default/glossary/

## 1. Ablauf PTE (Project Translation Editor)

- Willkommensseite «Bienvenue» (Canvas im Slack wordpressfr, von Goran am 09.10.2026 eingefügt): Guide lesen,
  Browser-Erweiterungen GlotDict und SPTE installieren (warnen bei Glossarbegriffen und Typografie), bei Bedarf
  «clavier enrichi»; Vorschläge validiert eine Person mit Rechten, alle im Team ehrenamtlich, es dauert. Bei
  zurückgewiesenen Vorschlägen (Sébastien Serre, 09.10.2026: «quelques règles non respectées») die Texte nach den
  Regeln korrigieren und auf translate.wordpress.org neu einreichen.

- Jedes Plugin ist ein eigenes «Projekt». Vorschläge von Beitragenden landen zuerst «en attente de validation»; geprüft wird durch PTE (Projektverantwortliche), GPTE (alle Plugins/Themes) oder GTE (ganzes Ökosystem).
- Wer das Plugin schreibt und Französisch kann, darf die eigenen Übersetzungen nicht selbst freigeben: Französisch sprechen garantiert nicht, dass die Regeln eingehalten werden.
- Wer kein Französisch spricht und eine Person übersetzen lässt, lässt sie auf translate.wordpress.org/locale/fr arbeiten. Eine PTE-Anfrage ohne Französischkenntnisse wird nicht angenommen.
- Schritte vor der Vergabe (Entwickler und/oder Übersetzer, am besten beide):
  1. Slack wordpressfr beitreten, Kanal **#traductions** (Slack ist für die PTE-Vergabe nur «facultatif mais vraiment recommandé»).
  2. Das Handbuch «Guide de traduction de WordPress en français» lesen.
  3. Als Contributor übersetzen (Vorschläge, keine Freigabe).
  4. Ein PTE prüft; PTE oder GTE geben Rückmeldung (Korrekturschleifen bis die Regeln sitzen).
  5. Bei Qualität auf Niveau der Regeln wird PTE-Recht vergeben.
- Voraussetzungen PTE: alle Übersetzungsregeln einhalten, Verhaltenskodex einhalten, im Verhältnis zur Projektgrösse substanziell am Projekt mitgearbeitet, mittelfristig Zeit für das Projekt. GTE können PTE-Rechte ohne Vorwarnung entziehen (meist bei Inaktivität).
- Empfohlen: in Translate unter «Translate Settings» die Option «I want to receive notifications of discussions» aktivieren, damit Prüfer-Kommentare ankommen.
- Zweifelhafte Strings überspringen («Traduisez ce que vous comprenez»), bei Fragen zu Begriffen in #traductions nachfragen.

## 2. Stil

- Anrede: formell, **«vous» statt «tu»**. Ton des Originals respektieren, nicht wörtlich übersetzen, kurze klare Sätze, Passiv vermeiden, auch für Leute ohne technische Vorkenntnisse verständlich.
- **Knöpfe/Aktionen: Infinitiv** («Enregistrer», «Ajouter»). **Hilfetexte und Tipps: Imperativ** (Beispiel: «Cliquez sur le bouton pour enregistrer les modifications effectuées dans les réglages.»).
- Inklusive Sprache (rédaction épicène), Reihenfolge: 1. neutrale Formulierung («les personnes chargées de l’administration»), 2. Doppelform («les administrateurs et administratrices»), 3. Mittelpunkt («administrateur·ice·s») nur bei sehr knappem Platz. Mittelpunkt: Linux `AltGr + Maj + .`, Windows Alt+0183.
- Grossschreibung in Titeln und Oberfläche: **nur Satzanfang, Eigennamen, Sigel gross**; englische Title Case nicht übernehmen (Ausnahme laut Glossar: «Tableau de bord» mit grossem T). Gilt auch für Dokument- und Kapiteltitel. Wochentage und Monate klein: «vendredi 25 mars 2016».
- **Nicht übersetzen:** Namen von Plugins und Themes, URLs. «WordPress» immer mit grossem W und P («WordPress»); «Wordpress» wird nie akzeptiert, ganz klein nur wo nötig (URLs).
- Platzhalter (`%s`, `%1$s`, `%2$d`) nie ändern und ihre Leerzeichen beachten; Stellung im Satz darf sich ändern, dann Zusammenhänge anpassen (Entwicklerkommentare über dem Eingabefeld lesen). HTML-Tags: nur Text zwischen öffnendem und schliessendem Tag übersetzen. Verdoppelte Prozentzeichen `%%` im Original auch in der Übersetzung verdoppeln.
- Anglizismen: Glossar gilt. «plugin» heisst immer **«extension»** (nie «plugin»); «post» = «publication» (nur «article», wenn nicht der generische Typ gemeint ist); «bug» = «bogue», «e-mail» (mit Bindestrich), «téléverser» für upload, «chaine» für string. Automatische Übersetzer (Google, Bing, Reverso, Lexicool) werden nicht empfohlen.
- Links: Zielsprache angeben («En savoir plus sur le CSS (en anglais)», knapp «(en)»); Linktext muss ausserhalb des Kontexts Sinn ergeben, nie «cliquez ici», «en savoir plus», «ici».
- Glossar darf je nach Kontext überschrieben werden, im Zweifel in #traductions fragen.

## 3. Typografie

Quelle nennt «espace insécable» ohne Unicode-Angabe; hier daher U+00A0 (NBSP). Ein schmaler Zeichencode (z. B. U+202F) wird in den Quellen nicht verlangt.

| Zeichen | Regel |
|---|---|
| `.` `,` `…` `)` `]` | kein Leerzeichen davor, eines danach |
| `(` `[` | eines davor, keines danach |
| `:` `;` `?` `!` | **NBSP davor**, normales Leerzeichen danach |
| `»` | NBSP davor, normales Leerzeichen danach |
| `«` | normales Leerzeichen davor, **NBSP danach** |
| `%`, Einheiten (25 km), Währung (25 €), mathematische Zeichen | NBSP davor |
| `/` | kein Leerzeichen («Oui/Non», «Précédent/Suivant»); Leerzeichen beidseits nur bei Ausdrücken oder Wörtern mit Bindestrich |
| Initial und Name | NBSP dazwischen |

- Anführungszeichen: französische «guillemets» mit NBSP innen.
- Apostroph: **typografisch ’ (U+2019)**, nie gerade `'`. Gerade Apostrophe und fehlende NBSP vor `:` sind die zwei häufigsten Fehler.
- Auslassungspunkte: ein Zeichen `…` (kein «...»), zählt als Satzzeichen; nach «etc.» keine Auslassungspunkte. Satzende immer mit `.` `?` `!` oder `…`; Titel enden ohne Satzzeichen. Aufzählung in einem Satz: Strichpunkt je Eintrag, Punkt am Ende.
- Zahlen: Dezimaltrenner **Komma**; Tausendertrenner **NBSP** (nie Punkt); Ordnungszahlen 1er, 2e; Jahrhunderte «XXIe siècle».
- Akzente auf Grossbuchstaben setzen («École», «Étant»), ausser bei Sigeln.
- Abkürzungen: Punkt nur, wenn nicht auf letztem Buchstaben endend («bd», aber «cat.», «art.»); «M.» statt «Mr». Sigel ohne Punkte.
- Datum: Monate und Tage klein. Ein festes Zahlenformat für Datum nennt die Quelle nicht. Das Glossar gibt für die Uhrzeit `g:i a` → `G\hi` vor (Form «14h30»).
- Tastatur: Windows «clavier enrichi» (Elrick oder Denis Liégeois), Linux Layout `fr` Variante `oss` (`setxkbmap -variant oss`), Mac hat alles eingebaut. Für Skills: Zeichen direkt als Unicode ausgeben.

## 4. Glossar (verbindliche Einträge fr_FR)

| Englisch | Französisch | Hinweis |
|---|---|---|
| plugin | extension | nie «plugin» |
| theme | thème | |
| settings / setting | réglages / réglage | |
| dashboard | tableau de bord | |
| customer | client/cliente | im Satz kombinieren; «client·e» nur bei Platzmangel |
| user | utilisateur/utilisatrice; «compte»; «internaute» (öffentlicher Teil) | |
| order (E-Commerce, Nomen) | commande | |
| order (Verb, E-Commerce) | commander | |
| order / order by (Sortierung) | trier / trier par | |
| checkout (Nomen) | commande | |
| checkout (Verb) | valider la commande | |
| store | boutique | E-Commerce |
| item (E-Commerce) | article | sonst «élément» |
| shipping | livraison (Kundenseite), expédition (Adminseite) | |
| payment method | moyen de paiement | |
| coupon / coupon code | code promo | |
| discount / discount code | remise / code de remise | |
| currency | devise | |
| rate (E-Commerce) | taux | |
| backorder | en réapprovisionnement | |
| SKU | UGS | Unité de Gestion des Stocks |
| lead (Onlinehandel) | prospect | |
| subscription | abonnement | |
| plan (Marketing) | offre | |
| company | entreprise | |
| form | formulaire | |
| submission(s) | envoi(s) | bei Formularen auch «entrée(s)» |
| submit | envoyer | |
| save | enregistrer | |
| edit / editing | modifier / modification | |
| delete / remove | supprimer / retirer | «Supprimer» für Benutzer, Plugins, Themes; sonst «retirer» |
| add new | ajouter | |
| select | sélectionner | |
| enter (Button) | saisir | |
| choose (Button) | choisir | |
| activate / deactivate | activer / désactiver | |
| upload | téléverser | |
| import / export | importer / exporter | |
| default | par défaut | |
| required / optional | obligatoire / facultatif | |
| invalid | invalide | |
| error | erreur | |
| warning | avertissement | |
| notice | notification | |
| status | état | |
| pending | en attente | |
| draft | brouillon | |
| trash | corbeille / mettre à la corbeille | |
| bulk actions | actions groupées | |
| filter | filtre | |
| search | rechercher | |
| email / email address | e-mail / adresse e-mail | mit Bindestrich |
| password / username | mot de passe / identifiant | |
| log in / log out | se connecter / se déconnecter | Nomen: connexion / déconnexion |
| permission(s) | droit(s) | auch «permission» bei capability |
| role | rôle | |
| API key | clé de l’API | |
| token | jeton | |
| webhook | crochet web | |
| log / log file | journal / fichier journal | Verb «journaliser» |
| debug | débogage / déboguer | |
| deprecated | obsolète | |
| language pack | paquet de langue | |
| changelog | journal des modifications | |
| upgrade | mettre à niveau / mise à niveau | |
| support (Verb) | prendre en charge | |
| Privacy Policy | politique de confidentialité | |
| Legal Terms | mentions légales | |
| try again | réessayer | |
| An error occurred | Une erreur s’est produite | |
| Please | Veuillez | |
| Are you sure | Confirmez-vous | |

Das Glossar enthält keinen Eintrag für invoice/Rechnung, tax/Steuer, cart/Warenkorb, price/Preis, product/Produit, address, total: dort Rückfrage in #traductions oder an der Stelle der Plugin-Übersetzung konsistent bleiben und nicht als verbindlich ausgeben.

## 5. Häufige Ablehnungsgründe (aus SPTE, Empfehlungen und Validierungs-FAQ)

1. Gerade Apostrophe `'` statt `’`.
2. Fehlender NBSP vor `:` `;` `?` `!` `»` `%` (und nach `«`).
3. Glossarverstösse, vor allem «plugin» statt «extension», «Post» statt «publication», «Wordpress»/«wordpress» statt «WordPress».
4. «tu» statt «vous», wörtliche Übersetzung, Passiv, überlange Sätze.
5. Englische Grossschreibung übernommen (Title Case in Knöpfen, Menüs, Titeln).
6. Platzhalter oder HTML verändert, verdoppelte `%%` verloren, Plugin-Name oder URL übersetzt.
7. Linktext «cliquez ici» oder fehlende Sprachangabe bei fremdsprachigem Link.
8. Maschinelle Übersetzung ohne Nachbearbeitung (nicht empfohlen).
9. Wiederholte Verstösse: Prüfer verlangen Korrekturen in Schleifen, PTE-Recht wird erst vergeben, wenn die Regeln sitzen. Die Quellen nennen keine weiteren Ablehnungsgründe.
