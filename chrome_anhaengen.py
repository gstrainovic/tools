#!/usr/bin/env python3
"""playwright-cli an Gorans laufenden Chrome hängen, über die Playwright Extension ohne Freigabedialog.

Aufruf: chrome-anhaengen [--session gchrome]

Läuft die Session schon, bleibt sie (nie schliessen). Sonst `playwright-cli attach --extension=chrome` mit dem Token
aus ~/.config/playwright-extension/token (PLAYWRIGHT_MCP_EXTENSION_TOKEN): Mit Token verbindet die Erweiterung ohne
Rückfrage. Die Session sieht nur die Tabs ihrer eigenen Tabgruppe, Gorans übrige Tabs nicht. Einrichtung (Erweiterung
per Chrome-Richtlinie, Token): Skill browser-wahl, «Gorans Chrome anhängen».
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def session_laeuft(session: str) -> bool:
    r = subprocess.run(["playwright-cli", f"-s={session}", "tab-list"], capture_output=True, text=True)
    return r.returncode == 0 and "is not open" not in r.stdout + r.stderr


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--session", default="gchrome")
    s = ap.parse_args().session
    if session_laeuft(s):
        print(f"Session {s} läuft schon")
        return 0
    datei = Path.home() / ".config" / "playwright-extension" / "token"
    if not datei.is_file():
        print(f"FEHLER: kein token in {datei} (Skill browser-wahl, «Gorans Chrome anhängen»)", file=sys.stderr)
        return 1
    env = {**os.environ, "PLAYWRIGHT_MCP_EXTENSION_TOKEN": datei.read_text().strip()}
    r = subprocess.run(["playwright-cli", "attach", "--extension=chrome", f"--session={s}"],
                       env=env, capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not session_laeuft(s):
        print(f"FEHLER: Anhängen gescheitert\n{r.stdout[-500:]}{r.stderr[-500:]}", file=sys.stderr)
        return 1
    print(f"Session {s} angehängt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
