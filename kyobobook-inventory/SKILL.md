---
name: kyobobook-inventory
description: Use when checking Kyobo Book Centre physical bookstore inventory from the kiosk APIs: find books by title, list which stores carry a book, or verify whether a specific book is in stock at specific Kyobo stores.
metadata:
  short-description: Check Kyobo physical store book inventory
---

# Kyobo Book Inventory

## Purpose

Use this skill when the user asks to check Kyobo Book Centre stock for physical bookstore items, especially:

- Whether a book exists in Kyobo's kiosk-searchable physical catalog.
- Which Kyobo stores have a requested book.
- Whether a specific Kyobo store has a requested book.
- Store-specific quantity and shelf-location checks.

The observed APIs are used by Kyobo's kiosk experience. Treat them as physical store inventory APIs. Do not describe them as a complete Kyobo-wide catalog or an ebook-inclusive search unless fresh evidence proves that scope. The stable working assumption is: these APIs cover physical merchandise/books that can be searched from Kyobo store kiosks, and ebook inventory is out of scope.

## Core Endpoints

### 1. Kiosk Commodity Search

```text
GET https://kiosk.kyobobook.co.kr/schf/api/v1/kiosk/search/commodity
```

Known query parameters:

- `query`: Search text. Usually the book title or ISBN.
- `page`: Result page number. Use `1` by default.
- `pageSize`: Number of results. Use `20` by default.
- `category`: Optional category filter. Omit unless the task requires narrowing.

Important response fields:

- `data.source[]`: Search results.
- `dqId`: Sale commodity ID. Use this as `saleCmdtId` for inventory calls.
- `cmdtName`: Title. May include HTML `<b>` tags around matched text.
- `isbn`: ISBN when present.
- `cmdtcode`: Commodity code. For books this usually matches ISBN.
- `saleCmdtDvsnCode`: Sale commodity division code. `KOR` means Korean domestic book.
- `realInvnQntt`: Total observed inventory count across stores, as returned by search.
- `rdpAvlbInvnQntt`: Store-code inventory summary, formatted like `046@0,049@1`.
- `rdpBkshLctnInfm`: Store-code shelf-location summary, formatted like `049@...`.

### 2. Store-Specific Inventory

```text
GET https://kiosk.kyobobook.co.kr/kiosk/api/v1/commodity/inventory
```

Known query parameters:

- `rdpCode`: Kyobo store code, for example `046` for 은평점 or `049` for 합정점.
- `saleCmdtId`: Value from search response `dqId`.
- `cmdtcode`: Value from search response `cmdtcode`.
- `saleCmdtDvsnCode`: Value from search response `saleCmdtDvsnCode`.

Important response fields:

- `data.inventory.realInvnQntt`: Quantity in the requested store.

## Store Codes

Use official store pages and kiosk links to confirm store codes when needed:

- `https://store.kyobobook.co.kr/store-info/{rdpCode}`
- Store pages link to kiosk URLs in the form `https://kiosk.kyobobook.co.kr/main?site={rdpCode}`.

Known codes from prior verification:

- `046`: 은평점, also referred to by users as 은평 롯데몰점.
- `049`: 합정점.

Do not assume unknown store codes. If a store code is not already known, discover it from the Kyobo store-info page or search the official store pages.

## Recommended Workflow

1. Search for the requested title with the kiosk commodity search API.
2. Pick the intended result:
   - Prefer exact title match after stripping HTML tags.
   - If multiple editions or similar titles appear, compare `cmdtName`, `isbn`, author/publisher, and product page ID if available.
3. Extract `dqId`, `cmdtcode`, and `saleCmdtDvsnCode`.
4. For broad store availability:
   - Parse `rdpAvlbInvnQntt`.
   - Report only stores with `quantity > 0`, unless the user asked for specific stores.
5. For specific-store confirmation:
   - Call the store-specific inventory API for each requested `rdpCode`.
   - Prefer `data.inventory.realInvnQntt` as the final per-store quantity.
6. Parse `rdpBkshLctnInfm` for shelf hints when useful.
7. State the check time and warn that store inventory can change quickly.

## Helper Script

This skill includes a no-dependency Python helper in its own `scripts/` directory.
When using it, run commands from the directory containing this `SKILL.md`, or
resolve `scripts/kyobobook_inventory.py` relative to this skill directory. Do
not call a helper from a workspace backup or any external project path.

```bash
python3 scripts/kyobobook_inventory.py \
  --title "견고한 데이터 엔지니어링" \
  --stores 046 049
```

Multiple titles are supported:

```bash
python3 scripts/kyobobook_inventory.py \
  --title "데이터 엔지니어링 디자인 패턴" \
  --title "견고한 데이터 엔지니어링" \
  --title "대규모 머신러닝 시스템 디자인 패턴" \
  --stores 046 049
```

For machine-readable output:

```bash
python3 scripts/kyobobook_inventory.py \
  --title "견고한 데이터 엔지니어링" \
  --stores 046 049 \
  --json
```

## Reporting Guidance

For Korean user requests, answer in Korean. Keep the result compact:

- Show a table with book title and requested stores.
- Use `재고 N권` when quantity is positive.
- Use `재고 0권` or `없음` when quantity is zero.
- Include shelf location if it is available and useful.
- Include source URLs:
  - Product page when `dqId` starts with `S`, for example `https://product.kyobobook.co.kr/detail/S000202731288`.
  - Store page, for example `https://store.kyobobook.co.kr/store-info/049`.

If search returns no exact result, say so and show the closest candidates rather than inventing a product ID.

## Reliability Notes

- These endpoints are unofficial and may change without notice.
- Network calls can fail due to Kyobo-side routing, caching, or anti-automation behavior. If API calls fail, use the browser or Kyobo store page/kiosk page to verify.
- The search API already contains `rdpAvlbInvnQntt`, but store-specific inventory calls are better for final confirmation when the user asks about particular stores.
- Shelf-location strings are compact kiosk data. Preserve useful labels such as wall/shelf section and topic, but do not over-interpret internal coordinates.
