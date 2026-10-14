#!/usr/bin/env python3
"""Codex-apply_patch an die vorhandenen Edit/Write-Regeln von security-guidance weiterreichen.

Die ursprünglichen Plugin-Hooks bleiben aktiv. Dieser Zusatz schliesst nur deren Lücke bei apply_patch;
es werden weder Plugin-Quellen verändert noch Sicherheitsprüfungen abgeschaltet.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib


def plugin_root():
    basis = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    config = basis / "config.toml"
    if config.exists():
        einstellungen = tomllib.loads(config.read_text())
        if not einstellungen.get("plugins", {}).get("security-guidance@claude-plugins-official", {}).get("enabled", False):
            return None
    versionen = list((basis / "plugins/cache/claude-plugins-official/security-guidance").glob("*/hooks/sg-python.sh"))
    if not versionen:
        raise FileNotFoundError("Das aktivierte Plugin security-guidance ist nicht installiert.")
    return max(versionen, key=lambda p: tuple(int(x) for x in re.findall(r"\d+", p.parent.parent.name))).parent.parent


def dateien(patch):
    aktuell = None
    for zeile in patch.splitlines():
        for kennung, typ in (("*** Update File: ", "Edit"), ("*** Add File: ", "Write"), ("*** Delete File: ", "Edit")):
            if zeile.startswith(kennung):
                if aktuell:
                    yield aktuell
                aktuell = [typ, zeile[len(kennung):], []]
                break
        else:
            if aktuell and zeile.startswith("*** Move to: "):
                aktuell[1] = zeile[len("*** Move to: "):]
            elif aktuell and zeile.startswith("+"):
                aktuell[2].append(zeile[1:])
    if aktuell:
        yield aktuell


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path)
    args = parser.parse_args()
    eingabe = json.loads(sys.stdin.read())
    argumente = eingabe.get("tool_input", {})
    patch = argumente if isinstance(argumente, str) else argumente.get("command", "")
    root = args.plugin_root or plugin_root()
    if root is None:
        print("{}")
        return 0
    kontexte = []
    meldungen = []
    status = 0
    for typ, pfad, zeilen in dateien(patch):
        ziel = Path(eingabe.get("cwd", os.getcwd())) / pfad
        transformiert = dict(eingabe, tool_name=typ, tool_input={
            "file_path": str(ziel), "content" if typ == "Write" else "new_string": "\n".join(zeilen)})
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(root), PLUGIN_ROOT=str(root),
                   CLAUDE_PROJECT_DIR=eingabe.get("cwd", os.getcwd()))
        r = subprocess.run(["bash", str(root / "hooks/sg-python.sh"),
                            str(root / "hooks/security_reminder_hook.py")],
                           input=json.dumps(transformiert), capture_output=True, text=True, env=env)
        if r.stderr:
            print(r.stderr, file=sys.stderr, end="")
        if r.returncode:
            status = r.returncode
        if r.stdout.strip():
            aus = json.loads(r.stdout)
            kontext = aus.get("hookSpecificOutput", {}).get("additionalContext")
            if kontext:
                kontexte.append(kontext)
            if aus.get("systemMessage"):
                meldungen.append(aus["systemMessage"])
    ausgabe = {}
    if kontexte:
        ausgabe["hookSpecificOutput"] = {"hookEventName": "PostToolUse", "additionalContext": "\n\n".join(kontexte)}
    if meldungen:
        ausgabe["systemMessage"] = "\n".join(meldungen)
    print(json.dumps(ausgabe, ensure_ascii=False))
    return status


if __name__ == "__main__":
    sys.exit(main())
