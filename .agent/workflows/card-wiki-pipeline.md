# 카드 v37·쟁점 위키 운영 워크플로우

> 갱신: 2026-06-16
> 목적: 카드/리서치/위키화 운영 기준. 실행 주체에 무관하게 적용한다.
> 운영 주체(2026-06-16 환원): Claude Web으로 복귀. (GPT Pro/Codex 미사용 — 사용자 지정) 구독 활성·워크스페이스 접근·korean-law-mcp 직접 호출 가능 → anchor 검증을 외부 API 대신 korean-law-mcp로 우선 수행한다. 본 문서·핸드오프는 Codex/외부 AI 인계 시에도 그대로 유효하다. (검토: `sync/_meta/codex이관_claude환원_검토_2026-06-16.md`)

## 0. 우선순위

1. 루트 `AGENTS.md`와 과목별 `AGENTS.md`
2. 본 문서
3. `sync/_meta/이식용_핸드오프_프롬프트_2026-06-15.md`
4. `5.기타/프롬프트 등 개선/claude_code_package_v2/prompts/03-wiki-rollup_쟁점아티클_v1.md`
5. `5.기타/프롬프트 등 개선/claude_code_package_v2/prompts/10_v37_apkg_빌드_파이프라인.md`

`claude_code_package_v2`는 레거시 패키지명이다. 실행 주체를 Claude로 고정하지 말고, 실제 존재하는 파일·스크립트만 사용한다.

## 1. 현재 상태

- 카드 최신: v37, 19,629장.
- 카드 소스: `outputs/02_cards_v37/*.md` 276개.
- apkg: `outputs/anki/v37/apkg/` 과목별 7개.
- 빌드 리포트: `outputs/anki/v37/apkg/_apkg_report.md` 기준 Basic 8,172 / Cloze 11,457.
- 위키 쟁점 아티클: `sync/wiki/쟁점/` 36개.
- 미완 쟁점: 약 53개. 중단 사유는 코드 오류가 아니라 Claude Code 구독 접근 비활성화로 인한 서브에이전트 인증 실패.

## 2. 소스 맵

| 용도 | 경로 |
|---|---|
| 카드 readable 소스 | `outputs/02_cards_v37/*.md` |
| OCR 원문 | `outputs/01_ocr_llamaparse/*.md` |
| apkg 빌더 | `.agent/scripts/build_v37_apkg.py` |
| apkg 산출 | `outputs/anki/v37/apkg/` |
| 위키 산출 | `sync/wiki/쟁점/*.md` |
| 주제 인벤토리 | `.agent/state/wiki_topic_inventory.json` |
| anchor 검증 | `.agent/scripts/anchor_verify_batch.py`, `.agent/state/anchor_verify_summary.md` |

외부 법령·판례 확인은 korean-law-mcp 또는 국가법령정보센터 API 반환값만 공적 원문 예외 소스로 취급한다.

## 3. 리서치 절차

1. 기존 위키 확인: `sync/wiki/쟁점/{쟁점명}.md`.
2. 카드 검색: `outputs/02_cards_v37/`에서 쟁점명, 동의어, 사건번호, 조문번호를 검색한다.
3. 카드 근거가 부족하거나 충돌하면 OCR 원문(`outputs/01_ocr_llamaparse/`)으로 역확인한다.
4. 판례·조문 anchor는 필요할 때만 korean-law-mcp로 확인한다.
5. 카드나 원문에서 확인되지 않는 단정은 쓰지 않는다. 출력은 "자료 부족"으로 남긴다.

## 4. 위키 roll-up 규칙

저장 위치: `sync/wiki/쟁점/{쟁점명}.md`.

```markdown
---
type: 쟁점아티클
과목: {과목}
주제: {쟁점}
생성: YYYY-MM-DD
anchor검증: 미검증
---
# {쟁점명}
## 1. 조문
## 2. 요건
## 3. 일반론 설시 판례
## 4. 예외·주요 케이스
## 5. 관련 태그 클러스터
```

- 본문은 40~70줄을 기준으로 한다.
- cloze 마커 `{{cN::...}}`는 평문화한다.
- 한자와 외국어 표기는 한국어로 정리한다.
- 표 셀·각주 안에는 백링크를 넣지 않는다.
- 요약 문장에는 카드 원문 발췌 각주를 붙인다.
- 판례 백링크는 선고일·사건번호가 검증된 경우에만 `[[대판 YYYY.M.DD, YY다XXXX]]` 형식으로 둔다.
- 생성 후 `sync/wiki/_index.md`에 과목별 1줄을 추가한다.

