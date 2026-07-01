# MySkills

[ [English](https://github.com/jaewonE/MySkills) | [한국어](https://github.com/jaewonE/MySkills/blob/master/README.ko.md) ]

반복적인 엔지니어링 및 조사 작업을 위해 관리하는 개인 Codex 스킬 모음입니다.

## kakaotalk

### 스킬 소개

`kakaotalk`은 macOS에서 KakaoTalk 일일 요약 자동화를 관리하는 스킬입니다. 안정적인 `chat_id`를 기준으로 선택한 채팅방을 요약하기 위해 필요한 Codex 스킬 지침, 대화 추출 스크립트, 요약 실행기, launchd 템플릿, runtime workspace 설치 스크립트를 포함합니다.

### 사용 방법

다음 작업에 사용합니다.

- `~/Library/Application Support/kakaotalk-summary` 아래에 사용자별 runtime workspace 만들기.
- KakaoTalk 요약 대상 채팅방을 찾거나 등록하기.
- 로컬 KakaoTalk 데이터베이스에서 정규화된 대화 또는 전체 대화 추출하기.
- `agy`를 통한 일일 요약 워크플로우 실행 또는 dry-run 수행하기.
- KakaoTalk 자동화의 요약 프롬프트나 launchd 스케줄 조정하기.

설치된 스킬 패키지는 의도적으로 머신별 상태를 포함하지 않습니다. `scripts/install_runtime_workspace.sh`로 runtime workspace를 만든 뒤, launchd를 활성화하기 전에 그 안의 `kakao_daily_summary.config.json`에 실제 `chat_id` 값을 등록해야 합니다.

### 주의 사항

채팅방 이름은 오래되었거나 모호할 수 있으므로 config를 수정하기 전에 확인된 `chat_id`를 우선 사용해야 합니다. 공개 스킬 패키지에는 private `kakao_daily_summary.config.json`, 추출한 대화, 생성된 요약, 인증 정보, 채팅 내용을 저장하지 않아야 합니다.

## kyobobook-inventory

### 스킬 소개

`kyobobook-inventory`는 교보문고 키오스크 API를 이용해 교보문고 오프라인 매장의 실물 도서 재고를 확인하는 스킬입니다. 도서를 검색하고, 교보문고 상품 ID를 식별하며, 은평점이나 합정점 같은 특정 매장의 재고를 확인할 수 있습니다.

### 사용 방법

다음 작업에 사용합니다.

- 제목이나 ISBN으로 교보문고 도서를 찾기.
- 어떤 오프라인 매장에 도서 재고가 있는지 확인하기.
- 특정 도서가 특정 교보문고 매장에 있는지 확인하기.
- 교보문고가 제공하는 경우 서가 위치 힌트 확인하기.

스킬에는 helper script가 포함되어 있습니다.

```bash
cd kyobobook-inventory
python3 scripts/kyobobook_inventory.py --title "견고한 데이터 엔지니어링" --stores 046 049
```

### 주의 사항

해당 API는 비공식 API이며 예고 없이 변경될 수 있습니다. 이 데이터는 전자책을 포함한 전체 카탈로그가 아니라 실물 매장 키오스크 재고로 취급해야 합니다. 매장 재고는 빠르게 바뀔 수 있으므로 구매 판단에 사용할 때는 확인 시각을 함께 기록해야 합니다.

## obsidian-make

### 스킬 소개

`obsidian-make`는 JaewonE Obsidian 플러그인 작업을 표준화하는 스킬입니다. 프로젝트 생성, 메타데이터 동기화, 양국어 README 정책, 버전 관리, vault 설치, GitHub 릴리스 처리, archive cleanup 규칙을 문서화합니다.

### 사용 방법

Obsidian 플러그인을 생성, 수정, 문서화, 빌드, 설치, 게시, 정리할 때 사용합니다. 스크립트 묶음이라기보다는 반복 작업을 위한 워크플로우 및 정책 가이드입니다.

### 주의 사항

사용자가 지정한 작업 범위를 정확히 지켜야 합니다. 사용자가 명시적으로 요청하지 않는 한 publish, tag, release 생성, Obsidian Community Directory 제출을 수행하지 않습니다. 일반적인 로컬 플러그인 작업에서는 작은 요청을 전체 릴리스 워크플로우로 확장하지 않아야 합니다.

## 라이선스

이 저장소는 GNU General Public License v3.0에 따라 배포됩니다. 자세한 내용은 [LICENSE](LICENSE)를 확인하세요.
