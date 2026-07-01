# Agent Guide

This repository manages Jaewon's local KakaoTalk daily summary automation. Use this guide when editing the project, operating the launchd job, registering chatrooms, extracting transcripts, or changing the Gemini prompt.

## Working Directory

Work from the runtime workspace when operating the actual automation. It must contain the machine-local `kakao_daily_summary.config.json`:

```bash
cd /path/to/kakaotalk-summary-workspace
```

Core files:

- `SKILL.md`: Codex skill entrypoint for this workspace.
- `kakao_daily_summary.config.example.json`: portable config template for new environments.
- `kakao_daily_summary.config.json`: local chatroom ids, active chat, output directories, model, timezone, and limits.
- `summary_prompt.md`: Gemini prompt template.
- `scripts/kakao_chat_core.py`: shared extraction, filtering, and transcript normalization logic.
- `scripts/extract_kakao_chat.py`: CLI for chat transcript extraction by `chat_id`.
- `scripts/kakao_daily_summary.py`: CLI for full Gemini summary generation.
- `scripts/run_daily_summary_if_needed.sh`: lightweight daily guard used by launchd.
- `scripts/install_launch_agent.sh`: installs/reloads the LaunchAgent.
- `scripts/install_runtime_workspace.sh`: creates a user-local runtime workspace outside the Codex skill package.
- `scripts/install_codex_skill.sh`: installs the full portable Codex skill package.
- `launchd/com.jaewone.kakao-daily-summary.plist`: launchd schedule definition.
- `history/`: durable summary archive.
- `logs/`: launchd stdout/stderr logs.

This repository can be installed as a Codex skill because `SKILL.md` lives at the project root:

```text
~/.codex/skills/kakaotalk/SKILL.md
```

Use `scripts/install_codex_skill.sh` to install the full package. A `SKILL.md`-only installed copy works only as instruction text and is not enough for this repo-as-skill layout because the skill references `scripts/`, `summary_prompt.md`, and the config example by relative path.

Do not confuse the installed Codex skill package with the launchd runtime workspace. The installed package excludes `kakao_daily_summary.config.json`, `history/`, and `logs/`; launchd should point to the runtime workspace that has those local files. For distributed installs, prefer `~/Library/Application Support/kakaotalk-summary`.

Do not store private `kakao_daily_summary.config.json` in `~/.codex/skills/kakaotalk` during normal distribution. Skill package updates may replace that directory.

Keep `README.md`, this agent guide, and the root `SKILL.md` aligned when workflow behavior changes. If a local installed copy exists, sync it with `scripts/install_codex_skill.sh` after changing the root `SKILL.md`.

## Operating Principles

- Prefer `chat_id` over chatroom display names. Display names can be missing, stale, or `(unknown)`.
- The summary runner has no default chatroom fallback. It uses `active_chat`, or a `--chat-id` that is already registered in `kakao_daily_summary.config.json`.
- Keep transcript extraction logic centralized in `scripts/kakao_chat_core.py`.
- Do not duplicate normalization rules in one-off scripts.
- Use `scripts/extract_kakao_chat.py` for transcript inspection and test fixtures.
- Use `scripts/kakao_daily_summary.py` for Gemini/agy summary runs.
- Treat `history/` as durable output.
- Treat `~/Desktop/kakao open chat` (`/Users/<user>/Desktop/kakao open chat`) as a disposable latest-snapshot folder.
- Do not delete `history/`, `kakao_daily_summary.config.json`, or `summary_prompt.md` unless explicitly requested.
- When chatroom discovery involved inference, report the evidence separately from the judgment.

## Chatroom Registration Workflow

Registering a chatroom has two phases.

### 1. Discover the `chat_id`

For discovery only, try exact or substring matching first:

```bash
kakaocli messages --chat "<chat title>" --since 7d --limit 5 --json
kakaocli chats --json --limit 10000 | rg -n "<keyword>"
```

If direct lookup fails, search distinctive names or message terms:

```bash
kakaocli search "<keyword-1>" --json --limit 20
kakaocli search "<keyword-2>" --json --limit 20
```

Compare candidate `chat_id` values. Favor a candidate only when multiple signals point to it, such as sender names, mentions, matching message content, and recent activity.

Verify directly:

```bash
scripts/extract_kakao_chat.py <chat_id> --start-date YYYY-MM-DD --limit 20
```

Ask the user to choose if more than one candidate remains plausible.

### 2. Register the `chat_id`

Edit `kakao_daily_summary.config.json`:

```json
{
  "chats": {
    "stable-slug": {
      "name": "Human-readable chatroom name",
      "chat_id": 123456789,
      "enabled": true
    }
  }
}
```

Use stable slug keys. Keep disabled entries when they help document existing `chat_id` mappings.

Validate:

```bash
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 20
```

## Transcript CLI

Normalized output:

```bash
scripts/extract_kakao_chat.py <chat_id> \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --limit 100
```

Full output:

```bash
scripts/extract_kakao_chat.py <chat_id> \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --full
```

Save output:

```bash
scripts/extract_kakao_chat.py <chat_id> \
  --start-date YYYY-MM-DD \
  --save-path /path/to/output.log
```

Important behavior:

