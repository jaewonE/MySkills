#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import kakao_chat_core as core
import check_auth


DEFAULT_TIMEZONE = "Asia/Seoul"
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "kakao_daily_summary.config.json"
FETCH_LIMIT = 1_000_000


def parse_date(value, option_name):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise RuntimeError(f"{option_name} must be YYYY-MM-DD: {value}") from exc


def date_window(start_date_arg, end_date_arg, timezone):
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    if start_date_arg:
        start_day = parse_date(start_date_arg, "--start-date")
    else:
        start_day = (now - timedelta(days=1)).date()

    start = datetime.combine(start_day, time.min, tzinfo=tz)
    if end_date_arg:
        end_day = parse_date(end_date_arg, "--end-date")
        end = datetime.combine(end_day, time.min, tzinfo=tz)
    else:
        end = now

    if end <= start:
        raise RuntimeError("end-date/current time must be later than start-date")
    return start, end, now


def since_for_start(start, now):
    seconds = max(1, (now - start).total_seconds())
    days = max(1, math.ceil(seconds / 86400))
    return f"{days}d"


def load_chat_name(chat_id, timeout, db=None, key=None, user_id=None):
    cmd = ["kakaocli", "chats", "--json", "--limit", "10000"]
    cmd.extend(core.kakaocli_database_args(db=db, key=key, user_id=user_id))
    proc = core.run(cmd, timeout=timeout)
    if proc.returncode != 0:
        return None
    try:
        chats = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(chats, list):
        return None
    for chat in chats:
        if str(chat.get("id")) == str(chat_id):
            return chat.get("display_name") or None
    return None


def safe_filename_part(value):
    cleaned = re.sub(r"[^0-9A-Za-z가-힣._ -]+", "_", value).strip()
    return cleaned.replace(" ", "_") or "chat"


def resolve_output_path(save_path, chat_name, generated_at):
    if save_path is None:
        return None
    path = Path(save_path).expanduser()
    if path.exists() and path.is_dir():
        directory = path
    elif not path.exists() and path.suffix == "":
        directory = path
    else:
        return path

    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{safe_filename_part(chat_name)}_{generated_at.strftime('%Y%m%d_%H%M%S')}.log"
    return directory / filename


def load_range(
    chat_id,
    start,
    end,
    since,
    fetch_limit,
    kakaocli_timeout,
    db=None,
    key=None,
    user_id=None,
):
    args = SimpleNamespace(
        chat_id=chat_id,
        db=db or os.environ.get("KAKAOCLI_DB"),
        key=key or os.environ.get("KAKAOCLI_DB_KEY"),
        user_id=user_id or os.environ.get("KAKAOCLI_USER_ID"),
        limit=fetch_limit,
        since=since,
        kakaocli_timeout=kakaocli_timeout,
    )
    raw_messages = core.load_messages(args)
    return core.filter_messages(raw_messages, start, end)


def load_range_with_auth_retry(args, start, end, since, config):
    try:
        return load_range(
            args.chat_id,
            start,
            end,
            since,
            FETCH_LIMIT,
            args.kakaocli_timeout,
            db=args.db,
            key=args.key,
            user_id=args.user_id,
        )
    except Exception:
        check_auth.ensure_auth(
            args.config,
            config,
            require_agy=False,
            require_kakaocli=True,
            kakaocli_timeout=args.kakaocli_timeout,
            force_auth_check=True,
        )
        args.user_id = args.user_id or check_auth.config_kakaocli_user_id(config)
        return load_range(
            args.chat_id,
            start,
            end,
            since,
            FETCH_LIMIT,
            args.kakaocli_timeout,
            db=args.db,
            key=args.key,
            user_id=args.user_id,
        )


def main():
    parser = argparse.ArgumentParser(description="Extract KakaoTalk chat messages by chat_id.")
    parser.add_argument("chat_id", type=int, help="Required KakaoTalk chat_id.")
    parser.add_argument("--start-date", help="Inclusive start date, YYYY-MM-DD. Defaults to yesterday.")
    parser.add_argument("--end-date", help="Exclusive end date, YYYY-MM-DD. Defaults to current time.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum formatted messages from start date. 0 means all.")
    parser.add_argument("--full", action="store_true", help="Print/save unnormalized original transcript format.")
    parser.add_argument("--save-path", help="Output file path or directory. If omitted, prints to stdout.")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("KAKAO_SUMMARY_CONFIG", DEFAULT_CONFIG)))
    parser.add_argument("--db", default=os.environ.get("KAKAOCLI_DB"))
    parser.add_argument("--key", default=os.environ.get("KAKAOCLI_DB_KEY"))
    parser.add_argument("--user-id", default=os.environ.get("KAKAOCLI_USER_ID"))
    parser.add_argument("--kakaocli-timeout", type=int, default=180)
    args = parser.parse_args()

    if args.limit < 0:
        raise RuntimeError("--limit must be 0 or an integer greater than or equal to 1")

    args.config = args.config.expanduser()
    config = check_auth.load_config(args.config)
    check_auth.ensure_auth(
        args.config,
        config,
        require_agy=False,
        require_kakaocli=True,
        kakaocli_timeout=args.kakaocli_timeout,
    )
    args.user_id = args.user_id or check_auth.config_kakaocli_user_id(config)

    start, end, now = date_window(args.start_date, args.end_date, args.timezone)
    since = since_for_start(start, now)
    filtered = load_range_with_auth_retry(args, start, end, since, config)
    if args.limit > 0:
        filtered = filtered[: args.limit]

    output = core.full_transcript(filtered) if args.full else core.transcript(filtered)
    path = resolve_output_path(
        args.save_path,
        load_chat_name(args.chat_id, args.kakaocli_timeout, db=args.db, key=args.key, user_id=args.user_id) or f"chat_{args.chat_id}",
        now,
    )
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + ("\n" if output else ""), encoding="utf-8")
        print(path)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
