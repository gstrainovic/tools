#!/usr/bin/env bash
# PreCompact: Der JSON-Pfad wird von Claude und Codex geliefert; keine Umgebungsvariable erforderlich.
set -euo pipefail
ein=$(cat)
transkript=$(jq -r '.transcript_path // empty' <<<"$ein")
if [ -n "$transkript" ] && [ -r "$transkript" ]; then
  kopie=$(mktemp "${transkript%.jsonl}-backup-XXXXXXXX.jsonl")
  cp -- "$transkript" "$kopie"
fi
printf '{}\n'
