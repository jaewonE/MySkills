#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$HOME/.codex/skills/kakaotalk}"

if ! command -v rsync >/dev/null 2>&1; then
  echo "ERROR: rsync is required to install the Codex skill package" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")" "$DEST"

rsync -a --delete \
  --exclude '.git/' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'kakao_daily_summary.config.json' \
  --exclude 'history/' \
  --exclude 'logs/' \
  "$ROOT/" "$DEST/"

echo "Installed Codex skill package at $DEST"
echo "Restart Codex to reload the skill list."
