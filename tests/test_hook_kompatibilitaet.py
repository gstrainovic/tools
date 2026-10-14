"""Die gemeinsamen Hooks mit Eingaben und Protokollen beider Programme ausführen."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HOOKS = Path(__file__).resolve().parents[1] / "hooks"


class Kompatibilitaet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.protokoll = Path(self.tmp.name) / "sitzung mit leerzeichen.jsonl"
        self.schreibe({"type": "response_item", "payload": {
            "type": "message", "role": "user", "content": [{"type": "input_text", "text": "Prüfe das"}]}})

    def schreibe(self, *zeilen):
        self.protokoll.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")

    def aufruf(self, hook, werkzeug="Bash", eingabe=None, **felder):
        payload = {"hook_event_name": "PreToolUse", "tool_name": werkzeug,
                   "tool_input": eingabe or {}, "transcript_path": str(self.protokoll), **felder}
        r = subprocess.run(["bash", str(HOOKS / hook)], input=json.dumps(payload),
                           capture_output=True, text=True, env={k: v for k, v in os.environ.items()
                                                               if k != "TRANSCRIPT_PATH"})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else {}

    def kontext(self, *args, **kwargs):
        return self.aufruf(*args, **kwargs).get("hookSpecificOutput", {}).get("additionalContext", "")

    def test_codex_agentenauftrag_wird_geprueft(self):
        aus = self.aufruf("agent-auftrag.sh", "spawn_agent", {"message": "Erstelle ein Video"})
        self.assertEqual(aus.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")

    def test_codex_modellwahl_nennt_keine_claude_modellaliase(self):
        kontext = self.kontext("modellwahl.sh", "spawn_agent", {"message": "Prüfe den Code"})
        self.assertIn("Codex", kontext)
        self.assertNotIn("model=fable", kontext)
        self.assertNotIn("model=opus", kontext)

    def test_codex_agentenrecherche_ohne_lokale_suche_blockiert(self):
        aus = self.aufruf("erst-lokal.sh", "spawn_agent", {"message": "Recherchiere im Web"})
        self.assertEqual(aus.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")

    def test_codex_lokale_suche_zaehlt_bis_zum_naechsten_prompt(self):
        nutzer = {"type": "response_item", "payload": {"type": "message", "role": "user",
                  "content": [{"type": "input_text", "text": "Prüfe das"}]}}
        suche = {"type": "response_item", "payload": {"type": "function_call", "name": "exec_command",
                 "arguments": json.dumps({"cmd": "rg thema ~/projects"})}}
        for neu, entscheid in ((False, None), (True, "deny")):
            self.schreibe(nutzer, suche, *([nutzer] if neu else []))
            aus = self.aufruf("erst-lokal.sh", "WebSearch", {"query": "thema"})
            self.assertEqual(aus.get("hookSpecificOutput", {}).get("permissionDecision"), entscheid)

    def test_codex_skillempfehlung_fuer_mehrere_patchdateien(self):
        patch = "*** Begin Patch\n*** Update File: /projekt/TODO.md\n@@\n-a\n+b\n*** Add File: /projekt/test.sh\n+true\n*** End Patch"
        kontext = self.kontext("skill-hinweis.sh", "apply_patch", {"command": patch}, turn_id="t")
        self.assertIn("Skill doku-pflege laden", kontext)
        self.assertIn("Skill entwicklung laden", kontext)
        self.assertIn("SKILL.md", kontext)

    def test_codex_todo_nur_lesen_gilt_nicht_als_dokumentierter_befund(self):
        self.schreibe({"type": "response_item", "payload": {"type": "function_call", "name": "exec_command",
                       "arguments": json.dumps({"cmd": "cat /projekt/TODO.md"})}})
        aus = self.aufruf("befunde-eingetragen.sh", hook_event_name="Stop",
                          last_assistant_message="Befunde: Der Export ist defekt.")
        self.assertEqual(aus.get("decision"), "block")

    def test_claude_todo_nur_lesen_gilt_nicht_als_dokumentierter_befund(self):
        for name, eingabe in (("Read", {"file_path": "/projekt/TODO.md"}),
                              ("Bash", {"command": "cat /projekt/TODO.md"})):
            with self.subTest(werkzeug=name):
                self.schreibe({"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "name": name, "input": eingabe}]}})
                aus = self.aufruf("befunde-eingetragen.sh", hook_event_name="Stop",
                                  last_assistant_message="Befunde: Der Export ist defekt.")
                self.assertEqual(aus.get("decision"), "block")

    def test_codex_todo_lesen_mit_stderr_umleitung_zaehlt_nicht_als_aenderung(self):
        self.schreibe({"type": "response_item", "payload": {"type": "function_call", "name": "exec_command",
                       "arguments": json.dumps({"cmd": "cat /projekt/TODO.md 2>/dev/null"})}})
        aus = self.aufruf("befunde-eingetragen.sh", hook_event_name="Stop",
                          last_assistant_message="Befunde: Der Export ist defekt.")
        self.assertEqual(aus.get("decision"), "block")

    def test_codex_echter_todo_patch_gilt_als_dokumentation(self):
        self.schreibe({"type": "response_item", "payload": {"type": "custom_tool_call", "name": "apply_patch",
                       "input": "*** Begin Patch\n*** Update File: /projekt/TODO.md\n@@\n+a\n*** End Patch"}})
        self.assertEqual(self.aufruf("befunde-eingetragen.sh", hook_event_name="Stop",
                                    last_assistant_message="Befunde: Der Export ist defekt."), {})

    def test_codex_gelesener_skill_loest_keinen_erneuten_hinweis_aus(self):
        self.schreibe({"type": "response_item", "payload": {"type": "function_call", "name": "exec_command",
                       "arguments": json.dumps({"cmd": "cat /home/g/.agents/skills/doku-pflege/SKILL.md"})}})
        kontext = self.kontext("skill-hinweis.sh", "apply_patch",
                              {"command": "*** Begin Patch\n*** Update File: /projekt/TODO.md\n*** End Patch"})
        self.assertNotIn("Skill doku-pflege laden", kontext)

    def test_codex_browser_bekommt_portalskill_hinweis(self):
        kontext = self.kontext("skill-hinweis.sh", "mcp__cua_repl__js",
                              {"code": "await tab.goto('https://www.upwork.com/nx/proposals/');"})
        self.assertIn("Skill browser-wahl laden", kontext)
        self.assertIn("Skill upwork laden", kontext)

    def test_sicherung_verwendet_json_pfad_ohne_umgebungsvariable(self):
        inhalt = self.protokoll.read_bytes()
        for _ in range(2):
            self.aufruf("transkript-sichern.sh", hook_event_name="PreCompact")
        kopien = list(Path(self.tmp.name).glob("*-backup-*.jsonl"))
        self.assertEqual(len(kopien), 2)
        for kopie in kopien:
            self.assertEqual(kopie.read_bytes(), inhalt)
        self.assertEqual(self.protokoll.read_bytes(), inhalt)


if __name__ == "__main__":
    unittest.main()
