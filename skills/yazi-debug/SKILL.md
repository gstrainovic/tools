---
name: yazi-debug
description: Yazi (Dateimanager im Terminal) debuggen und fernsteuern (feste Client-ID, ya emit-to, Debug-Log). Laden, bevor yazi gestartet, per ya gesteuert oder ein Yazi-Plugin untersucht wird.
---

# Yazi debuggen

- Yazi läuft **nicht** in einer headless tmux-Session (`tmux new-session -d`): Das Log meldet `Terminal failed to respond to DA1 … TimedOut`. Der Nutzer startet yazi im echten Terminal, Claude steuert danach per `ya`.
- Start mit fester Client-ID: `yazi --client-id 1337` (die ID muss global eindeutig sein).
- Aktionen an diese Instanz: `ya emit-to 1337 <Aktion> [Argumente …]`. Plugin-Argumente stehen positional hinter dem Plugin-Namen, nicht als `--args=…`, z. B. `ya emit-to 1337 plugin toggle-pane max-preview`. Manche Plugins tun ohne Argument nichts.
- Debug-Log: `YAZI_LOG=debug yazi --client-id 1337` schreibt nach `~/.local/state/yazi/yazi.log`.
- Installierte Plugin-Pakete liegen unter `~/.local/state/yazi/packages/`.
- Konfiguration: `~/.config/yazi` ist ein Symlink auf `~/projects/tools/.config/yazi`. Das Ziel ist aus dem tools-Repo entfernt, yazi läuft darum mit der Standardkonfiguration. Eine eigene Konfiguration gehört nicht mehr ins tools-Repo.
