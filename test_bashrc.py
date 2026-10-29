"""Tests für die Funktion claude in .bashrc: nur eine Sitzung bindet den Telegram-Bot an.

Aufruf: python3 -m unittest test_bashrc.py
"""
import os, subprocess, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).parent


def aufruf(kanal_laeuft: bool) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        bin_ = Path(tmp)
        (bin_ / "claude").write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
        (bin_ / "pgrep").write_text(f"#!/bin/sh\nexit {0 if kanal_laeuft else 1}\n")
        for f in bin_.iterdir():
            f.chmod(0o755)
        env = {**os.environ, "PATH": f"{tmp}:{os.environ['PATH']}"}
        return subprocess.run(["bash", "-c", f'source "{HERE / ".bashrc"}"; claude --resume x'],
                              env=env, capture_output=True, text=True, check=True).stdout


class ClaudeMitTelegram(unittest.TestCase):
    def test_erste_sitzung_bekommt_den_telegram_kanal(self):
        args = aufruf(kanal_laeuft=False).splitlines()
        self.assertIn("--channels", args)
        self.assertEqual(args[args.index("--channels") + 1], "plugin:telegram@claude-plugins-official")
        self.assertEqual(args[-2:], ["--resume", "x"])

    def test_zweite_sitzung_schaltet_das_plugin_ab_statt_den_bot_zu_uebernehmen(self):
        args = aufruf(kanal_laeuft=True).splitlines()
        self.assertNotIn("--channels", args)
        settings = args[args.index("--settings") + 1]
        self.assertIn('"telegram@claude-plugins-official":false', settings)
        self.assertIn("--allow-dangerously-skip-permissions", args)
        self.assertEqual(args[-2:], ["--resume", "x"])


if __name__ == "__main__":
    unittest.main()
