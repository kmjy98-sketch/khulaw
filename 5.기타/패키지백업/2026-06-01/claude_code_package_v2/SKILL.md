# SKILL: 로스쿨 단권화·사례집 카드화 파이프라인 (v3.6 Phase 1.2 — Claude Code 운영 모드)

이 패키지는 한국 로스쿨 학습 자료(단권화 책·사례집)를 Obsidian 위키 마크다운으로 구조화 후 Anki 카드로 변환하는 **프롬프트 묶음**이다.
사용자(이권민)는 연세대 로스쿨 1학년, 변시 준비 중.

## v3.6 Phase 1.2 운영 모드 (2026-05-21)

**Claude Code(이 세션)에서 직접 PDF 처리**. 외부 API 스크립트(scripts/*.py)는 legacy로 보존하지만 사용하지 않는다.

| 항목 | 운영 방식 |
|---|---|
| PDF 처리 | Claude Code에 PDF 첨부 → prompts/{단계}_claude.xml을 system context로 적용 → 결과 저장 |
| API 키 | 불필요 (Claude Code 구독으로 처리) |
| .env | 사용 안 함 (legacy 보존만) |
| scripts/*.py | 사용 안 함 (legacy 보존만, 추후 API key 발급 시 사용 가능) |
| 출력 | Claude Code가 outputs/{단계}/에 직접 저장 |

## v3.6 paradigm shift (변경 없음)

| 항목 | v3.5.2 | v3.6 |
|---|---|---|
| 파이프라인 | 01 OCR → 02 카드 → 04 소크라테스 → 06 사례집 (5단계) | **01 OCR → 02-wiki → 02-card → 06 사례집** (4단계) |
| 학습 보조 | NotebookLM 소크라테스 메인 | **Anki 카드 메인** (NotebookLM 보조로 강등) |
| 책 입력 | 마킹 한 부분 OCR | **책 유형 자동 식별 → 위키 마크다운 → 카드** |
| 태그 체계 | 과목/유형/난이도/출처/보류 | **속성 + 주제 2축** (`유형::` → `속성::`+`주제::`) |
| Mode | Mode A (마킹) default | **Mode B (전체)** default — 02-wiki가 속성 자동 분류 |
| Obsidian | 별도 | **위키 마크다운 vault에 그대로 import** |

## 핵심 원칙 (절대 위반 금지)

1. **prompts/ 폴더의 v3.6 프롬프트는 system context로 그대로 흡수.** 그 안의 규칙(abstention, grounding, korean_law_safeguards 4축, 마크다운 충돌 회피 매핑)이 환각 방지·Obsidian 호환의 핵심이다.
2. **출력을 임의 후처리 금지.** 위키 마크다운·TSV·grounding·verification 체크리스트를 그대로 outputs/에 보존. 사용자가 검증 후 직접 수정.
3. **사용자가 v3.6 Phase 1.2 시범 운영 단계.** v3.5.2와 병행. 첫 책 1권 처리 후 사용자 검토 시간, 다음 책 진행 전 확인.
4. **환각·누락 발생 시 즉시 보고.** 100장당 3장 초과 → 작업 중단.
5. **02-wiki 출력은 Obsidian 호환 마크다운.** callout 변환·{불명}·이스케이프 적용 검증 필수.
6. **한자 병기 금지** (CLAUDE.md #37). 동음이의는 한국어 풀이로만 구별.

## 사용자 컨텍스트

- 연세대 로스쿨 17기 (1학년), 변시 준비 중
- 1학년 2학기 학습 과목: 민법1·민법3·형법총론·헌법총론
- 단권화 책: 송영곤 [2026] 논점민법강의 12판, 김성돈 형법총론 등
- Anki 운영: FSRS, 7과목 sub-deck
- Obsidian 단권화 vault 보유 — 02-wiki 출력 그대로 import 가능

## v3.6 4단계 파이프라인 (Claude Code 모드)

```
[PDF 책]
    │
    ▼
Step 0: PDF 분할 (선택)
    - Claude Code에 PDF 첨부 가능 크기면 분할 불필요
    - Claude API 한계: 32MB / 100p — 큰 책은 사용자가 분할 후 청크 업로드
    │
    ▼
Step 1: 01 OCR (선택)
    - prompts/01_claude_마킹_구조_조문_추출_v3.6.md를 system context로 적용
    - Claude Code가 PDF native 처리 → outputs/01_ocr/책이름_chunk_NNN.md
    - Mode B (전체 추출) default
    - 깔끔한 인쇄 PDF는 01번 건너뛰고 바로 02-wiki로 진행 가능
    ▼
Step 2: 02-wiki 위키화 ⭐ v3.6 신규
    - prompts/02-wiki_claude_위키화_v3.6.xml을 system context로 적용
    - 책 유형 자동 식별 (7종 enum)
    - 속성 라벨 자동 부착 (10종)
    - 마크다운 충돌 회피 (callout 변환, {불명})
    - Obsidian backlink [[쟁점명]] 생성
    → outputs/02_wiki/책이름_chunk_NNN_wiki.md
    ▼
┌──── Step 3a ─────┐    ┌──── Step 3b ─────┐
│ 02-card 단권화   │    │ 06a 정밀 / 06b 자동│
│ prompts/02-card  │    │ prompts/06a or 06b │
│ _claude_         │    │ _claude_           │
│ Anki카드화.xml   │    │ 사례집문제_*.xml   │
│ 속성 자동 분기   │    │ 사례집 카드화      │
│ → outputs/02_cards/   │ → outputs/06_cases/
└──────────────────┘    └──────────────────┘
                │
                ▼
Step 4: Anki Import
    - 사용자가 outputs/ 안의 TSV를 Anki Import 메뉴로 직접 가져오기
    - 자동 조립 스크립트(anki_import_assemble.py)는 사용 안 함 (수동 처리)
```

## 워크플로우 (Claude Code 운영)

### A) 단권화 책 전체 카드화 (300p 책 1권 → 약 1.5~2시간)

```
사용자: "송영곤논점민법강의.pdf 단권화 처리해줘"
+ PDF 첨부 (inputs/raw_pdf/ 안에 둠 또는 채팅에 직접)

Claude Code 실행:
  1. (사용자 사전 분할) PDF가 100p 초과면 사용자가 청크로 나눔 또는 Claude Code에 청크 단위로 첨부
  2. 청크별로:
     a. prompts/01_claude_마킹_구조_조문_추출_v3.6.md 적용 → OCR
        → outputs/01_ocr/송영곤논점민법강의_chunk_NNN.md 저장
     b. prompts/02-wiki_claude_위키화_v3.6.xml 적용 → 위키화
        → outputs/02_wiki/송영곤논점민법강의_chunk_NNN_wiki.md 저장
     c. 사용자에게 검토 권유: "위키 출력 확인. Obsidian vault 복사? 02-card 진행?"
     d. prompts/02-card_claude_Anki카드화_v3.6.xml 적용 → 카드화
        → outputs/02_cards/송영곤논점민법강의_chunk_NNN_TSV.txt 저장
```

### B) 사례집 풀이 포함 자동 카드화 (06b)

```
사용자: "김춘환민법사례연습.pdf 06b로 카드화"
+ PDF 첨부

Claude Code 실행:
  1. prompts/06b_claude_사례집문제_extract_v3.6.xml 적용
  2. 풀이 영역 식별 + TSV → outputs/06_cases/...
  3. 모든 카드에 `검증필요::AI추출` 태그 자동
  4. 사용자에게 사후 검증 안내
```

### C) 사례집 정밀 카드화 (06a)

```
사용자: "문제5.md 06a로 카드화"
+ inputs/cases/문제5.md (case_problem + user_issue_list 작성됨)

Claude Code 실행:
  1. prompts/06a_claude_사례집문제_manual_v3.6.xml 적용
  2. → outputs/06_cases/...
```

### D) 02-wiki 단독 (Obsidian vault 위해서)

```
사용자: "송영곤논점민법강의.pdf 위키화만"
+ PDF 첨부

Claude Code 실행:
  1. prompts/02-wiki_claude_위키화_v3.6.xml 적용
  2. → outputs/02_wiki/
  3. (선택) Obsidian vault 복사
```

## prompts 사용 규칙

Claude Code가 작업 시작 시:
1. 사용자 명령에서 단계 식별 (01·02-wiki·02-card·06a·06b)
2. 해당 단계의 `prompts/{단계}_claude_*.xml` 또는 `.md` 파일을 Read 도구로 읽기
3. 그 안의 규칙(`<system>`, `<absolute_prohibitions>`, `<verification_protocol>` 등)을 현재 작업의 가이드로 적용
4. 사용자 첨부 PDF를 처리 (Claude Code의 PDF native 지원)
5. 출력을 outputs/{단계}/에 Write로 저장
6. verification_protocol 체크리스트를 사용자에게 보고

## 출력 자동 검증 (Claude Code가 직접 수행)

### 02-wiki 검증
1. YAML frontmatter 존재
2. 책 유형 추정 메시지
3. 속성 라벨 부착 (3개 이상)
4. **Obsidian callout 변환** — `> [!summary]`·`> [!example]` 등으로
5. `[불명]` → `{불명}` 변환
6. END_OF_CHUNK 메시지

### 02-card·06a·06b 검증
1. TSV 컬럼 일치
2. **태그 2축**: `과목::`+`속성::`+`난이도::` 필수
3. **구버전 잔존 경고**: `유형::`·`쟁점::` 발견 시
4. {불명}/[불명] 비율 (50% 초과 시)
5. 06b: `검증필요::AI추출` 태그 부착 여부

## 응답 톤

사용자는 한국어, 두괄식, 간결 선호.
- 보고는 짧게: "02-wiki 완료 (단권화 95%, 속성 라벨 23개)"
- 에러는 사실 + 다음 행동 제안
- 환각·누락 즉시 보고

## v3.6 Phase 1.2 시범 운영 (현재)

- **첫 1~2주: 단권화 1챕터(50p)만 시범**
- 책 유형 추정 신뢰도 90%+ 확인 후 다음 책
- 100장당 hallucination 측정
- 3장 초과 시 작업 중단

## 안전 규칙

- API key 사용 안 함 — Claude Code 구독으로 처리
- 사용자 PDF는 inputs/에 두거나 채팅에 직접 첨부
- 명시 안 한 작업 금지 (자동 git commit, 자동 Obsidian 동기화, 자동 Anki Import).
- 한자 병기 금지 (CLAUDE.md #37).
- 동음이의는 한국어 풀이로 구별.
- 외국어 표현 금지 (한국어 대역만).

## legacy 보존

다음은 추후 API key 발급 시 사용 가능하도록 보존:
- `scripts/*.py` — 외부 API 자동화 (Anthropic API key 필요)
- `.env`, `.env.example` — API key 설정
- `requirements.txt` — Python 의존성

현 운영 모드(v3.6 Phase 1.2)에서는 사용 안 함.

## 막힐 때

- 프롬프트 출력 형식 위반 → 원본 outputs/ 저장 + 사용자 확인 (임의 수정 금지)
- 사용자 명령 모호 → 추측 말고 되묻기
- PDF가 너무 크면 → 사용자에게 분할 요청 (Claude API 한계: 32MB / 100p)
