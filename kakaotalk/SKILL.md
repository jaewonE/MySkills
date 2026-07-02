---
name: kakaotalk
description: Use when managing KakaoTalk daily summary automation: register chatrooms by chat_id, extract chat logs, run AI summaries through agy, edit the summary prompt, or manage the macOS launchd schedule.
metadata:
  short-description: Manage KakaoTalk chat extraction and daily summary automation
---

# KakaoTalk Daily Summary

## Purpose

Use this macOS-only skill when the user wants to operate or modify a KakaoTalk daily summary workspace. Distinguish the installed Codex skill package from the runtime workspace:

- `~/.codex/skills/kakaotalk` is the Codex skill package used for discovery, instructions, scripts, and templates.
- The runtime workspace is the directory that contains the machine-local `kakao_daily_summary.config.json`, `history/`, and `logs/`. For a distributed install, use `~/Library/Application Support/kakaotalk-summary`.
- launchd should point to the runtime workspace, not to `~/.codex/skills/kakaotalk`, unless that skill package directory is intentionally being used as the runtime workspace and has its own local config.

The project depends on Antigravity2 (`agy`) and `kakaocli`:

- Antigravity2 is installed with `curl -fsSL https://antigravity.google/cli/install.sh | bash`; see <https://antigravity.google/docs/cli/install>.
- `kakaocli` is installed with `brew install silver-flight-group/tap/kakaocli`; see <https://github.com/silver-flight-group/kakaocli#%EA%B0%9C%EC%9A%94>.
- `agy` must be logged in by running `agy` and following its login prompt.
- `kakaocli` auth is checked with `kakaocli auth`; when it fails and local `clang` is available, `scripts/check_auth.py` can infer `KAKAO_USER_ID` from KakaoTalk preference plist SHA-512 revision keys. If inference fails or `clang` is unavailable, the user must run `kakaocli auth --user-id <KAKAO_USER_ID>`.

The project uses:

- `scripts/check_auth.py` to verify macOS dependencies/auth and update successful auth timestamps in `auth_status.agy_checked_at` / `auth_status.kakaocli_checked_at`.
- `kakaocli` to read the local KakaoTalk database.
- `scripts/extract_kakao_chat.py` to extract normalized or full chat transcripts by `chat_id`.
- `scripts/kakao_daily_summary.py` to render `summary_prompt.md`, call `agy`, and save Markdown summaries.
- `kakao_daily_summary.config.json` as the local source of truth for chatroom labels, `chat_id` mappings, output directories, model, timezone, and limits.
- `launchd/com.jaewone.kakao-daily-summary.plist` plus `scripts/run_daily_summary_if_needed.sh` for scheduled macOS runs.

Prefer the local CLI and config over ad hoc SQL. Do not duplicate transcript-cleaning logic in new scripts unless the user explicitly asks for a new implementation.

The installed skill directory must include this full package, not only `SKILL.md`, because the instructions intentionally reference bundled scripts and templates by relative path. Use `scripts/install_codex_skill.sh` from the source repo to sync `~/.codex/skills/kakaotalk`. The installer excludes `kakao_daily_summary.config.json`, `history/`, and `logs/`, so the installed skill package is not the scheduled runtime root.

Do not store user-specific `kakao_daily_summary.config.json` inside `~/.codex/skills/kakaotalk` for normal distribution. Skill installs and updates may replace that directory. Put private config in the runtime workspace instead.

## Orientation

For a distributed install, create the runtime workspace from the installed skill package:

```bash
~/.codex/skills/kakaotalk/scripts/install_runtime_workspace.sh
```

Then edit:

```text
~/Library/Application Support/kakaotalk-summary/kakao_daily_summary.config.json
```

When operating an existing automation, start from the runtime workspace:

```bash
cd "$HOME/Library/Application Support/kakaotalk-summary"
```

Whenever this skill is loaded for real work, check authentication before proceeding:

```bash
scripts/check_auth.py --config kakao_daily_summary.config.json
```

Authentication checks are cached for 5 hours. If the previous check is still fresh, real extraction/summary commands skip preflight and only force a new check after an actual `kakaocli` or `agy` error.

For read-only code/document edits in the installed skill package, this live auth check may be skipped when it is unrelated to the requested change. Before changing runtime behavior, inspect the current state:

```bash
scripts/check_auth.py --config kakao_daily_summary.config.json
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
python3 -m py_compile scripts/check_auth.py scripts/kakao_chat_core.py scripts/extract_kakao_chat.py scripts/kakao_daily_summary.py
```

