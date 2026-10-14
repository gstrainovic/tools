"""Codex-Patches erreichen die vorhandenen Sicherheitsregeln des Plugins."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ADAPTER = Path(__file__).resolve().parents[1] / "hooks" / "security-guidance-codex.py"


class SecurityGuidance(unittest.TestCase):
    def test_echte_pluginregeln_warnen_vor_eval_im_codex_patch(self):
        basis = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        plugins = list((basis / "plugins/cache/claude-plugins-official/security-guidance").glob(
            "*/hooks/security_reminder_hook.py"))
        if not plugins:
            self.skipTest("security-guidance ist nicht installiert")
        original = max(plugins, key=lambda p: p.stat().st_mtime)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks = root / "hooks"
            hooks.mkdir()
            # Echte Regeln und Zustandsverwaltung; der Test startet keinen SDK-Download oder Prüfdienst.
            (hooks / "security_reminder_hook.py").write_text(
                "import sys\n"
                f"sys.path.insert(0, {str(original.parent)!r})\n"
                "import security_reminder_hook as hook\n"
                "hook._maybe_bootstrap_agent_sdk_async = lambda: None\n"
                "hook.main()\n")
            (hooks / "sg-python.sh").write_text(f'exec {sys.executable} "$@"\n')
            patch = "*** Begin Patch\n*** Update File: pruefung.py\n@@\n+eval(eingabe)\n*** End Patch"
            r = subprocess.run([sys.executable, str(ADAPTER), "--plugin-root", str(root)],
                               input=json.dumps({"hook_event_name": "PostToolUse", "tool_name": "apply_patch",
                                                 "session_id": "hook-kompatibilitaet",
                                                 "tool_input": {"command": patch}, "cwd": tmp}),
                               capture_output=True, text=True,
                               env=dict(os.environ, SECURITY_WARNINGS_STATE_DIR=str(root / "zustand")))
            self.assertEqual(r.returncode, 0, r.stderr)
            kontext = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("eval", kontext)
            self.assertIn("security-guidance", kontext)

    def test_patch_mit_mehreren_dateien_wird_als_edit_und_write_geprueft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks = root / "hooks"
            hooks.mkdir()
            (hooks / "security_reminder_hook.py").write_text(
                "import json,sys\nx=json.loads(sys.stdin.read())\n"
                "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PostToolUse',"
                "'additionalContext':x['tool_name']+' '+x['tool_input']['file_path']+' '+"
                "x['tool_input'].get('new_string',x['tool_input'].get('content',''))}}))\n")
            # Der Test verwendet nur das örtliche Ersatzplugin und ruft keinen Prüfdienst auf.
            (hooks / "sg-python.sh").write_text(f'exec {sys.executable} "$@"\n')
            patch = "*** Begin Patch\n*** Update File: src/a.py\n@@\n-alt\n+warnung\n*** Add File: src/b.py\n+neu\n*** End Patch"
            r = subprocess.run([sys.executable, str(ADAPTER), "--plugin-root", str(root)],
                               input=json.dumps({"hook_event_name": "PostToolUse", "tool_name": "apply_patch",
                                                 "tool_input": {"command": patch}, "cwd": tmp}),
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            kontext = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn(f"Edit {tmp}/src/a.py warnung", kontext)
            self.assertIn(f"Write {tmp}/src/b.py neu", kontext)


if __name__ == "__main__":
    unittest.main()
