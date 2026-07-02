#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import kakao_chat_core as chat_core
import extract_kakao_chat as chat_extract
import check_auth


DEFAULT_HISTORY_DIR = Path(__file__).resolve().parents[1] / "history"
DEFAULT_DISPLAY_DIR = Path.home() / "Desktop" / "kakao open chat"
DEFAULT_TIMEZONE = "Asia/Seoul"
DEFAULT_MODEL = "Gemini 3.5 Flash (High)"
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "kakao_daily_summary.config.json"
DEFAULT_PROMPT_TEMPLATE = Path(__file__).resolve().parents[1] / "summary_prompt.md"


def load_config(path):
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid config JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Config root must be an object: {path}")
    return data


def normalize_registered_chat(key, chat):
    if not isinstance(chat, dict):
        raise RuntimeError(f"Config chat '{key}' must be an object")
    if chat.get("enabled") is False:
        raise RuntimeError(f"Config chat '{key}' is disabled")

    name = chat.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RuntimeError(f"Config chat '{key}' must define a non-empty name")

    raw_chat_id = chat.get("chat_id")
    if raw_chat_id is None:
        raise RuntimeError(f"Config chat '{key}' must define chat_id")
    try:
        chat_id = int(raw_chat_id)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Config chat '{key}' has invalid chat_id: {raw_chat_id}") from exc

    return {"key": key, "name": name, "chat_id": chat_id}


def configured_chats(config):
    chats = config.get("chats", {})
    if not isinstance(chats, dict):
        raise RuntimeError("Config 'chats' must be an object")
    if not chats:
        raise RuntimeError("Config 'chats' must contain at least one registered chat")
    return chats


def selected_chat(config, chat_id=None):
    chats = configured_chats(config)
    if chat_id is not None:
        requested_chat_id = int(chat_id)
        matches = []
        for key, chat in chats.items():
            if not isinstance(chat, dict):
                continue
            raw_chat_id = chat.get("chat_id")
            if raw_chat_id is None:
                continue
            try:
                candidate_chat_id = int(raw_chat_id)
            except (TypeError, ValueError):
                continue
            if candidate_chat_id == requested_chat_id:
                matches.append(normalize_registered_chat(key, chat))
        if not matches:
            raise RuntimeError(f"chat_id {requested_chat_id} is not registered in config 'chats'")
        if len(matches) > 1:
            keys = ", ".join(match["key"] for match in matches)
            raise RuntimeError(f"chat_id {requested_chat_id} is registered multiple times: {keys}")
        return matches[0]

    active_key = config.get("active_chat")
    if not active_key:
        raise RuntimeError("Config must define active_chat when --chat-id is not provided")
    chat = chats.get(active_key)
    if chat is None:
        raise RuntimeError(f"Config active_chat '{active_key}' does not exist in chats")
    return normalize_registered_chat(active_key, chat)


def enabled_registered_chats(config):
    chats = configured_chats(config)
    selected = []
    for key, chat in chats.items():
        if not isinstance(chat, dict):
            continue
        if chat.get("enabled") is False:
            continue
        selected.append(normalize_registered_chat(key, chat))
    if not selected:
        raise RuntimeError("Config 'chats' must contain at least one enabled chat")
    return selected


def first_value(*values):
    for value in values:
        if value is not None:
            return value
    return None


def configured_path(cli_value, env_name, config, config_key, default, config_dir):
    if cli_value is not None:
        return Path(cli_value).expanduser()
    env_value = os.environ.get(env_name)
    if env_value is not None:
        return Path(env_value).expanduser()
    config_value = config.get(config_key)
    if config_value is not None:
        path = Path(config_value).expanduser()
        if not path.is_absolute():
            path = config_dir / path
        return path
    return Path(default).expanduser()


def yesterday_window(tz_name, date_override=None):
    tz = ZoneInfo(tz_name)
    if date_override:
        day = datetime.strptime(date_override, "%Y-%m-%d").date()
    else:
        day = (datetime.now(tz) - timedelta(days=1)).date()
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    return day, start, end


def render_template(template, values):
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


def load_prompt_template(path):
    if not path.exists():
        raise RuntimeError(f"Prompt template does not exist: {path}")
    return path.read_text(encoding="utf-8")


