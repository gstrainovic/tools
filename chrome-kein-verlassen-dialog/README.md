# Kein «Website verlassen?»-Dialog

Chrome-Erweiterung für Gorans Chrome: macht `beforeunload`-Handler auf ricardo.ch und tutti.ch wirkungslos. Ohne sie
bleibt ein automatisierter Lauf (playwright-cli, angehängt an Chrome) nach einem abgebrochenen Formular am Dialog
«Website verlassen?» hängen: Die Playwright-Extension kennt den Dialog nach dem Abbruch nicht mehr, `dialog-accept`
greift nicht, und jede weitere Navigation (goto, reload, tab-close) wirft ihn erneut.

Einmalig laden (das Startflag `--load-extension` ignoriert Chrome seit Version 137):

1. `chrome://extensions` öffnen, oben rechts «Entwicklermodus» einschalten.
2. «Entpackte Erweiterung laden» → diesen Ordner wählen (`~/projects/tools/chrome-kein-verlassen-dialog`).
3. Offene Ricardo- und tutti-Tabs neu laden.

Prüfen: in einem Ricardo-Verkaufsformular ein Feld ändern und die Seite verlassen; es darf kein Dialog kommen.
Weitere Domains: in `manifest.json` unter `matches` ergänzen, dann auf `chrome://extensions` «Aktualisieren».
