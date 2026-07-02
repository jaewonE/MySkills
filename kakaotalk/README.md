# Kakao Daily Summary

Automate KakaoTalk chat extraction and daily Gemini summaries on macOS.

The current project reads KakaoTalk messages through `kakaocli`, normalizes the transcript, renders `summary_prompt.md`, calls Gemini through `agy`, and saves Markdown summaries to both a permanent history folder and a Desktop snapshot folder.

## Platform and Prerequisites

This is a macOS-only Codex skill. It depends on two external CLIs:

- Antigravity2, which provides `agy` for Gemini calls.
- `kakaocli`, which reads the local KakaoTalk database.

Install Antigravity2:

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

See the Antigravity2 CLI install documentation: [https://antigravity.google/docs/cli/install](https://antigravity.google/docs/cli/install)

Install `kakaocli`:

```bash
brew install silver-flight-group/tap/kakaocli
```

See the `kakaocli` project page: [https://github.com/silver-flight-group/kakaocli#%EA%B0%9C%EC%9A%94](https://github.com/silver-flight-group/kakaocli#%EA%B0%9C%EC%9A%94)

Both tools require authentication before this skill can run real extraction or summary work.

For Antigravity2, run:

```bash
agy
```

Follow the login instructions shown by `agy`. After login, verify it with:

```bash
agy -p "Reply exactly: PONG"
```

For `kakaocli`, verify it with:

```bash
kakaocli auth
```

If `kakaocli auth` fails and local `clang` is installed, this package can try to infer the internal `KAKAO_USER_ID` from KakaoTalk preference plist SHA-512 revision keys. If that recovery fails, or if `clang` is not installed, authenticate manually:

```bash
kakaocli auth --user-id <KAKAO_USER_ID>
```

The skill records authentication status in the runtime config:

```json
{
  "auth_status": {
    "agy_checked_at": null,
    "kakaocli_checked_at": null
  },
  "kakaocli_user_id": null
}
```

Run the preflight check from the runtime workspace before skill operations:

```bash
scripts/check_auth.py --config kakao_daily_summary.config.json
```

The check updates `auth_status.agy_checked_at` and `auth_status.kakaocli_checked_at` only after successful checks. Failed checks set the matching timestamp back to `null`. A successful timestamp is reused for 5 hours. Within that window, extraction and summary commands skip the preflight check and only force a new check if `kakaocli` or `agy` fails during the real operation. If `kakaocli` recovery succeeds, it also stores the recovered `kakaocli_user_id` in the private runtime config so later extraction commands can pass the right database key derivation input.

## Current Behavior

- Chat target: selected by `kakao_daily_summary.config.json`.
- Date window: yesterday, `00:00:00 <= timestamp < today 00:00:00`, in `Asia/Seoul`.
- Extractor: `scripts/extract_kakao_chat.py`.
- Summary runner: `scripts/kakao_daily_summary.py`.
- Prompt template: `summary_prompt.md`.
- AI CLI: `agy` with `Gemini 3.5 Flash (High)` by default.
- launchd: checks hourly and runs only once per day.
- Permanent output: `history/<chat_id>_<YYYYMMDD>.md`.
- Desktop snapshot: `~/Desktop/kakao open chat/<chatroom_name>.md` (`/Users/<user>/Desktop/kakao open chat/<chatroom_name>.md` on macOS).
- Desktop snapshot cleanup: launchd clears `~/Desktop/kakao open chat` before writing a fresh result.

## Repository Layout

```text
kakao_daily_summary.config.example.json
                                      Portable example config for new environments
SKILL.md                              Codex skill entrypoint for this workspace
summary_prompt.md                    Editable Gemini prompt template
scripts/kakao_chat_core.py           Shared KakaoTalk extraction and transcript formatting logic
scripts/extract_kakao_chat.py        Chat transcript extraction CLI
scripts/kakao_daily_summary.py       Gemini summary CLI
scripts/check_auth.py                macOS dependency and auth preflight
scripts/run_daily_summary_if_needed.sh
scripts/install_launch_agent.sh
scripts/install_runtime_workspace.sh Creates user-local runtime workspace
scripts/install_codex_skill.sh       Installs this repo as a portable Codex skill package
launchd/com.jaewone.kakao-daily-summary.plist
```

Runtime-only files live outside the skill package, normally under:

```text
~/Library/Application Support/kakaotalk-summary/kakao_daily_summary.config.json
~/Library/Application Support/kakaotalk-summary/history/
~/Library/Application Support/kakaotalk-summary/logs/
```

This repository can be used as a Codex skill because `SKILL.md` lives at the project root. The Codex skill package and the scheduled runtime workspace are separate concepts:

- `~/.codex/skills/kakaotalk` is where Codex discovers the skill and reads bundled instructions/scripts.
- The runtime workspace is where the machine-local `kakao_daily_summary.config.json`, `history/`, and `logs/` live. For a distributed install, use `~/Library/Application Support/kakaotalk-summary`.
- launchd should point to the runtime workspace.
- Do not point launchd at `~/.codex/skills/kakaotalk` unless you intentionally create a local config there and use that directory as the runtime workspace.

Install the full portable Codex skill package with:

```bash
scripts/install_codex_skill.sh
```

The installer copies the repo to `~/.codex/skills/kakaotalk` while excluding machine-local state: `kakao_daily_summary.config.json`, `history/`, and `logs/`. A `SKILL.md`-only install is only an instruction-only skill; this project expects the installed skill package to include `scripts/`, `summary_prompt.md`, the launchd template, and `kakao_daily_summary.config.example.json`.

For a distributed install, create a separate runtime workspace:

```bash
~/.codex/skills/kakaotalk/scripts/install_runtime_workspace.sh
```

Then edit:

```text
~/Library/Application Support/kakaotalk-summary/kakao_daily_summary.config.json
```

After registering real `chat_id` values, install launchd from the runtime workspace:

```bash
"$HOME/Library/Application Support/kakaotalk-summary/scripts/install_launch_agent.sh"
```

For development, a symlink to the full repository is also acceptable:

```bash
mkdir -p ~/.codex/skills
ln -sfn /path/to/kakaotalk-summary-workspace ~/.codex/skills/kakaotalk
```

Restart Codex after installing or changing skills.

## Configuration

`kakao_daily_summary.config.json` is the source of truth for chatroom labels and `chat_id` values. It is private runtime state and should live in the runtime workspace, not in `~/.codex/skills/kakaotalk`. For a new machine, start from the portable example:

```bash
cp kakao_daily_summary.config.example.json kakao_daily_summary.config.json
```

Path values support `~`. Relative config paths are resolved from the config file directory.
The local config, generated history, and logs are ignored by git; distribute `kakao_daily_summary.config.example.json`, not a machine-specific config with real `chat_id` values.

```json
{
  "active_chat": "example-room",
  "history_dir": "history",
  "display_dir": "~/Desktop/kakao open chat",
  "timezone": "Asia/Seoul",
  "model": "Gemini 3.5 Flash (High)",
  "limit": 10000,
  "auth_status": {
    "agy_checked_at": null,
    "kakaocli_checked_at": null
  },
  "kakaocli_user_id": null,
  "chats": {
    "example-room": {
      "name": "Example KakaoTalk Room",
      "chat_id": 1234567890,
      "enabled": true
    }
  }
}
```

Use `chat_id` as the durable identifier. Chatroom names can be missing, stale, or shown as `(unknown)` by `kakaocli`.

The summary runner has no default chatroom fallback. Without `--chat-id`, `active_chat` must point to an enabled entry with both `name` and `chat_id`. With `--chat-id`, that id must already exist under `chats`; the display name is read from the matching config entry.

Validate the config after editing:

```bash
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
scripts/check_auth.py --config kakao_daily_summary.config.json
```

## Chatroom Selection

Registering a new chatroom is a two-step process.

1. Discover or infer the correct `chat_id`.
2. Add the `chat_id` and human-readable `name` to `kakao_daily_summary.config.json`.

For discovery only, start with exact or substring matching:

```bash
kakaocli messages --chat "<chat title>" --since 7d --limit 5 --json
kakaocli chats --json --limit 10000 | rg -n "<keyword>"
```

If the title is not directly found, search distinctive member names or message keywords:

```bash
kakaocli search "<keyword-1>" --json --limit 20
kakaocli search "<keyword-2>" --json --limit 20
```

When several keywords point to the same `chat_id`, verify the candidate:

```bash
scripts/extract_kakao_chat.py <chat_id> --start-date YYYY-MM-DD --limit 20
```

If multiple candidates are plausible, do not guess silently. Ask the user to choose or provide more evidence.

## Extract Chat Logs

Use `scripts/extract_kakao_chat.py` when you need conversation text without Gemini.

```bash
scripts/extract_kakao_chat.py <chat_id> [options]
```

Options:

- `--start-date YYYY-MM-DD`: inclusive start date. Defaults to yesterday.
- `--end-date YYYY-MM-DD`: exclusive end date. Defaults to the current time.
- `--limit N`: first `N` messages from the selected range. `0` means all.
- `--full`: output the unnormalized original transcript format.
- `--save-path PATH`: write to a file, or generate a file inside a directory.
- `--timezone NAME`: timezone for date windows. Defaults to `Asia/Seoul`.

Normalized extraction:

```bash
scripts/extract_kakao_chat.py <chat_id> \
  --start-date 2026-07-01 \
  --end-date 2026-07-02 \
  --limit 100
```

Full, unnormalized extraction:

```bash
scripts/extract_kakao_chat.py <chat_id> \
  --start-date 2026-07-01 \
  --end-date 2026-07-02 \
  --full
```

## Transcript Format

Gemini receives the normalized transcript, not the `--full` transcript.

Example:

```text
<2026-07-01>
[12:10:09] 이창현: 낼 ㅇㄷ?
[12:37:34] 태호: 먹고싶은거 있음?
```

Normalization rules:

- Remove `[unknown]` messages.
- Remove the exact bot message `공지 먼저 확인 부탁드립니다.`
- Flatten multiline messages into one line.
- Convert exact `사진` to `[사진]`.
- Compact consecutive photos within 10 minutes into `[사진] N개 첨부`.
- Remove messages made only of `ㅋ`.
- Reduce `ㅋ` repeated 3 or more times to `ㅋㅋㅋ`.
- Convert exact `모두에게 삭제` to `[삭제된 메세지]`.
- Remove JSON feed messages with `feedType` and `hidden: true`.
- Remove JSON feed messages with `feedType` and `members` or `member`.

The `--full` option bypasses normalization and uses this shape:

```text
[2026-07-01 12:10:09] 이창현: 낼 ㅇㄷ?
```

## Run Summaries

Manual summary:

```bash
scripts/kakao_daily_summary.py --force
```

Specific date:

```bash
scripts/kakao_daily_summary.py --date 2026-07-01
```

Dry-run without Gemini:

```bash
scripts/kakao_daily_summary.py --date 2026-07-01 --dry-run --limit 20
```

Important options:

- `--config PATH`: config JSON path.
- `--chat-id ID`: select a `chat_id` already registered in `kakao_daily_summary.config.json`. If omitted, `active_chat` is used.
- `--history-dir PATH`: permanent Markdown output directory.
- `--display-dir PATH`: latest Desktop snapshot directory.
- `--reset-display-dir`: clear display directory before writing.
- `--prompt-template PATH`: prompt template file. Defaults to `summary_prompt.md`.
- `--timezone NAME`: timezone. Defaults to `Asia/Seoul`.
- `--model NAME`: `agy` model. Defaults to `Gemini 3.5 Flash (High)`.
- `--limit N`: maximum messages kept from the selected date window.
- `--agy-timeout DURATION`: passed to `agy --print-timeout`. Defaults to `10m`.

Each successful summary writes:

```text
history/<chat_id>_<YYYYMMDD>.md
~/Desktop/kakao open chat/<chatroom_name>.md
```

The history file is durable. The Desktop folder is only the latest readable snapshot.

## Prompt Template

The Gemini prompt is editable at:

```text
summary_prompt.md
```

The summary script replaces double-brace variables and sends the rendered prompt to `agy` through stdin.

Supported variables:

- `{{chatroom_name}}`: display name of the chatroom being summarized.
- `{{summary_date}}`: target date in `YYYY-MM-DD`.
- `{{conversation}}`: normalized KakaoTalk transcript.

Override the prompt template:

```bash
scripts/kakao_daily_summary.py --prompt-template /path/to/prompt.md
```

or:

```bash
export KAKAO_SUMMARY_PROMPT_TEMPLATE='/path/to/prompt.md'
```

## Gemini / agy

The summary script does not attach or upload a log file. It builds one prompt string and passes it through stdin:

```bash
printf '%s' "$PROMPT" | agy --model "Gemini 3.5 Flash (High)" -p "" --print-timeout 10m
```

The answer is read from stdout and saved as Markdown.

## launchd Automation

Installed launch agent:

```text
~/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist
```

Project files:

```text
launchd/com.jaewone.kakao-daily-summary.plist  Template with __ROOT__ and __PATH__ placeholders
scripts/install_launch_agent.sh
scripts/run_daily_summary_if_needed.sh
```

The wrapper checks:

```text
~/.kakao_daily_summary/last_run
```

If today's date is already recorded, it exits without running Python. Otherwise it calls:

```bash
scripts/kakao_daily_summary.py --config kakao_daily_summary.config.json --all-enabled --reset-display-dir
```

When it actually runs, launchd log lines include timestamp and metadata:

```text
[2026-07-02T09:10:11+0900] level=INFO component=kakao-daily-summary pid=12345 summary_run_started config=...
```

If today's summary has already run, the wrapper exits silently and does not append an `Already ran today` log entry.

Install or reinstall:

```bash
scripts/install_launch_agent.sh
launchctl print "gui/$(id -u)/com.jaewone.kakao-daily-summary"
```

Run `scripts/install_launch_agent.sh` from the runtime workspace that contains `kakao_daily_summary.config.json`. The installer refuses to install if the local config is missing. For a distributed install, that path is normally:

```text
~/Library/Application Support/kakaotalk-summary/scripts/install_launch_agent.sh
```

Change the schedule by editing `StartInterval` in:

```text
launchd/com.jaewone.kakao-daily-summary.plist
```

Then rerun `scripts/install_launch_agent.sh`.

Disable/remove:

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist"
```

Do not delete `history/`, `kakao_daily_summary.config.json`, or `summary_prompt.md` unless explicitly requested.

## Auth Notes

`YOUR_KAKAO_USER_ID` is not the login email. It is KakaoTalk's internal numeric account id used by `kakaocli` to derive the encrypted local database filename and SQLCipher key.

The relevant user preference plists are under:

```text
~/Library/Containers/com.kakao.KakaoTalkMac/Data/Library/Preferences/
```

`/Applications/KakaoTalk.app/Contents/Info.plist` is only app bundle metadata.

The normal auth checks are:

```bash
agy -p "Reply exactly: PONG"
kakaocli auth
```

The integrated preflight is:

```bash
scripts/check_auth.py --config kakao_daily_summary.config.json
```

By default the preflight reuses checks for 5 hours. Use `--force` when you intentionally want to ignore the cached check and verify both tools immediately:

```bash
scripts/check_auth.py --config kakao_daily_summary.config.json --force
```

When `kakaocli auth` fails and `clang` is available, `scripts/check_auth.py` automatically compiles and runs the C recovery helper against active SHA-512 revision hashes found in the KakaoTalk preference plists. The helper can also be run manually:

```bash
clang -O3 -pthread scripts/find_kakao_user_id.c -o /tmp/find_kakao_user_id
/tmp/find_kakao_user_id '<sha512-from-plist-key>' 100000000 1000000000 8
```

If recovery fails or `clang` is unavailable, provide the internal id manually:

```bash
kakaocli auth --user-id <KAKAO_USER_ID>
```

Use auth recovery only when needed. Do not rewrite preference plists casually.

## Validation Checklist

Run these after code/config changes:

```bash
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
python3 -m json.tool kakao_daily_summary.config.example.json >/dev/null
python3 -m py_compile scripts/check_auth.py scripts/kakao_chat_core.py scripts/extract_kakao_chat.py scripts/kakao_daily_summary.py
scripts/check_auth.py --config kakao_daily_summary.config.json
scripts/extract_kakao_chat.py <chat_id> --start-date YYYY-MM-DD --limit 5
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 5
```

Full end-to-end test:

```bash
scripts/kakao_daily_summary.py --date YYYY-MM-DD --reset-display-dir
```

Confirm outputs:

```bash
ls -l history/<chat_id>_<YYYYMMDD>.md
ls -l "$HOME/Desktop/kakao open chat"
```
