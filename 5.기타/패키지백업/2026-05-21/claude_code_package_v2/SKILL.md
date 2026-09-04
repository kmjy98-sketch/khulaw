# SKILL: 로스쿨 단권화·사례집 자동 카드화 파이프라인 (v3.6 Phase 1)

이 패키지는 한국 로스쿨 학습 자료(단권화 책·사례집)를 Obsidian 위키 마크다운으로 구조화 후 Anki 카드로 자동 변환한다.
사용자(이권민)는 연세대 로스쿨 1학년, 변시 준비 중.

## v3.6 paradigm shift

| 항목 | v3.5.2 | v3.6 (현재) |
|---|---|---|
| 파이프라인 | 01 OCR → 02 카드 → 04 소크라테스 → 06 사례집 (5단계) | **01 OCR → 02-wiki → 02-card → 06 사례집** (4단계) |
| 학습 보조 | NotebookLM 소크라테스 메인 | **Anki 카드 메인** (NotebookLM 보조로 강등) |
| 책 입력 | 마킹 한 부분 OCR | **책 유형 자동 식별 → 위키 마크다운 → 카드** |
| 태그 체계 | 과목/유형/난이도/출처/보류 | **속성 + 주제 2축** (`유형::` → `속성::`+`주제::`) |
| Mode | Mode A (마킹) default | **Mode B (전체)** default — 02-wiki가 속성 자동 분류 |
| Obsidian | 별도 | **위키 마크다운 vault에 그대로 import** |

## 핵심 원칙 (절대 위반 금지)

1. **prompts/ 폴더의 v3.6 프롬프트는 수정하지 마라.** 그 안의 규칙(abstention, grounding, korean_law_safeguards 4축, 마크다운 충돌 회피 매핑)이 환각 방지·Obsidian 호환의 핵심이다. 그대로 API에 전달.
2. **API 호출 결과를 임의 후처리 금지.** 출력한 위키 마크다운·TSV·grounding·verification 체크리스트를 그대로 보존. 사용자가 검증 후 직접 수정.
3. **사용자가 v3.6 Phase 1 시범 운영 단계.** v3.5.2와 병행. 첫 책 1권 처리 후 사용자 검토 시간, 다음 책 진행 전 확인.
4. **환각·누락 발생 시 즉시 보고.** 100장당 3장 초과 → 작업 중단.
5. **02-wiki 출력은 Obsidian 호환 마크다운.** callout 변환·{불명}·이스케이프 적용 검증 필수.

## 사용자 컨텍스트

- 연세대 로스쿨 17기 (1학년), 변시 준비 중
- 1학년 2학기 학습 과목: 민법1·민법3·형법총론·헌법총론
- 단권화 책: 송영곤 [2026] 논점민법강의 12판, 김성돈 형법총론 등
- Anki 운영: FSRS, 7과목 sub-deck
- Obsidian 단권화 vault 보유 — 02-wiki 출력 그대로 import 가능

## v3.6 4단계 파이프라인

```
[PDF 책]
    │
    ▼
Step 0: pdf_split_100p.py (100p 사전 분할)
    │
    ▼
Step 1: 01_ocr.py (Claude Sonnet 4.6 default, Mode B default)
    │  → outputs/01_ocr/책이름_chunk_NNN.md
    ▼
Step 2: 02_wiki.py 위키화 (Claude Opus 4.7) ⭐ v3.6 신규
    │  - 책 유형 자동 식별 (7종 enum)
    │  - 속성 라벨 자동 부착 (10종)
    │  - 마크다운 충돌 회피 (callout 변환, {불명})
    │  - Obsidian backlink [[쟁점명]] 생성
    │  → outputs/02_wiki/책이름_chunk_NNN_wiki.md
    ▼
┌──── Step 3a ─────┐    ┌──── Step 3b ─────┐
│ 02_card.py       │    │ 06a_manual.py    │
│ (단권화 카드화)  │    │ 06b_extract.py   │
│ 속성 자동 분기   │    │ 사례집 카드화    │
│ rule/case_law/   │    │ 검증필요 태그    │
│ mcq              │    │                  │
│ → outputs/02_cards/   │ → outputs/06_cases/
└──────────────────┘    └──────────────────┘
                │
                ▼
Step 4: anki_import_assemble.py
    Anki Import용 단일 TSV 조립
```

## 워크플로우

### A) 단권화 책 전체 카드화 (300p 책 1권 → 약 1.5시간, $8~15)

```
사용자 명령: "송영곤논점민법강의.pdf 처리"
실행:
  1. scripts/pdf_split_100p.py inputs/raw_pdf/송영곤논점민법강의.pdf
  2. 각 청크 01_ocr.py (Claude Sonnet 4.6, Mode B)
     → outputs/01_ocr/송영곤논점민법강의_chunk_NNN.md
  3. 각 청크 02_wiki.py (Claude Opus 4.7)
     - book_type_hint: 단권화 (사용자 알려준 경우)
     - 출력: outputs/02_wiki/송영곤논점민법강의_chunk_NNN_wiki.md
     - 책 유형 추정 신뢰도 보고
  4. 사용자에게 검토 권유: "02-wiki 결과 확인. Obsidian vault 복사? 02-card 진행?"
  5. 02_card.py 카드화 (note_type=auto, 속성 라벨로 자동 분기)
     → outputs/02_cards/송영곤논점민법강의_chunk_NNN_TSV.txt
```

