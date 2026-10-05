---
name: entwicklung
description: Allgemeine Entwicklungsregeln für alle Repos: Tests prüfen Verhalten statt Hilfsfunktionen, TDD in Plänen für Subagenten, Umfang einer Änderung (Nebenbefunde melden statt nebenbei umsetzen), Python nur mit uv, GitHub-Inhalte per gh, lokale Modelle über Ollama (127.0.0.1, Tool-Calling kleiner Modelle), llama_index mit Nicht-OpenAI-Anbietern, Container-Fallen. Laden, bevor Code, Tests oder ein Umsetzungsplan geschrieben werden.
---

# Entwicklung (alle Repos)

## Tests

- **Verhalten testen, nicht Implementierung.** Ein Test für einen Parser oder eine Hilfsfunktion reicht nicht; getestet wird, was der Nutzer sieht (z. B. `test_rename_prefills_current_name`, `test_search_finds_renamed_session`).
- Bei einem neuen Datenfeld oder Feature jede Stelle prüfen, an der es auftaucht: Liste oder Spalte, Vorschau, Suche, Sortierung, Vorbelegung, Aktualisierung nach Änderung.
- Prüffrage: Würde ein echter Fehler durchrutschen, wenn dieser Test fehlt? Wenn nein, ist es der falsche Test.
- **Pläne für Subagenten fordern TDD ausdrücklich** («RED → GREEN → REFACTOR» je Schritt), auch bei kleinen Änderungen. Grund: Subagenten sehen oft nur den Plan, nicht die CLAUDE.md.

## Umfang einer Änderung

Gilt für jedes Modell (Fable neigt besonders dazu) und gehört in jeden Plan für Subagenten:

- **Knapp planen:** Reicht die Information zum Handeln, handeln. Geklärtes nicht neu herleiten, getroffene Entscheide nicht neu aufrollen, keine Optionen aufzählen, die nicht genommen werden; bei einer Wahl eine Empfehlung statt einer Übersicht. Ein langes Ergebnis nicht erst ganz im Kopf entwerfen und dann nochmals ausschreiben.
- **Nur ändern, was die Aufgabe verlangt.** Gezielte Änderungen statt ganze Dateien neu zu schreiben; Prüfskripte nicht als feste Tests einchecken, Tests nur auf Verhalten (siehe «Tests»).
- **Nebenbefunde melden, nicht nebenbei umsetzen:** veralteter Code oder Kommentar, Fehler, fehlende Tests, Aufräumbedarf kommen am Ende als Liste in den Bericht. Goran oder ein eigener Schritt entscheidet.
- **Umgesetzt wird ein Nebenbefund nur in eigenen Produkten**, als eigener Commit mit eigenem Test, getrennt von der eigentlichen Änderung.
- **Nie nebenbei** in Kundencode (etwa Druckdaten-Tool), in Plugins, die bei wordpress.org in Prüfung liegen, und in den Läufen auf dem Server (find-jobs-lauf: Code-Lauf baut keine neuen Funktionen).

## Python

- Immer `uv`, nie `pip` direkt. Passt die Python-Version nicht, holt uv sie: `uv python install 3.13`, `uv venv --python 3.13`, `uv run --python 3.13`. Nicht aufgeben, bevor diese Wege versucht sind.

## GitHub-Inhalte

- github.com-Inhalte (README, Dateien, Issues, Releases) mit `gh` lesen: `gh repo view OWNER/REPO`, `gh api repos/OWNER/REPO/contents/PFAD`, sonst `gh api`. Grund: eingeloggt, Rohinhalt, private Repos, kein Ratenlimit. Jina Reader nur für Seiten ausserhalb von GitHub.

## Lokale Modelle (Ollama)

- Ollama immer über `http://127.0.0.1:11434` ansprechen, nicht `localhost`: Ollama hört nur auf IPv4, `localhost` löst zuerst IPv6 auf und endet in «Connection refused». `OLLAMA_API_BASE` und `OLLAMA_HOST` stehen in `~/.bashrc`.
- Eigenes Modell per Modelfile: das Template muss `{{ .Tools }}` und `{{ .ToolCalls }}` enthalten, sonst meldet Ollama «does not support tools».
- Modelle mit 1 bis 4 Milliarden Parametern können Tool-Aufrufe auswählen, aber nicht über Code nachdenken; für Coding-Aufgaben ein Cloud-Modell nehmen. Für einen Agenten-Loop mit kleinem Modell reicht eine einfache Schleife über Ollama und MCP statt eines Frameworks.

## llama_index mit Nicht-OpenAI-Anbietern

Die OpenAI-Integration von llama_index ist nicht generisch OpenAI-kompatibel; bei Mistral und anderen kompatiblen APIs scheitern:

1. `openai_modelname_to_contextsize` (ValueError bei unbekanntem Modell): Kontextgrösse selbst setzen
2. `is_chat_model` und `is_function_calling_model` liefern False: auf True zwingen
3. `tiktoken.encoding_for_model` (KeyError): Rückfall auf `cl100k_base`
4. `tool_choice`: Mistral braucht `"any"` statt `"auto"` für erzwungene Tool-Aufrufe

Provider-unabhängig ist das Vercel AI SDK.

## Container und APIs

- Container-Start mit Migrationen und Superuser dauert rund eine Minute, erst danach testen.
- Umgebungsvariablen überschreiben gespeicherte App-Konfiguration nicht immer; den tatsächlichen Wert über die API prüfen und per PATCH setzen.
- CSRF-Fehler bei curl-Aufrufen: Browser-Session oder Token-Header verwenden.
