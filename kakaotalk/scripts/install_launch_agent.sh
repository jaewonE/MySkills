#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.jaewone.kakao-daily-summary"
SRC="$ROOT/launchd/$LABEL.plist"
DST="$HOME/Library/LaunchAgents/$LABEL.plist"
LAUNCHD_PATH="${KAKAO_DAILY_SUMMARY_LAUNCHD_PATH:-$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin}"

if [[ ! -f "$ROOT/kakao_daily_summary.config.json" ]]; then
  echo "ERROR: missing $ROOT/kakao_daily_summary.config.json" >&2
  echo "Create a local config first: cp kakao_daily_summary.config.example.json kakao_daily_summary.config.json" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"
chmod +x "$ROOT/scripts/kakao_daily_summary.py"
sed \
  -e "s#__ROOT__#$ROOT#g" \
  -e "s#__PATH__#$LAUNCHD_PATH#g" \
  "$SRC" > "$DST"

launchctl bootout "gui/$(id -u)" "$DST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$DST"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started $LABEL"
echo "stdout: $ROOT/logs/kakao-daily-summary.out.log"
echo "stderr: $ROOT/logs/kakao-daily-summary.err.log"
