# Shell-Aliase dieses Repos.
# Wird von ~/.bashrc am Ende gesourced:
#   [ -f "$HOME/projects/tools/.bashrc" ] && source "$HOME/projects/tools/.bashrc"

# Telegram als Kanal, sonst holt der Bot Nachrichten ab, ohne sie an die Sitzung weiterzugeben. Den Bot hält nur
# eine Sitzung: Läuft schon eine mit Kanal (etwa die Akquise-Sitzung), startet die neue ohne Telegram-Plugin,
# sonst übernähme sie den Bot und die laufende Sitzung hörte die Gruppe nicht mehr (Tests: test_bashrc.py).
claude() {
  if pgrep -f -- '[-]-channels plugin:telegram' >/dev/null; then
    command claude --settings '{"enabledPlugins":{"telegram@claude-plugins-official":false}}' \
      --allow-dangerously-skip-permissions "$@"
  else
    command claude --channels plugin:telegram@claude-plugins-official --allow-dangerously-skip-permissions "$@"
  fi
}
alias ll='ls -lha --color=auto'
