---
name: kakaotalk
description: Use when managing Jaewon's KakaoTalk daily summary automation: choose or register chatrooms by chat_id, manage the launchd schedule, extract chat logs with the local CLI, run Gemini summaries through agy, or edit the summary prompt template.
metadata:
  short-description: Manage KakaoTalk chat extraction and Gemini summary automation
---

# KakaoTalk

## Purpose

Use this skill when the user asks to work on the local KakaoTalk summary automation in:

```text
/Users/jaewone/developer/utils/kakao-cli
```

The project uses:

- `kakaocli` to read the local KakaoTalk database.
- `scripts/extract_kakao_chat.py` to extract normalized or full chat transcripts by `chat_id`.
- `scripts/kakao_daily_summary.py` to render `summary_prompt.md`, call `agy`, and save Markdown summaries.
- `launchd/com.jaewone.kakao-daily-summary.plist` plus `scripts/run_daily_summary_if_needed.sh` for hourly launchd checks.
- `kakao_daily_summary.config.json` as the source of truth for chatroom labels, `chat_id` mappings, output directories, model, timezone, and limit.

Prefer the local CLI and config over ad hoc SQL. Do not duplicate transcript-cleaning logic in new scripts unless the user explicitly asks for a new implementation.

## Initial Orientation

Start from the project root:

```bash
cd /Users/jaewone/developer/utils/kakao-cli
```

Before changing behavior, inspect the current state:

```bash
kakaocli auth
kakaocli login --status
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
python3 -m py_compile scripts/kakao_chat_core.py scripts/extract_kakao_chat.py scripts/kakao_daily_summary.py
```

If `kakaocli auth` fails because the DB cannot be decrypted, stop and resolve auth first. Do not guess a user id. Use the repo README recovery notes and the local helper scripts only when the user asks to repair auth.

## Chatroom Selection

Selecting a chatroom has two phases:

1. Infer or discover the intended `chat_id` from the user's title or description.
2. Register that exact `chat_id` in `kakao_daily_summary.config.json`.

### Phase 1: Infer Or Discover `chat_id`

Always prefer exact `chat_id` once known. Chatroom display names can be `(unknown)`, incomplete, stale, or different from the user's natural-language name.

The summary runner has no default chatroom fallback. It uses `active_chat`, or a `--chat-id` that is already registered in `kakao_daily_summary.config.json`. The display name must come from that config entry.

Use this progression:

1. For discovery only, try exact or substring name lookup through `kakaocli`:

```bash
kakaocli messages --chat "<user provided chat title>" --since 7d --limit 5 --json
kakaocli chats --json --limit 10000 | rg -n "<distinct keyword>"
```

2. If name lookup fails, split the user title into distinctive tokens or member names and search messages:

```bash
kakaocli search "<keyword-1>" --json --limit 20
kakaocli search "<keyword-2>" --json --limit 20
```

3. Compare candidate `chat_id` values from search results. Favor a candidate when:

- multiple keywords point to the same `chat_id`;
- message `sender` values or mentions match the people the user named;
- recent sample messages match the user's described room;
- extracting a small sample by `chat_id` shows plausible conversation content.

4. Verify the candidate directly:

```bash
scripts/extract_kakao_chat.py <chat_id> --start-date YYYY-MM-DD --limit 20
```

If there are multiple plausible candidates, report the candidates and ask the user to choose. Do not register a chatroom when the evidence is ambiguous.

### Phase 2: Register The Chatroom

Update `kakao_daily_summary.config.json` under `chats`:

```json
{
  "active_chat": "nekara-study",
  "history_dir": "/Users/jaewone/developer/utils/kakao-cli/history",
  "display_dir": "/Users/jaewone/Desktop/kakao open chat",
  "chats": {
    "nekara-study": {
      "name": "네카라쿠배 개발자랑 함께 공부하자!",
      "chat_id": 18472038831524877,
      "enabled": true
    }
  }
}
```

Use a stable slug key such as `nekara-study`, `family`, or `ichanghyun-taeho`. The `name` field is for humans. The `chat_id` field is the durable lookup key used by automation. Keep disabled chats in the file when useful because this config also documents what each `chat_id` means.

Validate after editing:

```bash
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 20
```

## CLI Usage

Use the extractor when the user asks to fetch raw conversation data, inspect a chatroom, create test logs, compare normalized versus full output, or provide data for prompt tuning.

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

Use the summary CLI when the user wants the full Gemini path. `--chat-id` may be used only for a chat already registered in `kakao_daily_summary.config.json`; otherwise the configured `active_chat` is used:

```bash
scripts/kakao_daily_summary.py --force
scripts/kakao_daily_summary.py --date YYYY-MM-DD
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 20
```

Successful summaries write:

```text
history/<chat_id>_<YYYYMMDD>.md
/Users/jaewone/Desktop/kakao open chat/<chatroom_name>.md
```

The `history` file is durable. The Desktop folder is a latest-readable snapshot and may be cleared by launchd before new results are written.

## launchd Schedule Management

The project uses:

```text
launchd/com.jaewone.kakao-daily-summary.plist
scripts/install_launch_agent.sh
scripts/run_daily_summary_if_needed.sh
```

The wrapper checks `~/.kakao_daily_summary/last_run` and exits silently when today's summary already ran. It calls `scripts/kakao_daily_summary.py --config kakao_daily_summary.config.json --reset-display-dir` only when a new daily result should be produced. Do not reintroduce `Already ran today` stdout/stderr logging in the launchd wrapper.

When the summary actually runs, wrapper output is metadata-prefixed before launchd writes it to `logs/`:

```text
[YYYY-MM-DDTHH:MM:SS+0900] level=INFO component=kakao-daily-summary pid=<pid> <message>
```

### Register Or Reinstall

After editing the plist or wrapper:

```bash
scripts/install_launch_agent.sh
launchctl print "gui/$(id -u)/com.jaewone.kakao-daily-summary"
```

Verify the effective interval, last exit status, and program arguments.

### Modify Schedule

Edit `launchd/com.jaewone.kakao-daily-summary.plist`. Common keys:

- `RunAtLoad`: run once when the agent loads.
- `StartInterval`: repeat interval in seconds. For example, `3600` is hourly.
- `StandardOutPath` and `StandardErrorPath`: log paths under the project `logs/` directory.

Then reinstall with `scripts/install_launch_agent.sh` and verify with `launchctl print`.

### Delete Or Disable

When the user asks to remove the automation:

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.jaewone.kakao-daily-summary.plist"
```

Do not delete `history/`, `kakao_daily_summary.config.json`, or `summary_prompt.md` unless the user explicitly asks.

## Prompt Editing

The Gemini prompt template is:

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

Useful checks:

```bash
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 20
python3 -m py_compile scripts/kakao_daily_summary.py
```

## Gemini / agy Behavior

The summary script does not upload a file to Gemini. It builds a prompt string and passes it to `agy` through stdin:

```bash
printf '%s' "$PROMPT" | agy --model "Gemini 3.5 Flash (High)" -p "" --print-timeout 10m
```

`agy --model` is optional in the installed CLI. When running an end-to-end summary, first try the configured model. If the command fails and the stderr/stdout indicates a model selection problem, such as an unknown model, invalid model, unsupported model, unavailable model, or model flag parsing issue, retry once without the model argument:

```bash
printf '%s' "$PROMPT" | agy -p "" --print-timeout 10m
```

Treat this fallback as specific to model-related failures only. Do not retry without `--model` for auth failures, `kakaocli` failures, prompt/template errors, timeout issues, or empty transcript problems unless the user explicitly asks.

The transcript sent to Gemini is normalized, not `--full`. `--full` is only for manual extraction with `scripts/extract_kakao_chat.py`.

## Verification Checklist

After meaningful changes, run the smallest relevant checks:

```bash
python3 -m json.tool kakao_daily_summary.config.json >/dev/null
python3 -m py_compile scripts/kakao_chat_core.py scripts/extract_kakao_chat.py scripts/kakao_daily_summary.py
scripts/extract_kakao_chat.py <chat_id> --start-date YYYY-MM-DD --limit 5
scripts/kakao_daily_summary.py --date YYYY-MM-DD --dry-run --limit 5
```

For full end-to-end testing, call:

```bash
scripts/kakao_daily_summary.py --date YYYY-MM-DD --reset-display-dir
```

Confirm both output paths are written:

```bash
ls -l history/<chat_id>_<YYYYMMDD>.md
ls -l "/Users/jaewone/Desktop/kakao open chat"
```

## Reporting Guidance

For Korean user requests, answer in Korean. Mention:

- which `chat_id` was used or registered;
- which config or prompt file changed;
- whether launchd was reinstalled or only edited;
- exact output paths created during tests;
- tests run and any remaining risk.

If chatroom discovery required inference, clearly distinguish observed `kakaocli` evidence from LLM judgment.