def build_prompt(chat, day, messages, template_path):
    return render_template(
        load_prompt_template(template_path),
        {
            "chatroom_name": chat,
            "summary_date": day.isoformat(),
            "conversation": chat_core.transcript(messages),
        },
    )


def ask_agy(prompt, args):
    cmd = ["agy"]
    if args.model:
        cmd.extend(["--model", args.model])
    cmd.extend(["-p", "", "--print-timeout", args.agy_timeout])
    proc = chat_core.run(cmd, input_text=prompt, timeout=parse_timeout_seconds(args.agy_timeout) + 30)
    output = (proc.stdout or "").strip()
    if proc.returncode == 0 and output:
        return output
    detail = output or (proc.stderr or "").strip()
    raise RuntimeError(f"agy failed: {detail}")


def parse_timeout_seconds(value):
    match = re.fullmatch(r"(\d+)([smh]?)", value.strip())
    if not match:
        return 360
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "h":
        return amount * 3600
    if unit == "m":
        return amount * 60
    return amount


def safe_markdown_name(value):
    return re.sub(r"[/\\:\0]+", "_", value).strip() or "chat"


def history_output_path(history_dir, chat_id, day):
    if not chat_id:
        raise RuntimeError("chat_id is required to write history output")
    return history_dir / f"{chat_id}_{day.strftime('%Y%m%d')}.md"


def display_output_path(display_dir, chat):
    return display_dir / f"{safe_markdown_name(chat)}.md"


def reset_directory(path):
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            raise RuntimeError(f"Refusing to remove nested directory in display output: {child}")
        child.unlink()


def markdown_text(summary, chat, day, count):
    generated_at = datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S %Z")
    text = summary.strip() + "\n\n---\n"
    text += f"- Chat: {chat}\n- Date: {day.isoformat()}\n- Messages summarized: {count}\n- Generated at: {generated_at}\n"
    return text


def write_markdown(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def should_skip_today(state_file, force):
    if force:
        return False
    today = datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).date().isoformat()
    if state_file.exists() and state_file.read_text(encoding="utf-8").strip() == today:
        return True
    return False


def mark_ran_today(state_file):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).date().isoformat()
    state_file.write_text(today + "\n", encoding="utf-8")


def force_auth_check(args, *, require_agy, require_kakaocli):
    check_auth.ensure_auth(
        args.config,
        args.config_data,
        require_agy=require_agy,
        require_kakaocli=require_kakaocli,
        agy_timeout=min(parse_timeout_seconds(args.agy_timeout), 120),
        kakaocli_timeout=args.kakaocli_timeout,
        force_auth_check=True,
    )
    args.user_id = first_value(args.user_id, check_auth.config_kakaocli_user_id(args.config_data))


def load_messages_with_auth_retry(chat_id, start, end, since, args):
    try:
        return chat_extract.load_range(
            chat_id,
            start,
            end,
            since,
            chat_extract.FETCH_LIMIT,
            args.kakaocli_timeout,
            db=args.db,
            key=args.key,
            user_id=args.user_id,
        )
    except Exception:
        force_auth_check(args, require_agy=False, require_kakaocli=True)
        return chat_extract.load_range(
            chat_id,
            start,
            end,
            since,
            chat_extract.FETCH_LIMIT,
            args.kakaocli_timeout,
            db=args.db,
            key=args.key,
            user_id=args.user_id,
        )


def ask_agy_with_auth_retry(prompt, args):
    try:
        return ask_agy(prompt, args)
    except Exception:
        force_auth_check(args, require_agy=True, require_kakaocli=False)
        return ask_agy(prompt, args)


def summarize_chat(chat_config, args, day, start, end):
    chat_name = chat_config["name"]
    chat_id = chat_config["chat_id"]
    since = chat_extract.since_for_start(start, datetime.now(ZoneInfo(args.timezone)))
    messages = load_messages_with_auth_retry(chat_id, start, end, since, args)
    if args.limit > 0:
        messages = messages[: args.limit]

    if args.dry_run:
        print(f"== {chat_name} ({chat_id}) ==")
        print(f"{len(messages)} messages matched {start.isoformat()} - {end.isoformat()}")
        print(chat_core.transcript(messages)[:4000])
        return []

    if messages:
        summary = ask_agy_with_auth_retry(build_prompt(chat_name, day, messages, args.prompt_template), args)
    else:
        summary = f"# {chat_name} 카카오톡 요약 - {day.isoformat()}\n\n어제 하루 동안 요약할 텍스트 메시지가 없습니다."

    text = markdown_text(summary, chat_name, day, len(messages))
    history_path = history_output_path(args.history_dir, chat_id, day)
    display_path = display_output_path(args.display_dir, chat_name)
    write_markdown(history_path, text)
    write_markdown(display_path, text)
    return [history_path, display_path]


