#!/usr/bin/env python3
import argparse
import hashlib
import multiprocessing as mp
import os
import plistlib
import subprocess
import time
from pathlib import Path


EMPTY_SHA512 = (
    "31bca02094eb78126a517b206a88c73cfa9ec6f704c7030d18212cace820f025f00bf0ea68dbf3f3a5436ca63b53bf7bf80ad8d5de7d8359d0b7fed9dbc3ab99"
)
PREF_DIR = Path.home() / "Library/Containers/com.kakao.KakaoTalkMac/Data/Library/Preferences"


def active_hashes():
    hashes = []
    prefixes = (
        "DESIGNATEDFRIENDSREVISION:",
        "PROFILELISTREVISION:",
        "GETDRAWERUSERREVISION:",
        "DENYFILEEXTIONSIONREVISION:",
    )
    for path in sorted(PREF_DIR.glob("com.kakao.KakaoTalkMac*.plist")):
        try:
            data = plistlib.loads(path.read_bytes())
        except Exception:
            continue
        for key, value in data.items():
            key = str(key)
            for prefix in prefixes:
                if key.startswith(prefix):
                    digest = key.split(":", 1)[1]
                    if digest != EMPTY_SHA512 and digest not in hashes and _non_zero(value):
                        hashes.append(digest)
    return hashes


def _non_zero(value):
    try:
        return int(value) != 0
    except Exception:
        return bool(value)


def worker(target, start, end, step, found, progress):
    target = target.lower()
    checked = 0
    for value in range(start, end, step):
        if found.value:
            return
        if hashlib.sha512(str(value).encode()).hexdigest() == target:
            found.value = value
            return
        checked += 1
        if checked % 200_000 == 0:
            progress[start] = value


def find_user_id(target, start, end, workers):
    manager = mp.Manager()
    found = manager.Value("Q", 0)
    progress = manager.dict()
    procs = []
    started = time.time()
    for offset in range(workers):
        proc = mp.Process(target=worker, args=(target, start + offset, end, workers, found, progress))
        proc.start()
        procs.append(proc)

    try:
        while any(proc.is_alive() for proc in procs):
            if found.value:
                break
            time.sleep(10)
            done = sum(max(0, progress.get(start + offset, start + offset) - (start + offset)) // workers for offset in range(workers))
            rate = done / max(1, time.time() - started)
            print(f"checked~{done:,} rate~{rate:,.0f}/s", flush=True)
    finally:
        for proc in procs:
            if found.value and proc.is_alive():
                proc.terminate()
        for proc in procs:
            proc.join()

    return found.value or None


def main():
    parser = argparse.ArgumentParser(description="Recover KakaoTalk internal user id from plist SHA-512 hashes.")
    parser.add_argument("--hash", dest="target_hash")
    parser.add_argument("--start", type=int, default=100_000_000)
    parser.add_argument("--end", type=int, default=10_000_000_000)
    parser.add_argument("--workers", type=int, default=max(1, min(os.cpu_count() or 1, 8)))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    hashes = [args.target_hash] if args.target_hash else active_hashes()
    if not hashes:
        raise SystemExit("No active SHA-512 account hash found in KakaoTalk preference plists.")

    for digest in hashes:
        print(f"target={digest}")
        found = find_user_id(digest, args.start, args.end, args.workers)
        if found:
            print(f"FOUND_USER_ID={found}")
            if args.verify:
                subprocess.run(["kakaocli", "auth", "--user-id", str(found)], check=False)
            return 0
    print("No user id found in the searched range.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
