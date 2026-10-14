#!/usr/bin/env python3
"""Claude-Plugin-Ausgaben für Codex bereinigen; Entscheidungen und Sicherheitsmeldungen erhalten."""
import argparse
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile

MARKIERUNG = "# Codex-JSON-Adapter aus projects/tools"


def einrichten(home):
    cache = home / "plugins/cache/claude-plugins-official"
    adapter = shlex.quote(str(Path(__file__).resolve()))
    for plugin, datei, shell in (("security-guidance", "sg-python.sh", "bash"),
                                  ("claude-security", "hooks.sh", "sh")):
        for ziel in sorted((cache / plugin).glob(f"*/hooks/{datei}")):
            inhalt = ziel.read_text()
            if MARKIERUNG in inhalt:
                continue
            bedingung = '[ "${CODEX_HOOK_AUSGABE_AKTIV:-}" != 1 ]'
            zusatz = (f"{MARKIERUNG}\nif {bedingung}; then\n"
                      "  export CODEX_HOOK_AUSGABE_AKTIV=1\n"
                      f'  exec uv run --no-project python {adapter} -- {shell} "$0" "$@"\n'
                      "fi\n")
            erste, rest = inhalt.split("\n", 1)
            sicherung = ziel.with_name(ziel.name + ".vor-codex-adapter")
            if not sicherung.exists():
                sicherung.write_bytes(ziel.read_bytes())
                sicherung.chmod(stat.S_IMODE(ziel.stat().st_mode))
            # Atomar ersetzen: auch bei gemeinsam genutzten Inodes bleibt die Claude-Kopie unverändert.
            with tempfile.NamedTemporaryFile("w", dir=ziel.parent, delete=False) as f:
                f.write(erste + "\n" + zusatz + rest)
                temp = Path(f.name)
            temp.chmod(stat.S_IMODE(ziel.stat().st_mode))
            os.replace(temp, ziel)
            print(f"Codex-Ausgabeadapter eingerichtet: {ziel}")


def ausfuehren(befehl):
    eingabe = sys.stdin.read()
    payload = json.loads(eingabe)
    r = subprocess.run(befehl, input=eingabe, capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    if r.returncode:
        sys.stdout.write(r.stdout)
        return r.returncode if r.returncode > 0 else 128 - r.returncode
    stdout = r.stdout
    if payload.get("hook_event_name") == "SessionStart" and stdout.strip():
        try:
            erste, ende = json.JSONDecoder().raw_decode(stdout.lstrip())
            if (isinstance(erste, dict) and erste.get("async") is True
                    and set(erste) <= {"async", "asyncTimeout"}):
                # Claude kündigt Hintergrundarbeit mit einem eigenen JSON-Objekt an.
                # Codex erwartet nach Prozessende ein einziges Ereignisergebnis.
                stdout = stdout.lstrip()[ende:].strip()
        except json.JSONDecodeError:
            pass
    try:
        ausgabe = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError:
        if payload.get("hook_event_name") in ("Stop", "SubagentStop"):
            print("Plugin liefert ungültiges Stop-JSON; keine Freigabe erzeugt.", file=sys.stderr)
            return 1
        # Bei Ereignissen wie SessionStart ist Text als Kontext zulässig.
        sys.stdout.write(r.stdout)
        return 0
    if not isinstance(ausgabe, dict):
        print("Plugin liefert kein JSON-Objekt; keine Freigabe erzeugt.", file=sys.stderr)
        return 1
    # Nur Claude-Telemetrie entfernen. Unbekannte Steuerfelder nicht stillschweigend verwerfen.
    ausgabe.pop("metrics", None)
    ausgabe.pop("rewakeSummary", None)
    print(json.dumps(ausgabe, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--einrichten", action="store_true")
    parser.add_argument("--codex-home", type=Path,
                        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("befehl", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.einrichten:
        einrichten(args.codex_home)
        return 0
    befehl = args.befehl[1:] if args.befehl[:1] == ["--"] else args.befehl
    if not befehl:
        parser.error("Nach -- fehlt der Plugin-Befehl.")
    return ausfuehren(befehl)


if __name__ == "__main__":
    sys.exit(main())
