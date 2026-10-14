"""Plugin-Rückgaben müssen Codex' striktem Vertrag entsprechen und Sicherheitsfeedback bewahren."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "hooks/codex-hook-ausgabe.py"
STOP_SCHEMA = json.loads((ROOT / "tests/fixtures/codex-0.162.1-stop.schema.json").read_text())


class HookAusgabe(unittest.TestCase):
    def aufruf(self, ausgabe, *, ereignis="Stop", status=0, fehler=""):
        programm = (f"import sys; sys.stdout.write({ausgabe!r}); "
                    f"sys.stderr.write({fehler!r}); sys.exit({status})")
        return subprocess.run([sys.executable, str(ADAPTER), "--", sys.executable, "-c", programm],
                              input=json.dumps({"hook_event_name": ereignis, "turn_id": "pruefung"}),
                              capture_output=True, text=True)

    def assert_stop_schema(self, stdout):
        aus = json.loads(stdout)
        self.assertIsInstance(aus, dict)
        self.assertFalse(set(aus) - set(STOP_SCHEMA["properties"]), f"Unzulässige Stop-Felder: {list(aus)}")
        for name, wert in aus.items():
            typ = STOP_SCHEMA["properties"][name].get("type")
            if typ:
                self.assertIsInstance(wert, {"string": str, "boolean": bool}[typ])
        if "decision" in aus:
            self.assertEqual(aus["decision"], "block")
            self.assertTrue(aus.get("reason", "").strip())
        return aus

    def test_stop_entfernt_nur_claude_telemetrie(self):
        r = self.aufruf(json.dumps({"metrics": {"skipped": True}, "rewakeSummary": "Prüfung beendet"}))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.assert_stop_schema(r.stdout), {})

    def test_stop_blockierung_und_benutzermeldung_bleiben_erhalten(self):
        r = self.aufruf(json.dumps({"metrics": {}, "decision": "block", "reason": "Lücke schliessen",
                                   "systemMessage": "Sicherheitsprüfung meldet einen Befund"}))
        self.assertEqual(r.returncode, 0, r.stderr)
        aus = self.assert_stop_schema(r.stdout)
        self.assertEqual(aus["decision"], "block")
        self.assertEqual(aus["reason"], "Lücke schliessen")
        self.assertIn("Sicherheitsprüfung", aus["systemMessage"])

    def test_posttool_warnung_bleibt_erhalten(self):
        feedback = {"hookEventName": "PostToolUse", "additionalContext": "Kein eval verwenden"}
        r = self.aufruf(json.dumps({"metrics": {"hits": 1}, "hookSpecificOutput": feedback}),
                        ereignis="PostToolUse")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"hookSpecificOutput": feedback})

    def test_sessionstart_claude_async_vorspann_wird_in_ein_objekt_uebersetzt(self):
        feedback = {"hookEventName": "SessionStart", "additionalContext": "Prüfer ist verfügbar"}
        ausgabe = (json.dumps({"async": True, "asyncTimeout": 180000}) + "\n" +
                   json.dumps({"metrics": {"sdk_bootstrap": 1}, "hookSpecificOutput": feedback}))
        r = self.aufruf(ausgabe, ereignis="SessionStart")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"hookSpecificOutput": feedback})

    def test_exit_zwei_mit_sicherheitshinweis_bleibt_blockierend(self):
        r = self.aufruf("", status=2, fehler="SQL-Injection beheben")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stderr, "SQL-Injection beheben")

    def test_erfindet_bei_fehlerhafter_plugin_ausgabe_keine_freigabe(self):
        r = self.aufruf("kaputtes JSON")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("JSON", r.stderr)

    def test_leere_erfolgreiche_stop_ausgabe_liefert_freigabe_json(self):
        r = self.aufruf("")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.assert_stop_schema(r.stdout), {})

    def test_einrichtung_ist_idempotent_und_laesst_claude_unveraendert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex = root / ".codex"
            relativ = Path("plugins/cache/claude-plugins-official/security-guidance/2.0.13/hooks/sg-python.sh")
            original = b'#!/bin/sh\nprintf "%s" "{}"\n'
            for home in (codex, root / ".claude"):
                ziel = home / relativ
                ziel.parent.mkdir(parents=True)
                ziel.write_bytes(original)
                ziel.chmod(0o755)
            for _ in range(2):
                r = subprocess.run([sys.executable, str(ADAPTER), "--einrichten", "--codex-home", str(codex)],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                inhalt = (codex / relativ).read_bytes()
                if _ == 0:
                    zuerst = inhalt
                else:
                    self.assertEqual(inhalt, zuerst)
            self.assertIn(b"codex-hook-ausgabe.py", inhalt)
            self.assertEqual((root / ".claude" / relativ).read_bytes(), original)
            self.assertEqual((codex / relativ).stat().st_mode & 0o777, 0o755)

    def test_installierter_security_stop_erfuellt_das_echte_codex_schema(self):
        home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        versionen = list((home / "plugins/cache/claude-plugins-official/security-guidance").glob("*/hooks/sg-python.sh"))
        if not versionen:
            self.skipTest("security-guidance ist nicht installiert")
        shim = max(versionen, key=lambda p: p.stat().st_mtime)
        plugin = shim.parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PLUGIN_ROOT=str(plugin), CLAUDE_PLUGIN_ROOT=str(plugin),
                       SECURITY_WARNINGS_STATE_DIR=tmp)
            env.pop("CODEX_HOOK_AUSGABE_AKTIV", None)
            r = subprocess.run(["bash", str(shim), str(plugin / "hooks/security_reminder_hook.py")],
                               input=json.dumps({"hook_event_name": "Stop", "stop_hook_active": True,
                                                 "session_id": "schema-pruefung", "turn_id": "schema-pruefung"}),
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assert_stop_schema(r.stdout)


if __name__ == "__main__":
    unittest.main()