If `kakaocli auth` fails because the DB cannot be decrypted, stop and resolve auth first. Do not guess a user id. Use the README recovery notes and local helper scripts only when the user asks to repair auth.

## Portable Configuration

For a new runtime workspace, copy or edit the example config and register real chatrooms:

```bash
cp kakao_daily_summary.config.example.json kakao_daily_summary.config.json
```

Use portable path values in config:

```json
{
  "auth_status": {
    "agy_checked_at": null,
    "kakaocli_checked_at": null
  },
  "kakaocli_user_id": null,
  "history_dir": "history",
  "display_dir": "~/Desktop/kakao open chat"
}
```

`history_dir` may be relative to the config file. `display_dir` may use `~`, which expands to the current user's home directory, equivalent to `/Users/<user>/Desktop/kakao open chat` on macOS.

## Chatroom Selection

Selecting a chatroom has two phases:

1. Infer or discover the intended `chat_id` from the user's title or description.
2. Register that exact `chat_id` in `kakao_daily_summary.config.json`.

Always prefer exact `chat_id` once known. Chatroom display names can be `(unknown)`, incomplete, stale, or different from the user's natural-language name.

For discovery only, try exact or substring name lookup through `kakaocli`:

```bash
kakaocli messages --chat "<user provided chat title>" --since 7d --limit 5 --json
kakaocli chats --json --limit 10000 | rg -n "<distinct keyword>"
```

If name lookup fails, split the user title into distinctive tokens or member names and search messages:

```bash
kakaocli search "<keyword-1>" --json --limit 20
kakaocli search "<keyword-2>" --json --limit 20
```

If no plausible chatroom is found after direct name lookup, chat list filtering, and keyword/message search, stop and tell the user that the chatroom could not be found. Ask the user to provide either:

- a recent topic discussed in that room; or
- a specific message, phrase, link, file name, or participant clue that can be searched.

Then use that user-provided clue as the next discovery basis. Do not continue by guessing from weakly related rooms, and do not register a chatroom when there is no concrete `kakaocli` evidence.

Compare candidate `chat_id` values from search results. Favor a candidate when multiple keywords point to the same `chat_id`, sample messages match the described room, or direct extraction shows plausible conversation content.

Verify the candidate directly:

```bash
scripts/extract_kakao_chat.py <chat_id> --start-date YYYY-MM-DD --limit 20
```

If multiple candidates remain plausible, report the candidates and ask the user to choose. Do not register a chatroom when the evidence is ambiguous.

### Registration and Scheduled Runs

Registering a chatroom in `kakao_daily_summary.config.json` is not always the same as adding it to scheduled summaries. The launchd wrapper runs `scripts/kakao_daily_summary.py --all-enabled --reset-display-dir`, so any chat with `"enabled": true` is included in the recurring job.

Set `"enabled": true` only when the user explicitly asks to add the chatroom to recurring summaries, scheduled summaries, the hourly/daily automation, launchd processing, or other repeated work.

When the user only asks a one-off question, summary, extraction, inspection, or test for a chatroom, register the discovered chatroom with `"enabled": false` if registration is needed for command compatibility. In that case, answer the user's request and add a final sentence asking whether they want this chatroom added to recurring summaries.

Register a recurring chatroom under `chats`:

```json
{
  "active_chat": "example-room",
  "chats": {
    "example-room": {
      "name": "Example KakaoTalk Room",
      "chat_id": 1234567890,
      "enabled": true
    }
  }
}
```

Register a one-off/test-only chatroom under `chats`:

```json
{
  "active_chat": "example-room",
  "chats": {
    "example-room": {
      "name": "Example KakaoTalk Room",
      "chat_id": 1234567890,
      "enabled": false
    }
  }
}
```

Validate after editing:

```bash
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
scripts/check_auth.py --config kakao_daily_summary.config.json
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 20
```

## CLI Usage

Use the extractor when the user asks to fetch raw conversation data, inspect a chatroom, create test logs, compare normalized versus full output, or provide data for prompt tuning.

When the user asks to "summarize", "organize", "요약", "정리", or uses similar wording for chat content, do not manually summarize the transcript in the assistant response. Extract the relevant transcript and call Antigravity2 (`agy`) for the actual summarization/organization. Use `scripts/kakao_daily_summary.py` when the request matches its supported daily summary flow. For custom ranges or one-off transcript summaries that do not fit the daily summary CLI, pipe a rendered prompt and the extracted transcript to `agy` directly, then answer from the `agy` output while reporting the transcript path and `chat_id` used.

Normalized transcript:

```bash
scripts/extract_kakao_chat.py <chat_id> \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --limit 100 \
  --save-path /path/to/output.log
```

