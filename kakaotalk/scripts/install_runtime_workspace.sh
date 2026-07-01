#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_RUNTIME_ROOT="$HOME/Library/Application Support/kakaotalk-summary"
INSTALL_LAUNCHD=0
RUNTIME_ROOT="${KAKAO_SUMMARY_RUNTIME_ROOT:-$DEFAULT_RUNTIME_ROOT}"

usage() {
  cat <<'EOF'
Usage: scripts/install_runtime_workspace.sh [--install-launchd] [runtime-root]

Creates or updates a user-local runtime workspace for KakaoTalk summaries.
The runtime workspace stores private config, history, and logs outside the
Codex skill package.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-launchd)
      INSTALL_LAUNCHD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      RUNTIME_ROOT="$1"
      shift
      ;;
  esac
done

if ! command -v rsync >/dev/null 2>&1; then
  echo "ERROR: rsync is required to create the runtime workspace" >&2
  exit 1
fi

mkdir -p "$RUNTIME_ROOT/scripts" "$RUNTIME_ROOT/launchd" "$RUNTIME_ROOT/history" "$RUNTIME_ROOT/logs"

SOURCE_REAL="$(cd "$SOURCE_ROOT" && pwd -P)"
RUNTIME_REAL="$(cd "$RUNTIME_ROOT" && pwd -P)"

if [[ "$SOURCE_REAL" != "$RUNTIME_REAL" ]]; then
  rsync -a --delete \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    "$SOURCE_ROOT/scripts/" "$RUNTIME_ROOT/scripts/"

  rsync -a --delete "$SOURCE_ROOT/launchd/" "$RUNTIME_ROOT/launchd/"
  install -m 0644 "$SOURCE_ROOT/kakao_daily_summary.config.example.json" "$RUNTIME_ROOT/kakao_daily_summary.config.example.json"

  if [[ ! -f "$RUNTIME_ROOT/summary_prompt.md" ]]; then
    install -m 0644 "$SOURCE_ROOT/summary_prompt.md" "$RUNTIME_ROOT/summary_prompt.md"
  fi
fi

CREATED_CONFIG=0
if [[ ! -f "$RUNTIME_ROOT/kakao_daily_summary.config.json" ]]; then
  install -m 0644 "$SOURCE_ROOT/kakao_daily_summary.config.example.json" "$RUNTIME_ROOT/kakao_daily_summary.config.json"
  CREATED_CONFIG=1
fi

chmod +x "$RUNTIME_ROOT/scripts/"*.py "$RUNTIME_ROOT/scripts/"*.sh

echo "Runtime workspace: $RUNTIME_ROOT"
echo "Config: $RUNTIME_ROOT/kakao_daily_summary.config.json"
echo "History: $RUNTIME_ROOT/history"
echo "Logs: $RUNTIME_ROOT/logs"

if [[ "$CREATED_CONFIG" -eq 1 ]]; then
  echo "Created example config. Edit it with real chat_id values before enabling launchd."
fi

if [[ "$INSTALL_LAUNCHD" -eq 1 ]]; then
  if [[ "$CREATED_CONFIG" -eq 1 ]]; then
    echo "ERROR: refusing to install launchd with a newly created example config" >&2
    echo "Edit $RUNTIME_ROOT/kakao_daily_summary.config.json, then run:" >&2
    echo "  \"$RUNTIME_ROOT/scripts/install_launch_agent.sh\"" >&2
    exit 1
  fi
  "$RUNTIME_ROOT/scripts/install_launch_agent.sh"
fi