## 5. 미완 대상

민법: 부당이득, 근저당권, 법정지상권, 명의신탁, 공유, 손해배상_민법, 물상보증, 양도담보, 공동저당, 채권질권, 점유취득시효, 동시이행항변권, 전세권.

형법: 교사범, 중지미수, 배임죄, 횡령죄, 결과적가중범, 뇌물죄, 공무집행방해죄, 문서죄_형법, 위증죄_무고죄, 친족상도례, 합동범, 보이스피싱_관련범죄, 불가벌적_사후행위, 심신장애_원인자유행위, 명예훼손죄.

헌법: 헌법소원_적법요건, 과잉금지원칙, 권한쟁의심판, 탄핵심판, 선거권, 소급입법금지원칙, 표현의자유, 신체의자유, 위헌법률심판, 신뢰보호원칙, 정당해산심판, 면책특권, 포괄위임금지원칙, 양심의자유, 행복추구권.

민사소송법: 처분권주의, 변론주의, 소송물, 소이익, 당사자적격, 증명책임, 필수적공동소송, 재심, 불이익변경금지, 재판상자백.

## 6. 카드·apkg 작업

카드를 바꾼 경우에만 빌드한다.

```powershell
python .agent/scripts/build_v37_apkg.py
```

빌드 후 `outputs/anki/v37/apkg/_apkg_report.md`에서 다음을 확인한다.

- 총 카드 수
- Basic/Cloze 수
- 과목별 apkg 7개 존재
- 한자 잔존 0
- 번호 없는 cloze 0

## 7. 병렬 작업 기준

- 쟁점별 카드 검색·초안 작성은 과목 또는 쟁점 단위로 병렬화할 수 있다.
- 같은 파일(`sync/wiki/_index.md`, 같은 쟁점 md)은 동시에 편집하지 않는다.
- 산출물 작성 전 대상 파일의 존재·수정시각을 확인한다.
- `0.공유드라이브/`는 읽기·복사 외 작업 금지.
- 파일 이동·이름변경·복사는 이 워크플로우 범위가 아니다. 필요한 경우 파일 분류 규칙과 로그 규칙을 우선한다.

## 8. 카드 생명주기·note_key·중복방지 (2026-06-16 신설)

출처: `CODEX_BOOTSTRAP_REPORT.md.md` §11~13·20·23의 채택분. SQLite·CSV batch 설계는 기각(기존 JSON 상태·v37 apkg 유지).

### 8.1 note_key (안정 키)

- 형식: `{key}::{card_type}::{seq}` — `key`는 issue_id(있을 때) 또는 `{출처약어}_{소제목}`. 예: `민법_채권자대위권::requirement::001`.
- note_key는 **카드 내용이 바뀌어도 변경하지 않는다.** 내용 개선 시 같은 note_key로 갱신한다.
- 금지: 기존 note_key 변경, 같은 내용에 새 note_key 부여, 날짜를 note_key에 포함.
- 현 빌더(`build_v37_apkg.py`)는 genanki guid를 **내용 기반**(`guid_for(src, blk[:30], 정규화텍스트)`)으로 만든다 → 카드 텍스트 수정 시 guid가 바뀌어 Anki **복습이력이 분실**된다. 목표 = guid를 안정 note_key에서 파생. (코드 전환은 재임포트 영향이 있어 테스트 후 별도 적용 — `sync/_meta/codex이관_claude환원_검토_2026-06-16.md` §5)

### 8.2 카드 생명주기

`draft → pending → approved → batched → exported → updated`, 분기 `suspended`/`rejected`.

- `draft→pending`: source 있고 앞/뒤(또는 빈칸)가 채워짐.
- `pending→approved`: 중복 아니고 카드화 가치 있음.
- `approved→batched→exported`: 빌드/임포트 단계.
- `exported→updated`: 같은 note_key 내용 보강(다음 빌드에 업데이트로 포함).
- `rejected`: source 부족·중복·과도 분량·일회성 실수. 사용자 명시 허가 없이 재생성 금지.

### 8.3 중복방지

카드 생성 전 순서대로 확인:
1. 같은 note_key 존재 → 새로 만들지 말고 갱신.
2. 같은 `key + card_type + 정규화 앞면` 존재 → 병합.
3. 이미 exported면 새 후보 대신 기존을 `updated`로.
4. rejected였던 것은 재생성 금지(사용자 허가 시 예외).

