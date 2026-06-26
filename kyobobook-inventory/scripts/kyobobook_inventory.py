#!/usr/bin/env python3
"""Query Kyobo Book Centre kiosk APIs for physical store inventory."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


SEARCH_ENDPOINT = "https://kiosk.kyobobook.co.kr/schf/api/v1/kiosk/search/commodity"
INVENTORY_ENDPOINT = "https://kiosk.kyobobook.co.kr/kiosk/api/v1/commodity/inventory"
PRODUCT_BASE = "https://product.kyobobook.co.kr/detail/"
STORE_BASE = "https://store.kyobobook.co.kr/store-info/"

KNOWN_STORES = {
    "046": "은평점",
    "049": "합정점",
}


@dataclass
class BookResult:
    requested_title: str
    matched_title: str | None
    sale_cmdt_id: str | None
    isbn: str | None
    cmdtcode: str | None
    sale_cmdt_dvsn_code: str | None
    author: str | None
    publisher: str | None
    product_url: str | None
    candidates: list[dict[str, Any]]
    stores: list[dict[str, Any]]


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def strip_tags(value: str | None) -> str:
    if not value:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", value)).strip()


def parse_store_count_blob(value: str | None) -> dict[str, int]:
    result: dict[str, int] = {}
    for part in (value or "").split(","):
        if "@" not in part:
            continue
        code, quantity = part.split("@", 1)
        try:
            result[code] = int(quantity)
        except ValueError:
            continue
    return result


def parse_store_shelf_blob(value: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in (value or "").split(","):
        if "@" not in part:
            continue
        code, shelf = part.split("@", 1)
        result[code] = shelf
    return result


def search(title: str, page_size: int) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"query": title, "page": 1, "pageSize": page_size})
    payload = fetch_json(f"{SEARCH_ENDPOINT}?{query}")
    data = payload.get("data") or {}
    return data.get("source") or []


def pick_result(title: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_title = title.strip()
    for candidate in candidates:
        if strip_tags(candidate.get("cmdtName")) == normalized_title:
            return candidate
    return candidates[0] if candidates else None


def inventory_for_store(item: dict[str, Any], store_code: str) -> tuple[int | None, str]:
    query = urllib.parse.urlencode(
        {
            "rdpCode": store_code,
            "saleCmdtId": item.get("dqId", ""),
            "cmdtcode": item.get("cmdtcode", ""),
            "saleCmdtDvsnCode": item.get("saleCmdtDvsnCode", ""),
        }
    )
    url = f"{INVENTORY_ENDPOINT}?{query}"
    payload = fetch_json(url)
    inventory = ((payload.get("data") or {}).get("inventory") or {})
    quantity = inventory.get("realInvnQntt")
    return int(quantity) if quantity is not None else None, url


def inspect_title(title: str, stores: list[str], page_size: int) -> BookResult:
    candidates = search(title, page_size)
    item = pick_result(title, candidates)
    if not item:
        return BookResult(
            requested_title=title,
            matched_title=None,
            sale_cmdt_id=None,
            isbn=None,
            cmdtcode=None,
            sale_cmdt_dvsn_code=None,
            author=None,
            publisher=None,
            product_url=None,
            candidates=[],
            stores=[],
        )

    counts = parse_store_count_blob(item.get("rdpAvlbInvnQntt"))
    shelves = parse_store_shelf_blob(item.get("rdpBkshLctnInfm"))
    sale_cmdt_id = item.get("dqId")

    store_results = []
    for store_code in stores:
        try:
            quantity, inventory_url = inventory_for_store(item, store_code)
        except Exception as exc:  # noqa: BLE001 - command-line diagnostic
            quantity = counts.get(store_code)
            inventory_url = None
            error = str(exc)
        else:
            error = None

        store_results.append(
            {
                "storeCode": store_code,
                "storeName": KNOWN_STORES.get(store_code, ""),
                "quantity": quantity,
                "searchSummaryQuantity": counts.get(store_code),
                "shelf": shelves.get(store_code, ""),
                "storeUrl": f"{STORE_BASE}{store_code}",
                "inventoryUrl": inventory_url,
                "error": error,
            }
        )

    return BookResult(
        requested_title=title,
        matched_title=strip_tags(item.get("cmdtName")),
        sale_cmdt_id=sale_cmdt_id,
        isbn=item.get("isbn"),
        cmdtcode=item.get("cmdtcode"),
        sale_cmdt_dvsn_code=item.get("saleCmdtDvsnCode"),
        author=item.get("chrcName"),
        publisher=item.get("pbcmName"),
        product_url=f"{PRODUCT_BASE}{sale_cmdt_id}" if sale_cmdt_id else None,
        candidates=[
            {
                "title": strip_tags(candidate.get("cmdtName")),
                "saleCmdtId": candidate.get("dqId"),
                "isbn": candidate.get("isbn"),
                "author": candidate.get("chrcName"),
                "publisher": candidate.get("pbcmName"),
            }
            for candidate in candidates[:5]
        ],
        stores=store_results,
    )


def asdict_book(result: BookResult) -> dict[str, Any]:
    return {
        "requestedTitle": result.requested_title,
        "matchedTitle": result.matched_title,
        "saleCmdtId": result.sale_cmdt_id,
        "isbn": result.isbn,
        "cmdtcode": result.cmdtcode,
        "saleCmdtDvsnCode": result.sale_cmdt_dvsn_code,
        "author": result.author,
        "publisher": result.publisher,
        "productUrl": result.product_url,
        "candidates": result.candidates,
        "stores": result.stores,
    }


def print_text(results: list[BookResult]) -> None:
    for result in results:
        print(f"\n{result.requested_title}")
        if not result.matched_title:
            print("  No kiosk search result.")
            continue
        print(
            "  matched: "
            f"{result.matched_title} / {result.author or ''} / {result.publisher or ''}"
        )
        print(
            "  ids: "
            f"saleCmdtId={result.sale_cmdt_id}, "
            f"cmdtcode={result.cmdtcode}, "
            f"saleCmdtDvsnCode={result.sale_cmdt_dvsn_code}"
        )
        if result.product_url:
            print(f"  product: {result.product_url}")
        for store in result.stores:
            label = store["storeName"] or store["storeCode"]
            quantity = store["quantity"]
            quantity_text = "unknown" if quantity is None else f"{quantity}"
            print(f"  - {label}({store['storeCode']}): {quantity_text}")
            if store.get("shelf"):
                print(f"    shelf: {store['shelf']}")
            if store.get("error"):
                print(f"    inventory API error: {store['error']}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", action="append", required=True, help="Book title to search.")
    parser.add_argument("--stores", nargs="+", default=[], help="Kyobo store codes to verify.")
    parser.add_argument("--page-size", type=int, default=20, help="Search page size.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    stores = args.stores or sorted(KNOWN_STORES)
    results = [inspect_title(title, stores, args.page_size) for title in args.title]

    if args.json:
        print(json.dumps([asdict_book(result) for result in results], ensure_ascii=False, indent=2))
    else:
        print_text(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