Full transcript without normalization:

```bash
scripts/extract_kakao_chat.py <chat_id> \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --full
```

Important extractor behavior:

- `chat_id` is required.
- `--start-date` is inclusive and defaults to yesterday.
- `--end-date` is exclusive and defaults to the current time.
- `--limit 0` means all messages.
- Without `--save-path`, output goes to stdout.
- If `--save-path` is a directory, the filename is generated from the chatroom name and current datetime.

Use the summary CLI when the user wants the full AI summary path. `--chat-id` may be used only for a chat already registered in `kakao_daily_summary.config.json`; otherwise the configured `active_chat` is used:

```bash
scripts/kakao_daily_summary.py --force
scripts/kakao_daily_summary.py --date YYYY-MM-DD
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 20
```

Successful summaries write:

```text
history/<chat_id>_<YYYYMMDD>.md
~/Desktop/kakao open chat/<chatroom_name>.md
```

The history file is durable. The Desktop folder is a latest-readable snapshot and may be cleared by launchd before new results are written.

## launchd Schedule Management

The project uses:

```text
launchd/com.jaewone.kakao-daily-summary.plist
scripts/install_launch_agent.sh
scripts/run_daily_summary_if_needed.sh
```

The plist in the runtime workspace is a template. Run the installer from the runtime workspace, not from a config-less skill package, to replace `__ROOT__` and `__PATH__` with the current machine's paths:

```bash
scripts/install_launch_agent.sh
launchctl print "gui/$(id -u)/com.jaewone.kakao-daily-summary"
```

For a first distributed install:

```bash
~/.codex/skills/kakaotalk/scripts/install_runtime_workspace.sh
open "$HOME/Library/Application Support/kakaotalk-summary/kakao_daily_summary.config.json"
"$HOME/Library/Application Support/kakaotalk-summary/scripts/install_launch_agent.sh"
```

The wrapper checks `~/.kakao_daily_summary/last_run` and exits silently when today's summary already ran. It calls:

```bash
scripts/kakao_daily_summary.py --config kakao_daily_summary.config.json --all-enabled --reset-display-dir
```

only when a new daily result should be produced.

To change the schedule, edit `StartInterval` in `launchd/com.jaewone.kakao-daily-summary.plist`, reinstall, and verify with `launchctl print`.

To remove the LaunchAgent:

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist"
```

Do not delete `history/`, `kakao_daily_summary.config.json`, or `summary_prompt.md` unless explicitly requested.

## Prompt Editing

The prompt template is:

```text
summary_prompt.md
```

The summary script reads it, replaces double-brace variables, and sends the rendered prompt to `agy` through stdin. Supported variables:

- `{{chatroom_name}}`: display name of the chatroom being summarized.
- `{{summary_date}}`: summary target date in `YYYY-MM-DD`.
- `{{conversation}}`: normalized transcript generated by `scripts/kakao_chat_core.py`.

When editing the prompt:

1. Keep `{{conversation}}` unless the user explicitly wants a prompt with no transcript.
2. Preserve variables with double braces exactly.
3. Prefer direct Markdown instructions over vague style guidance.
4. After editing, run a dry-run or render smoke test before calling `agy`.

## Verification

After meaningful changes, run the smallest relevant checks:

```bash
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
python3 -m json.tool kakao_daily_summary.config.example.json >/dev/null
python3 -m py_compile scripts/check_auth.py scripts/kakao_chat_core.py scripts/extract_kakao_chat.py scripts/kakao_daily_summary.py
scripts/check_auth.py --config kakao_daily_summary.config.json
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 5
```

For full end-to-end testing, call:

```bash
scripts/kakao_daily_summary.py --date YYYY-MM-DD --reset-display-dir
```

Confirm both output paths are written:

```bash
ls -l history/<chat_id>_<YYYYMMDD>.md
ls -l "$HOME/Desktop/kakao open chat"
```

## Reporting Guidance

For Korean user requests, answer in Korean. Mention:

- which `chat_id` was used or registered;
- which config or prompt file changed;
- whether the chatroom was registered with `enabled: true` or `enabled: false`;
- whether launchd was reinstalled or only edited;
- exact output paths created during tests;
- tests run and any remaining risk.

If the chatroom was registered only for a one-off question, summary, extraction, inspection, or test, and the user did not explicitly ask for recurring automation, end the answer by asking whether to add the chatroom to recurring summaries. Do this even when the launchd schedule already exists, because `enabled: true` controls inclusion in the recurring job.

If chatroom discovery required inference, clearly distinguish observed `kakaocli` evidence from LLM judgment.