def main():
    parser = argparse.ArgumentParser(description="Summarize yesterday's KakaoTalk messages with agy.")
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("KAKAO_SUMMARY_CONFIG", DEFAULT_CONFIG)))
    parser.add_argument("--chat-id", type=int, help="Select a registered chat_id from the config instead of active_chat.")
    parser.add_argument("--all-enabled", action="store_true", help="Summarize every enabled chat in the config.")
    parser.add_argument("--history-dir", type=Path)
    parser.add_argument("--display-dir", type=Path)
    parser.add_argument("--prompt-template", type=Path)
    parser.add_argument("--timezone")
    parser.add_argument("--model")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--date", help="Summarize this date instead of yesterday, YYYY-MM-DD.")
    parser.add_argument("--force", action="store_true", help="Ignore the once-per-day guard.")
    parser.add_argument("--db", default=os.environ.get("KAKAOCLI_DB"))
    parser.add_argument("--key", default=os.environ.get("KAKAOCLI_DB_KEY"))
    parser.add_argument("--user-id", default=os.environ.get("KAKAOCLI_USER_ID"))
    parser.add_argument("--kakaocli-timeout", type=int, default=180)
    parser.add_argument("--agy-timeout", default=os.environ.get("AGY_TIMEOUT", "10m"))
    parser.add_argument("--dry-run", action="store_true", help="Fetch and filter messages, but do not call agy.")
    parser.add_argument("--reset-display-dir", action="store_true", help="Clear the display output directory before writing the summary.")
    args = parser.parse_args()

    args.config = args.config.expanduser()
    config = load_config(args.config)
    args.config_data = config
    config_dir = args.config.resolve().parent if args.config.exists() else Path.cwd()
    if args.all_enabled and args.chat_id is not None:
        raise RuntimeError("--all-enabled cannot be combined with --chat-id")

    args.history_dir = configured_path(args.history_dir, "KAKAO_SUMMARY_HISTORY_DIR", config, "history_dir", DEFAULT_HISTORY_DIR, config_dir)
    args.display_dir = configured_path(args.display_dir, "KAKAO_SUMMARY_DISPLAY_DIR", config, "display_dir", DEFAULT_DISPLAY_DIR, config_dir)
    args.prompt_template = configured_path(args.prompt_template, "KAKAO_SUMMARY_PROMPT_TEMPLATE", config, "prompt_template", DEFAULT_PROMPT_TEMPLATE, config_dir)
    args.timezone = first_value(args.timezone, os.environ.get("KAKAO_SUMMARY_TIMEZONE"), config.get("timezone"), DEFAULT_TIMEZONE)
    args.model = first_value(args.model, os.environ.get("AGY_MODEL"), config.get("model"), DEFAULT_MODEL)
    args.limit = int(first_value(args.limit, os.environ.get("KAKAO_SUMMARY_LIMIT"), config.get("limit"), 10000))
    check_auth.ensure_auth(
        args.config,
        config,
        require_agy=not args.dry_run,
        require_kakaocli=True,
        agy_timeout=min(parse_timeout_seconds(args.agy_timeout), 120),
        kakaocli_timeout=args.kakaocli_timeout,
    )
    args.user_id = first_value(args.user_id, check_auth.config_kakaocli_user_id(config))

    state_file = Path.home() / ".kakao_daily_summary" / "last_run"
    if not args.date and should_skip_today(state_file, args.force):
        print("Already ran today; use --force to run again.")
        return 0

    day, start, end = yesterday_window(args.timezone, args.date)
    chats_to_summarize = enabled_registered_chats(config) if args.all_enabled else [selected_chat(config, args.chat_id)]

    if args.reset_display_dir and not args.dry_run:
        reset_directory(args.display_dir)

    output_paths = []
    for chat_config in chats_to_summarize:
        output_paths.extend(summarize_chat(chat_config, args, day, start, end))

    if not args.date and not args.dry_run:
        mark_ran_today(state_file)
    for path in output_paths:
        print(path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
