#!/usr/bin/env python3
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR.parent / "kakao_daily_summary.config.json"
DEFAULT_KAKAO_USER_ID_START = 100_000_000
DEFAULT_KAKAO_USER_ID_END = 10_000_000_000
DEFAULT_AUTH_MAX_AGE_SECONDS = 5 * 60 * 60


class AuthCheckError(RuntimeError):
    pass


def run(cmd, *, input_text=None, timeout=120):
    try:
        return subprocess.run(
            cmd,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return SimpleNamespace(returncode=127, stdout="", stderr=str(exc))
    except subprocess.TimeoutExpired as exc:
        return SimpleNamespace(
            returncode=124,
            stdout=exc.stdout or "",
            stderr=f"Timed out after {timeout}s",
        )


def load_config(path):
    path = Path(path).expanduser()
    if not path.exists():
        raise AuthCheckError(f"Config does not exist: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise AuthCheckError(f"Invalid config JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AuthCheckError(f"Config root must be an object: {path}")
    return data


def save_config(path, config):
    path = Path(path).expanduser()
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def auth_status(config):
    status = config.get("auth_status")
    if not isinstance(status, dict):
        status = {}
        config["auth_status"] = status
    for key in ("agy", "kakaocli"):
        status.pop(key, None)
        status.setdefault(checked_at_key(key), None)
    return status


def now_utc():
    return datetime.now(timezone.utc)


def checked_at_key(name):
    return f"{name}_checked_at"


def parse_checked_at(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def mark_checked(status, name, ok):
    status[checked_at_key(name)] = (
        now_utc().isoformat(timespec="seconds").replace("+00:00", "Z") if ok else None
    )


def auth_check_is_fresh(status, name, max_age_seconds):
    checked_at = parse_checked_at(status.get(checked_at_key(name)))
    if checked_at is None:
        return False
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    return now_utc() - checked_at < timedelta(seconds=max_age_seconds)


def config_kakaocli_user_id(config):
    value = config.get("kakaocli_user_id")
    if value in (None, ""):
        return None
    return str(value)


def set_config_kakaocli_user_id(config, value):
    if value in (None, ""):
        return
    config["kakaocli_user_id"] = int(value)


def output_detail(proc):
    return ((proc.stdout or "").strip() or (proc.stderr or "").strip()).strip()


def require_macos():
    if platform.system() != "Darwin":
        return False, "This skill is macOS-only."
    return True, ""


def check_agy(timeout):
    if not shutil.which("agy"):
        return False, "agy is not installed or not on PATH."
    proc = run(["agy", "-p", "Reply exactly: PONG"], timeout=timeout)
    output = output_detail(proc)
    if proc.returncode == 0 and "PONG" in output.upper():
        return True, output
    return False, output or "agy did not return PONG."


def active_kakao_user_hashes():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        import find_kakao_user_id
    finally:
        try:
            sys.path.remove(str(SCRIPT_DIR))
        except ValueError:
            pass
    return find_kakao_user_id.active_hashes()


def build_kakao_user_id_helper():
    clang = shutil.which("clang")
    if not clang:
        return None, "clang is not installed or not on PATH."
    source = SCRIPT_DIR / "find_kakao_user_id.c"
    if not source.exists():
        return None, f"Missing helper source: {source}"
    tempdir = tempfile.TemporaryDirectory(prefix="kakao-user-id-")
    output = Path(tempdir.name) / "find_kakao_user_id"
    proc = run([clang, "-O3", "-pthread", str(source), "-o", str(output)], timeout=60)
    if proc.returncode != 0:
        tempdir.cleanup()
        return None, output_detail(proc) or "clang failed to build find_kakao_user_id."
    return (tempdir, output), ""


def parse_found_user_id(text):
    for token in reversed((text or "").split()):
        if token.isdigit():
            return token
    return None


def recover_kakao_user_id_with_clang(start, end, threads, timeout):
    helper, detail = build_kakao_user_id_helper()
    if helper is None:
        return None, detail
    tempdir, executable = helper
    try:
        hashes = active_kakao_user_hashes()
        if not hashes:
            return None, "No active SHA-512 account hash found in KakaoTalk preference plists."
        details = []
        for digest in hashes:
            proc = run([str(executable), digest, str(start), str(end), str(threads)], timeout=timeout)
            found = parse_found_user_id(proc.stdout)
            if proc.returncode == 0 and found:
                return found, f"Recovered user id from plist SHA-512 hash: {digest}"
            details.append(output_detail(proc) or f"No match for hash {digest}")
        return None, "; ".join(details)
    finally:
        tempdir.cleanup()


def kakaocli_auth(user_id=None, timeout=120):
    cmd = ["kakaocli", "auth"]
    if user_id:
        cmd.extend(["--user-id", str(user_id)])
    return run(cmd, timeout=timeout)


def check_kakaocli(config, *, timeout, recover, recovery_start, recovery_end, recovery_threads, recovery_timeout):
    if not shutil.which("kakaocli"):
        return False, "kakaocli is not installed or not on PATH."

    configured_user_id = config_kakaocli_user_id(config)
    if configured_user_id:
        proc = kakaocli_auth(configured_user_id, timeout=timeout)
        if proc.returncode == 0:
            return True, f"kakaocli auth succeeded with configured user id {configured_user_id}."

    proc = kakaocli_auth(timeout=timeout)
    if proc.returncode == 0:
        return True, output_detail(proc)

    original_detail = output_detail(proc)
    if not recover:
        return False, original_detail or "kakaocli auth failed."

    found_user_id, recovery_detail = recover_kakao_user_id_with_clang(
        recovery_start,
        recovery_end,
        recovery_threads,
        recovery_timeout,
    )
    if not found_user_id:
        return False, f"{original_detail} Recovery failed: {recovery_detail}".strip()

    verify = kakaocli_auth(found_user_id, timeout=timeout)
    if verify.returncode == 0:
        set_config_kakaocli_user_id(config, found_user_id)
        return True, f"kakaocli auth succeeded with recovered user id {found_user_id}."
    return False, output_detail(verify) or f"Recovered user id {found_user_id}, but kakaocli auth still failed."


def ensure_auth(
    config_path,
    config=None,
    *,
    require_agy=True,
    require_kakaocli=True,
    agy_timeout=60,
    kakaocli_timeout=120,
    recover_kakao_user_id=True,
    recovery_start=DEFAULT_KAKAO_USER_ID_START,
    recovery_end=DEFAULT_KAKAO_USER_ID_END,
    recovery_threads=None,
    recovery_timeout=180,
    max_age_seconds=DEFAULT_AUTH_MAX_AGE_SECONDS,
    force_auth_check=False,
):
    if os.environ.get("KAKAO_SUMMARY_SKIP_AUTH_CHECK") == "1":
        return config if config is not None else load_config(config_path)

    config_path = Path(config_path).expanduser()
    if not config_path.exists():
        raise AuthCheckError(f"Config does not exist: {config_path}")
    config = config if config is not None else load_config(config_path)
    before = json.dumps(config, ensure_ascii=False, sort_keys=True)

    status = auth_status(config)
    errors = []
    platform_ok, platform_detail = require_macos()
    if not platform_ok:
        if require_agy:
            mark_checked(status, "agy", False)
        if require_kakaocli:
            mark_checked(status, "kakaocli", False)
        errors.append(platform_detail)
    else:
        if require_agy and (force_auth_check or not auth_check_is_fresh(status, "agy", max_age_seconds)):
            ok, detail = check_agy(agy_timeout)
            mark_checked(status, "agy", ok)
            if not ok:
                errors.append(f"agy auth check failed: {detail}")
        if require_kakaocli and (force_auth_check or not auth_check_is_fresh(status, "kakaocli", max_age_seconds)):
            threads = recovery_threads or max(1, min(os.cpu_count() or 1, 8))
            ok, detail = check_kakaocli(
                config,
                timeout=kakaocli_timeout,
                recover=recover_kakao_user_id,
                recovery_start=recovery_start,
                recovery_end=recovery_end,
                recovery_threads=threads,
                recovery_timeout=recovery_timeout,
            )
            mark_checked(status, "kakaocli", ok)
            if not ok:
                errors.append(f"kakaocli auth check failed: {detail}")

    after = json.dumps(config, ensure_ascii=False, sort_keys=True)
    if after != before:
        save_config(config_path, config)

    if errors:
        raise AuthCheckError(" ".join(errors))
    return config


def main():
    parser = argparse.ArgumentParser(description="Check KakaoTalk summary prerequisites and authentication.")
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("KAKAO_SUMMARY_CONFIG", DEFAULT_CONFIG)))
    parser.add_argument("--skip-agy", action="store_true", help="Do not check agy authentication.")
    parser.add_argument("--skip-kakaocli", action="store_true", help="Do not check kakaocli authentication.")
    parser.add_argument("--agy-timeout", type=int, default=60)
    parser.add_argument("--kakaocli-timeout", type=int, default=120)
    parser.add_argument("--no-recover-kakao-user-id", action="store_true")
    parser.add_argument("--recovery-start", type=int, default=DEFAULT_KAKAO_USER_ID_START)
    parser.add_argument("--recovery-end", type=int, default=DEFAULT_KAKAO_USER_ID_END)
    parser.add_argument("--recovery-threads", type=int)
    parser.add_argument("--recovery-timeout", type=int, default=180)
    parser.add_argument("--max-age-seconds", type=int, default=DEFAULT_AUTH_MAX_AGE_SECONDS)
    parser.add_argument("--force", action="store_true", help="Ignore cached auth checks and verify now.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    config = ensure_auth(
        args.config,
        require_agy=not args.skip_agy,
        require_kakaocli=not args.skip_kakaocli,
        agy_timeout=args.agy_timeout,
        kakaocli_timeout=args.kakaocli_timeout,
        recover_kakao_user_id=not args.no_recover_kakao_user_id,
        recovery_start=args.recovery_start,
        recovery_end=args.recovery_end,
        recovery_threads=args.recovery_threads,
        recovery_timeout=args.recovery_timeout,
        max_age_seconds=args.max_age_seconds,
        force_auth_check=args.force,
    )
    if not args.quiet:
        status = auth_status(config)
        print(f"agy_authenticated={str(auth_check_is_fresh(status, 'agy', args.max_age_seconds)).lower()}")
        print(f"agy_checked_at={status.get('agy_checked_at') or ''}")
        print(f"kakaocli_authenticated={str(auth_check_is_fresh(status, 'kakaocli', args.max_age_seconds)).lower()}")
        print(f"kakaocli_checked_at={status.get('kakaocli_checked_at') or ''}")
        user_id = config_kakaocli_user_id(config)
        if user_id:
            print(f"kakaocli_user_id={user_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
