# MySkills

[ [English](https://github.com/jaewonE/MySkills) | [한국어](https://github.com/jaewonE/MySkills/blob/master/README.ko.md) ]

Personal Codex skills maintained for repeatable engineering and research workflows.

## kakaotalk

### Skill Introduction

`kakaotalk` manages Jaewon's local KakaoTalk daily summary automation. It documents how to select chatrooms by durable `chat_id`, register summary targets, run transcript extraction, operate the Gemini summary path through `agy`, and maintain the launchd schedule.

### Usage

Use this skill when you need to:

- Discover or register KakaoTalk chatrooms for automated summaries.
- Extract normalized or full chat transcripts from the local KakaoTalk database.
- Run or dry-run the daily summary workflow.
- Adjust the summary prompt or launchd schedule for the KakaoTalk automation.

The skill is a workflow guide for the local `kakao-cli` project and should be used with the installed local CLI and config files.

### Cautions

Chatroom names can be stale or ambiguous, so prefer confirmed `chat_id` values before editing config. The workflow reads local KakaoTalk data and may produce private conversation summaries; only publish general automation instructions, not extracted transcripts, credentials, or chat contents.

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