- `--start-date` is inclusive.
- `--end-date` is exclusive.
- `--limit 0` means all messages.
- Default output is the normalized Gemini transcript.
- `--full` bypasses normalization and preserves the old full transcript shape.

## Normalization Rules

Gemini receives normalized transcript text from `scripts/kakao_chat_core.py`.

Current rules:

- Remove `[unknown]`.
- Remove exact `공지 먼저 확인 부탁드립니다.`.
- Flatten multiline messages into one line.
- Convert exact `사진` to `[사진]`.
- Compact consecutive photos within 10 minutes into `[사진] N개 첨부`.
- Remove messages made only of `ㅋ`.
- Reduce `ㅋ` repeated 3 or more times to `ㅋㅋㅋ`.
- Convert exact `모두에게 삭제` to `[삭제된 메세지]`.
- Remove JSON feed messages with `feedType` and `hidden: true`.
- Remove JSON feed messages with `feedType` and `members`.

If these rules change, update:

- `scripts/kakao_chat_core.py`
- `README.md`
- `SKILL.md`
- this `AGENT.md`

## Summary CLI

Run a full summary:

```bash
scripts/kakao_daily_summary.py --force
```

Run for a specific date:

```bash
scripts/kakao_daily_summary.py --date YYYY-MM-DD
```

Dry-run without Gemini:

```bash
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 20
```

End-to-end test with Desktop snapshot reset:

```bash
scripts/kakao_daily_summary.py --date YYYY-MM-DD --reset-display-dir
```

Successful runs write:

```text
history/<chat_id>_<YYYYMMDD>.md
~/Desktop/kakao open chat/<chatroom_name>.md
```

## Gemini Prompt

Prompt file:

```text
summary_prompt.md
```

Supported variables:

- `{{chatroom_name}}`
- `{{summary_date}}`
- `{{conversation}}`

The summary runner renders the template and passes the final prompt to `agy` through stdin. It does not upload a file.

Call shape:

```bash
printf '%s' "$PROMPT" | agy --model "Gemini 3.5 Flash (High)" -p "" --print-timeout 10m
```

When editing the prompt:

- Keep `{{conversation}}` unless the user explicitly removes transcript input.
- Preserve double-brace variable syntax exactly.
- Prefer precise output instructions over vague style guidance.
- Run a dry-run and, when appropriate, an end-to-end summary test.

## launchd

Project LaunchAgent:

```text
launchd/com.jaewone.kakao-daily-summary.plist
```

Installed LaunchAgent:

```text
~/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist
```

Install or reload:

```bash
scripts/install_launch_agent.sh
launchctl print "gui/$(id -u)/com.jaewone.kakao-daily-summary"
```

Run the installer from the runtime workspace. It should not be run from a config-less `~/.codex/skills/kakaotalk` package unless that package directory has intentionally been turned into the runtime workspace. For distributed installs, first run `~/.codex/skills/kakaotalk/scripts/install_runtime_workspace.sh`, edit the runtime config, then run `~/Library/Application Support/kakaotalk-summary/scripts/install_launch_agent.sh`.

The launchd wrapper:

```text
scripts/run_daily_summary_if_needed.sh
```

It checks:

```text
~/.kakao_daily_summary/last_run
```

and runs the summary only if today's date has not already been recorded.

When the summary actually runs, wrapper output is metadata-prefixed before launchd writes it to `logs/`:

```text
[YYYY-MM-DDTHH:MM:SS+0900] level=INFO component=kakao-daily-summary pid=<pid> <message>
```

If today's date is already recorded, the wrapper exits silently. Do not reintroduce `Already ran today` stdout/stderr logging in the launchd wrapper.

To change the schedule, edit `StartInterval` in the plist, reinstall, then verify with `launchctl print`.

To remove:

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist"
```

## Auth Handling

Start with:

```bash
kakaocli auth
kakaocli login --status
kakaocli status
```

If `kakaocli auth` fails because the DB cannot be decrypted, do not guess the user id. Use the README recovery notes and helper scripts only when the user asks to repair auth.

`YOUR_KAKAO_USER_ID` is KakaoTalk's internal numeric account id, not the login email.

The relevant preference plists are under:

```text
~/Library/Containers/com.kakao.KakaoTalkMac/Data/Library/Preferences/
```

`/Applications/KakaoTalk.app/Contents/Info.plist` is app bundle metadata and is not the user preference plist used for auth recovery.

## Validation

Run these after edits:

```bash
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
python3 -m py_compile scripts/kakao_chat_core.py scripts/extract_kakao_chat.py scripts/kakao_daily_summary.py
```

For CLI behavior:

```bash
scripts/extract_kakao_chat.py <chat_id> --start-date YYYY-MM-DD --limit 5
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 5
```

For full behavior:

```bash
scripts/kakao_daily_summary.py --date YYYY-MM-DD --reset-display-dir
ls -l history/<chat_id>_<YYYYMMDD>.md
ls -l "$HOME/Desktop/kakao open chat"
```

## Response Expectations

When reporting work to the user:

- Answer in Korean unless the user asks otherwise.
- Mention exact changed files.
- Mention `chat_id` values used or registered.
- State whether launchd was reinstalled or only edited.
- Include output paths from tests.
- Separate observed `kakaocli` evidence from LLM inference.
- Mention any skipped tests or residual risk.
