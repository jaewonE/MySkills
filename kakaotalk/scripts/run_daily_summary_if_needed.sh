#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_FILE="$HOME/.kakao_daily_summary/last_run"
CONFIG="${KAKAO_SUMMARY_CONFIG:-$ROOT/kakao_daily_summary.config.json}"
TIMEZONE="${KAKAO_SUMMARY_TIMEZONE:-Asia/Seoul}"
TODAY="$(TZ="$TIMEZONE" date +%F)"

timestamp() {
  TZ="$TIMEZONE" date "+%Y-%m-%dT%H:%M:%S%z"
}

log_line() {
  local level="$1"
  local message="$2"
  printf '[%s] level=%s component=kakao-daily-summary pid=%s %s\n' "$(timestamp)" "$level" "$$" "$message"
}

log_file_lines() {
  local level="$1"
  local file="$2"
  while IFS= read -r line || [[ -n "$line" ]]; do
    log_line "$level" "$line"
  done < "$file"
}

if [[ -f "$STATE_FILE" ]] && [[ "$(tr -d '[:space:]' < "$STATE_FILE")" == "$TODAY" ]]; then
  exit 0
fi

stdout_file="$(mktemp)"
stderr_file="$(mktemp)"
trap 'rm -f "$stdout_file" "$stderr_file"' EXIT

log_line "INFO" "summary_run_started config=$CONFIG"
if python3 "$ROOT/scripts/kakao_daily_summary.py" --config "$CONFIG" --all-enabled --reset-display-dir >"$stdout_file" 2>"$stderr_file"; then
  log_file_lines "INFO" "$stdout_file"
  log_file_lines "ERROR" "$stderr_file" >&2
  log_line "INFO" "summary_run_finished status=0"
  exit 0
fi

status=$?
log_file_lines "INFO" "$stdout_file"
log_file_lines "ERROR" "$stderr_file" >&2
log_line "ERROR" "summary_run_finished status=$status" >&2
exit "$status"
