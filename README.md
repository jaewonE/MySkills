# MySkills

[ [English](https://github.com/jaewonE/MySkills) | [한국어](https://github.com/jaewonE/MySkills/blob/master/README.ko.md) ]

Personal Codex skills maintained for repeatable engineering and research workflows.

## kakaotalk

### Skill Introduction

`kakaotalk` manages KakaoTalk daily summary automation on macOS. It packages the Codex skill instructions, transcript extraction scripts, summary runner, launchd templates, and runtime-workspace installer needed to summarize selected chatrooms by durable `chat_id`.

### Usage

Use this skill when you need to:

- Create a user-local runtime workspace under `~/Library/Application Support/kakaotalk-summary`.
- Discover or register KakaoTalk chatrooms for automated summaries.
- Extract normalized or full chat transcripts from the local KakaoTalk database.
- Run or dry-run the daily summary workflow through `agy`.
- Adjust the summary prompt or launchd schedule for the KakaoTalk automation.

The installed skill package intentionally excludes machine-local state. Use `scripts/install_runtime_workspace.sh` to create the runtime workspace, then edit `kakao_daily_summary.config.json` there with real `chat_id` values before enabling launchd.

### Cautions

Chatroom names can be stale or ambiguous, so prefer confirmed `chat_id` values before editing config. Do not store private `kakao_daily_summary.config.json`, extracted transcripts, generated summaries, credentials, or chat contents in the public skill package.

## kyobobook-inventory

### Skill Introduction

`kyobobook-inventory` checks physical-store inventory for Kyobo Book Centre books through the Kyobo kiosk APIs. It can search for a book, identify matching commodity IDs, and verify stock for specific stores such as Eunpyeong or Hapjeong.

### Usage

Use this skill when you need to:

- Find Kyobo books by title or ISBN.
- Check which physical stores have a book in stock.
- Confirm whether a specific Kyobo store has a specific book.
- Retrieve shelf-location hints when Kyobo provides them.

The skill includes a helper script:

```bash
cd kyobobook-inventory
python3 scripts/kyobobook_inventory.py --title "견고한 데이터 엔지니어링" --stores 046 049
```

### Cautions

The APIs are unofficial and may change without notice. Treat the data as physical kiosk inventory, not ebook-inclusive catalog data. Store inventory changes quickly, so results should be timestamped when used for shopping decisions.

## obsidian-make

### Skill Introduction

`obsidian-make` standardizes local Obsidian plugin work for JaewonE projects. It documents project setup, metadata synchronization, bilingual README policy, versioning, vault installation, GitHub release handling, and archive cleanup rules.

### Usage

Use this skill when creating, updating, documenting, building, installing, publishing, or archiving an Obsidian plugin. It is a workflow and policy guide rather than a script bundle.

### Cautions

Follow the user's requested scope exactly. Do not publish, tag, create releases, or submit to the Obsidian Community Directory unless explicitly requested. For ordinary local plugin work, avoid expanding a small request into a full release workflow.

## License

This repository is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
