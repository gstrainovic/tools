---
name: wp-plugin-ch
description: WordPress-Plugins für Schweizer KMU bauen, testen und übersetzen (PHPUnit/Brain Monkey im Container, E2E mit Attrappe, Plugin Check, de_DE/de_CH/fr_FR/it_IT). Laden bei Arbeit an einem WordPress-Plugin, etwa in klara-shop-connector, bexio-formular-connector oder zefix-uid-check.
---

# WordPress-Plugin (Schweiz)

Repo-Spezifisches (Slug, API, Attrappe, Ports, Sonderfälle) steht in der AGENTS.md des Repos.

## Aufbau

- Plugin-Code unter `plugin/<slug>/`. Der Slug beginnt nicht mit einem fremden Markennamen (wordpress.org-Regel).
- Eigener Autoloader, keine Composer-Laufzeitabhängigkeiten.
- Die HTTP-Schicht ist austauschbar, damit Unit-Tests ohne Netz laufen.

## Tests

- TDD mit PHPUnit 11 und Brain Monkey im Container `composer:2`: `./bin-test.sh [phpunit-Argumente]`. PHP ist lokal nicht installiert.
- E2E: `cd e2e && docker compose up -d && ./e2e.sh`. Echtes WordPress im Container, der externe Dienst ist durch eine Attrappe ersetzt (mu-Plugin unter `e2e/mu/`), die sich an die Beispielantworten und Regeln der offiziellen API-Doku hält.
- Danach `docker compose exec -T cli wp plugin check <slug>` (offizieller Plugin Check von wordpress.org). Er muss ohne Fehler durchlaufen.

## wordpress.org

- `readme.txt`, Plugin-Kopf und Quelltexte sind englisch.
- `Tags:` in der readme sind die Suchbegriffe der Zielgruppe, nicht Technikwörter: wordpress.org wertet nur die
  ersten fünf, und Plugin-Spiegel (pluginsdb.com, wphive.com) übernehmen sie unverändert. Je Plugin die Begriffe,
  die ein Schweizer Shopbetreiber tippt (etwa `schweiz`, `bexio`, `zefix`, `rappen`, `mwst`), neben `woocommerce`
  und `switzerland`. Eine Tag-Änderung braucht keine neue Version: readme in `trunk/` und im Tag der stabilen
  Version per SVN committen (`svn-ci.sh`).
- Externe Dienste im readme-Abschnitt «External services» offenlegen.
- Pro Konto (gstrainovic) liegt nur ein Plugin gleichzeitig in der Prüfung. Rückfragen der Prüfer im selben Mail-Thread beantworten, nie neu einreichen.

## Übersetzungen

- Quelltext englisch. Alle sichtbaren Texte laufen durch `__()`/`esc_html__()` mit der Text Domain = Slug, auch Texte, die im Zielsystem oder im Protokoll landen.
- `plugin/<slug>/languages/` enthält `.pot` sowie `.po`/`.mo` für `de_DE`, `de_CH` (ohne ß), `fr_FR`, `it_IT`.
  Ins Paket für wordpress.org kommt nur die `.pot`: `languages/.gitattributes` mit `*.po export-ignore` und
  `*.mo export-ignore`, das Build-Skript prüft das ZIP. Die Prüfer lehnen mitgelieferte `.po`/`.mo` ab; nach der
  Freigabe die `.po` auf translate.wordpress.org importieren.
- Nach Textänderungen `./bin-uebersetzungen.sh`: `.pot` per `wp i18n make-pot` im Container `wordpress:cli`, `msgmerge` in jede `.po`, `.mo` per `msgfmt -c`. Neue Texte danach in allen `.po` übersetzen und das Skript noch einmal laufen lassen.
- Pluginnamen nie übersetzen (Style Guide der Polyglots, gilt auch für die Kurzform ohne «Strainovic IT» in Menü,
  Seitentitel und Sätzen; `UebersetzungenTest` prüft es). Gilt nur für WordPress; das Shopware-Plugin von KLARA
  behält seinen übersetzten Namen («Rechnungen für KLARA», Gorans Entscheid), weil der Shopware Store je Sprache
  benennt.
- `Sprache::datei()` bildet die Seitensprache ab: `de_CH*` → `de_CH`, übrige `de*` → `de_DE`, `fr*` → `fr_FR`, `it*` → `it_IT`, sonst Englisch.
- Laden per `load_textdomain()` auf `init` und bei `change_locale`. `load_plugin_textdomain()` meldet Plugin Check als veraltet.
- `UebersetzungenTest` schlägt fehl, wenn ein Text im Code nicht in der `.pot` steht, eine Übersetzung fehlt, Platzhalter abweichen oder eine `.mo` nicht zu ihrer `.po` passt.
- Terminologie Schweiz (MWST/TVA/IVA, Rappen/centimes/centesimi) und wie die WordPress- bzw. WooCommerce-Übersetzung. Französisch siezt («vous»), Italienisch duzt wie die WordPress-Übersetzung.
- **Französisch:** vor jeder `fr_FR.po`, jedem Vorschlag auf translate.wordpress.org und jeder Nachricht im Slack
  wordpressfr `fr-richtlinien.md` in diesem Ordner lesen (Stil, Typografie mit geschützten Leerzeichen, Glossar,
  PTE-Ablauf des französischen Teams); der Hook `skill-hinweis.sh` erinnert bei `.po`-Dateien,
  translate.wordpress.org, wordpress*.slack.com und Prompts zu Übersetzung, Polyglots und PTE an diesen Skill.
- E2E installiert die WordPress-Sprachpakete und prüft die Oberfläche je Sprache (en_US, de_CH, fr_FR, it_IT).