### B) 사례집 풀이 포함 자동 카드화 (06b extract)

```
사용자: "김춘환민법사례연습.pdf 06b로 카드화"
실행:
  1. 06b_extract.py inputs/cases/김춘환민법사례연습.pdf
     - prompts/06b_claude_사례집문제_extract_v3.6.xml
  2. 풀이 영역 식별 + TSV → outputs/06_cases/...
  3. 모든 카드에 `검증필요::AI추출` 태그 자동
  4. 사용자에게 사후 검증 안내
```

### C) 사례집 정밀 카드화 (06a manual)

```
사용자: "문제5.md 06a로 카드화"
실행:
  1. inputs/cases/문제5.md 읽기 (case_problem + user_issue_list 작성됨)
  2. 06a_manual.py → outputs/06_cases/...
```

### D) 02-wiki 단독 (Obsidian vault 위해서)

```
사용자: "송영곤논점민법강의.pdf 위키화만"
실행:
  1. PDF 분할
  2. 02_wiki.py만 호출
  3. outputs/02_wiki/...
  4. (선택) Obsidian vault 복사 (사용자 vault 경로 알면)
```

## API 호출 규칙

### Claude Sonnet 4.6 (01번 OCR) — v3.6 Phase 1.1
- 모델: `claude-sonnet-4-6` (default), `claude-haiku-4-5` 옵션 (저비용), `claude-opus-4-7` 옵션 (최고)
- 필수: `system` (prompts/01_claude...md), `max_tokens` 32000 (Sonnet) / 16000 (Haiku)
- PDF: document content block (base64)
- 실패 시 재시도 3회
- v3.6 Phase 1.1 변경 (2026-05): Gemini 3.1 Pro → Claude (사용자 결정, AI Studio 미사용)

### Claude Opus 4.7 (02-wiki·02-card·06a·06b)
- 모델: `claude-opus-4-7`
- 필수: `system` (해당 v3.6 .xml), `max_tokens` 32000, `temperature` 1.0
- 큰 입력 (PDF 직접) → `document` content block

## 출력 자동 검증

### 02-wiki (scripts/02_wiki.py 내장)
1. YAML frontmatter 존재
2. 책 유형 추정 메시지
3. 속성 라벨 부착 (3개 이상)
4. **Obsidian callout 변환** — `> [!summary]`·`> [!example]` 등으로
5. `[불명]` → `{불명}` 변환
6. END_OF_CHUNK 메시지

### 02-card·06a·06b (scripts/_utils.py)
1. TSV 컬럼 일치
2. **태그 2축**: `과목::`+`속성::`+`난이도::` 필수
3. **구버전 잔존 경고**: `유형::`·`쟁점::` 발견 시
4. {불명}/[불명] 비율 (50% 초과 시)
5. 06b: `검증필요::AI추출` 태그 부착 여부

## 응답 톤

사용자는 한국어, 두괄식, 간결 선호.
- 보고는 짧게: "02-wiki 완료 (5분, 단권화 95%, 속성 라벨 23개)"
- 에러는 사실 + 다음 행동 제안
- 환각·누락 즉시 보고

## v3.6 Phase 1 시범 운영 (현재)

- **첫 1~2주: 단권화 1챕터(50p)만 시범**
- 책 유형 추정 신뢰도 90%+ 확인 후 다음 책
- 100장당 hallucination 측정
- 3장 초과 시 작업 중단

## 비용 모니터링

- Claude Sonnet 4.6 (01번 OCR default): input $3/M, output $15/M
- Claude Haiku 4.5 (01번 OCR 저비용): input $0.80/M, output $4/M
- Claude Opus 4.7 (02-wiki·02-card·06a·06b): input $15/M, output $75/M
- 각 호출 후 누적 비용 표시
- 월 누적 `logs/cost_YYYY-MM.json`

### v3.6 비용 증가 주의
- 02-wiki 추가로 책 1권 비용 v3.5.2 대비 약 1.8배
- 책 1권 예상: v3.5.2 $5~10 → v3.6 $8~15
- 월 한도 ($50 default) 초과 시 작업 중단

## 안전 규칙

- API key는 `.env`에서만. 코드·로그 노출 금지.
- 사용자 PDF는 inputs/에만.
- 명시 안 한 작업 금지 (자동 git commit, 자동 Obsidian 동기화, 자동 Anki Import).
- `.env` 미설정 시 작업 중단 후 `.env.example` 안내.

## 막힐 때

- API 에러 → logs/ 확인 + 재시도 3회 + 사용자 보고
- 프롬프트 출력 형식 위반 → 원본 outputs/ 저장 + 사용자 확인 (임의 수정 금지)
- 비용 예상 초과 → 작업 중단 + 사용자 확인
- 사용자 명령 모호 → 추측 말고 되묻기
