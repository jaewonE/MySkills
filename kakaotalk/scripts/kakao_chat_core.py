import base64
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


KAKAO_CONTAINER = (
    Path.home()
    / "Library/Containers/com.kakao.KakaoTalkMac/Data/Library/Application Support/com.kakao.KakaoTalkMac"
)


def run(cmd, *, input_text=None, timeout=120):
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def platform_uuid():
    override = os.environ.get("KAKAOCLI_UUID")
    if override:
        return override

    proc = run(["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], timeout=20)
    match = re.search(r'"IOPlatformUUID" = "([0-9A-F-]+)"', proc.stdout)
    if not match:
        raise RuntimeError("Could not read IOPlatformUUID. Set KAKAOCLI_UUID manually.")
    return match.group(1)


def hashed_device_uuid(uuid):
    raw = uuid.encode()
    return base64.b64encode(hashlib.sha1(raw).digest() + hashlib.sha256(raw).digest()).decode()


def pbkdf2(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000, 128).hex()


def derive_db_name(user_id, uuid):
    hawawa = ".".join([".", "F", str(user_id), "A", "F", uuid[::-1], ".", "|"])
    salt = hashed_device_uuid(uuid)[::-1]
    return pbkdf2(hawawa, salt)[28:106]


def derive_secure_key(user_id, uuid):
    hashed = hashed_device_uuid(uuid)
    parts = ["A", hashed, "|", "F", uuid[:5], "H", str(user_id), "|", uuid[7:]]
    hawawa = "F".join(parts)
    salt = uuid[int(len(uuid) * 0.3) :]
    return pbkdf2(hawawa[::-1], salt)


def kakaocli_base_args(args):
    base = ["kakaocli", "messages", "--since", args.since, "--limit", str(args.limit), "--json"]
    if not args.chat_id:
        raise RuntimeError("chat_id is required for KakaoTalk message extraction")
    base.extend(["--chat-id", str(args.chat_id)])
    if args.db:
        base.extend(["--db", args.db])
    if args.key:
        base.extend(["--key", args.key])

    user_id = args.user_id or os.environ.get("KAKAOCLI_USER_ID")
    if user_id and not args.key:
        uuid = platform_uuid()
        db_name = derive_db_name(int(user_id), uuid)
        db_path = KAKAO_CONTAINER / db_name
        base.extend(["--db", str(db_path), "--key", derive_secure_key(int(user_id), uuid)])

    return base


def load_messages(args):
    proc = run(kakaocli_base_args(args), timeout=args.kakaocli_timeout)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"kakaocli failed: {detail}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"kakaocli returned non-JSON output: {proc.stdout[:500]}") from exc
    if not isinstance(data, list):
        raise RuntimeError("kakaocli JSON output was not a message array")
    return data


def parse_timestamp(value):
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def filter_messages(messages, start, end):
    filtered = []
    for msg in messages:
        ts = parse_timestamp(msg.get("timestamp"))
        if ts is None:
            continue
        local_ts = ts.astimezone(start.tzinfo)
        if start <= local_ts < end:
            copied = dict(msg)
            copied["local_timestamp"] = local_ts.strftime("%Y-%m-%d %H:%M:%S")
            filtered.append(copied)
    return sorted(filtered, key=lambda item: item.get("local_timestamp", ""))


def normalized_text(msg):
    text = msg.get("text") or f"[{msg.get('type', 'non-text')}]"
    return " ".join(str(text).splitlines())


def json_feed_should_skip(text):
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict) or "feedType" not in data:
        return False
    if data.get("hidden") is True:
        return True
    return "members" in data


def display_text(text):
    if text == "사진":
        return "[사진]", True
    if text == "모두에게 삭제":
        return "[삭제된 메세지]", False
    return re.sub(r"ㅋ{3,}", "ㅋㅋㅋ", text), False


def transcript_rows(messages):
    for msg in messages:
        text = normalized_text(msg)
        if (
            text == "[unknown]"
            or text == "공지 먼저 확인 부탁드립니다."
            or re.fullmatch(r"ㅋ+", text)
            or json_feed_should_skip(text)
        ):
            continue
        text, is_photo = display_text(text)
        sender = msg.get("sender") or ("나" if msg.get("is_from_me") else "Unknown")
        ts = datetime.strptime(msg["local_timestamp"], "%Y-%m-%d %H:%M:%S")
        yield {
            "timestamp": ts,
            "date": ts.date().isoformat(),
            "time": ts.time().isoformat(),
            "sender": sender,
            "text": text,
            "is_photo": is_photo,
        }


def compact_photo_rows(rows):
    compacted = []
    photo_group = []

    def flush_photo_group():
        nonlocal photo_group
        if not photo_group:
            return
        first = photo_group[0]
        if len(photo_group) == 1:
            compacted.append(first)
        else:
            merged = dict(first)
            merged["text"] = f"[사진] {len(photo_group)}개 첨부"
            merged["is_photo"] = False
            compacted.append(merged)
        photo_group = []

    for row in rows:
        if row.get("is_photo"):
            if photo_group:
                previous = photo_group[-1]
                same_sender = previous["sender"] == row["sender"]
                within_ten_minutes = row["timestamp"] - previous["timestamp"] <= timedelta(minutes=10)
                if same_sender and within_ten_minutes:
                    photo_group.append(row)
                    continue
            flush_photo_group()
            photo_group.append(row)
            continue

        flush_photo_group()
        compacted.append(row)

    flush_photo_group()
    return compacted


def transcript(messages):
    rows = compact_photo_rows(list(transcript_rows(messages)))
    lines = []
    current_date = None
    for row in rows:
        if row["date"] != current_date:
            if lines:
                lines.append("")
            current_date = row["date"]
            lines.append(f"<{current_date}>")
        lines.append(f"[{row['time']}] {row['sender']}: {row['text']}")
    return "\n".join(lines)


def full_transcript(messages):
    lines = []
    for msg in messages:
        sender = msg.get("sender") or ("나" if msg.get("is_from_me") else "Unknown")
        text = msg.get("text") or f"[{msg.get('type', 'non-text')}]"
        lines.append(f"[{msg['local_timestamp']}] {sender}: {text}")
    return "\n".join(lines)
