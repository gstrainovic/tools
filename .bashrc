# Shell-Aliase dieses Repos.
# Wird von ~/.bashrc am Ende gesourced:
#   [ -f "$HOME/projects/tools/.bashrc" ] && source "$HOME/projects/tools/.bashrc"

# Telegram als Kanal, sonst holt der Bot Nachrichten ab, ohne sie an die Sitzung weiterzugeben.
alias claude="claude --channels plugin:telegram@claude-plugins-official --allow-dangerously-skip-permissions --resume"
alias ll='ls -lha --color=auto'
