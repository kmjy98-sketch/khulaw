# 로스쿨 단권화·사례집 자동 카드화 파이프라인 (v3.6 Phase 1)

Claude Code 이관용 패키지. v3.5.2 수동 워크플로우(Claude Project·Gem 복사·붙여넣기)를 자동화.
v3.6 Phase 1.1 (2026-05): Gemini/AI Studio 제거, 전 단계 Claude 통일.

## v3.6 paradigm shift

| 항목 | v3.5.2 | v3.6 (현재) |
|---|---|---|
| 파이프라인 | 5단계 (01·02·04·06) | **4단계 (01·02-wiki·02-card·06)** |
| 책 입력 | 마킹 의존 | **책 유형 자동 식별 → 위키 → 카드** |
| 태그 | `유형::조문` 단축 | **`속성::요건`+`주제::채권자취소권` 2축** |
| Obsidian 통합 | 별도 | **위키 마크다운 vault import 가능** |
| 학습 보조 | NotebookLM 소크라테스 | **Anki 카드 메인** (NotebookLM 보조) |

## 0단계 — Claude Code에 알리기

Claude Code 터미널에서 이 폴더로 이동 후 한 번만:

```
SKILL.md 읽고 v3.6 Phase 1 패키지 구조 파악해.
환경 설정 안 됐으면 .env.example 보고 안내해줘.
```

이후엔 자연어 명령만.

## 자연어 명령 예시

| 하고 싶은 일 | 입력 |
|---|---|
| 새 단권화 책 전체 자동 (위키화 + 카드화) | `inputs/raw_pdf/송영곤논점민법강의.pdf 전체 처리. 단권화` |
| 위키화만 (Obsidian vault 위해) | `inputs/raw_pdf/송영곤논점민법강의.pdf 위키화만` |
| 위키 출력 → 카드화만 | `outputs/02_wiki/송영곤_chunk_001_wiki.md 02-card로 변환` |
| 사례집 풀이 포함 카드화 | `inputs/cases/김춘환민법사례연습.pdf 06b로 카드화` |
| 사례집 1문제 정밀 | `cases/문제5.md 06a로 카드화` |
| 사후 검증 | `검증필요::AI추출 카드 grounding 페이지 정리` |
| 선행 단서 카드 추가 | `02-card 호출할 때 generate_precursor_cards: true 켜줘` |

## 4가지 워크플로우

### A) 단권화 책 전체 자동 (300p 책 1권 → 약 1.5시간, $8~15)

```
입력: inputs/raw_pdf/책이름.pdf
명령: "책이름.pdf 처리. 단권화"
실행:
  1. PDF 100p 단위 분할
  2. 각 청크 → Claude Sonnet 4.6로 OCR (Mode B default)
     → outputs/01_ocr/책이름_chunk_NNN.md
  3. 각 청크 → Claude Opus 4.7로 위키화 ⭐ v3.6 신규
     - 책 유형 자동 식별 (단권화/사례집/판례집/객관식/...)
     - 속성 라벨 자동 (정의/요건/효과/학설/판례/...)
     - Obsidian callout 변환 ([논점정리] → > [!summary])
     - backlink [[쟁점명]] 부착
     → outputs/02_wiki/책이름_chunk_NNN_wiki.md
  4. 위키 출력 → Claude Opus 4.7로 카드화
     - 속성 라벨로 노트 타입 자동 분기 (rule/case_law/mcq)
     - 표 자동 분해
     → outputs/02_cards/책이름_TSV.txt
출력: Anki Import 가능한 TSV + Obsidian vault import 가능한 위키
```

### B) 사례집 풀이 포함 자동 (06b extract)

```
입력: inputs/cases/사례집이름.pdf
명령: "사례집이름.pdf 06b"
실행:
  1. 06b_extract.py → 풀이 영역 자동 식별 + 쟁점 추출
  2. 모든 카드에 `검증필요::AI추출` 태그 자동
  → outputs/06_cases/사례집이름_06b_TSV.txt
사후 검증 필수: Anki에서 tag:검증필요::AI추출 검색 → 풀이와 대조
```

### C) 사례집 정밀 (06a manual)

```
입력: inputs/cases/문제번호.md (case_problem + user_issue_list)
명령: "문제번호.md 06a"
실행: 06a_manual.py 호출
출력: 검증필요 태그 없음 (사용자가 이미 검증한 쟁점)
```

### D) 02-wiki 단독 (Obsidian vault 위해서)

```
입력: inputs/raw_pdf/책이름.pdf
명령: "책이름.pdf 위키화만"
실행: PDF 분할 → 01 OCR → 02-wiki까지만
출력: outputs/02_wiki/ (Obsidian vault에 그대로 복사 가능)
```

## 폴더 구조

```
claude_code_package_v2/
├── README.md              ← 이 파일
├── SKILL.md               ← Claude Code 자동 읽음
├── INSTRUCTIONS.md        ← 첫 명령 가이드
├── .env.example
├── requirements.txt
├── .gitignore
│
├── prompts/               ← v3.6 Phase 1 프롬프트 11개
│   ├── 01_claude_마킹_구조_조문_추출_v3.6.md       ⭐ v3.6 Phase 1.1 신규 (default)
│   ├── 01_gemini3.1pro_마킹_구조_조문_추출_v3.6.md  (legacy, 직접 Gem 사용 시)
│   ├── 02-wiki_claude_위키화_v3.6.xml          ⭐ 신규
│   ├── 02-wiki_gemini3.1pro_위키화_v3.6.md     ⭐ 신규
│   ├── 02-card_claude_Anki카드화_v3.6.xml      (02번 → 02-card 재명명)
│   ├── 02-card_gemini3.1pro_Anki카드화_v3.6.md
│   ├── 04_notebooklm_소크라테스.md             (보조용 강등)
│   ├── 05_anki_덱구조_태그_모델라우팅.md       (4단계 + 태그 2축)
│   ├── 06a_claude_사례집문제_manual_v3.6.xml
│   ├── 06a_gemini3.1pro_사례집문제_manual_v3.6.md
│   ├── 06b_claude_사례집문제_extract_v3.6.xml
│   └── 06b_gemini3.1pro_사례집문제_extract_v3.6.md
│
├── scripts/
│   ├── pdf_split_100p.py
│   ├── _utils.py            (태그 2축 검증, {불명}/[불명] 둘 다 호환)
│   ├── 01_ocr.py            (Claude Sonnet 4.6 default, --model haiku/opus 옵션)
│   ├── 02_wiki.py           ⭐ 신규 — 위키화 (Claude Opus 4.7)
│   ├── 02_card.py           (02_cardify → 02_card 재명명, auto note_type)
│   ├── 06a_manual.py
│   ├── 06b_extract.py
│   └── anki_import_assemble.py
│
├── inputs/
│   ├── raw_pdf/             ← 단권화 PDF
│   └── cases/               ← 사례집 PDF·md
│
├── outputs/
│   ├── 01_ocr/              ← 01번 OCR
│   ├── 02_wiki/             ⭐ 신규 — 위키 마크다운
│   ├── 02_cards/            ← 02-card 단권화 TSV
│   └── 06_cases/            ← 06a/06b 사례집 TSV
│
└── logs/                  ← API 호출 로그·에러·비용
```

## 환경 설정 (한 번만)

1. **Python 3.10+** 설치 확인
2. **의존성 설치**:
   ```bash
   pip install -r requirements.txt
   ```
3. **API key 발급**:
   - Anthropic: https://console.anthropic.com
   - (v3.6 Phase 1.1: Google AI/Gemini 사용 안 함)
4. **`.env` 파일 생성**:
   ```bash
   cp .env.example .env
   # 실제 키 입력
   ```

또는 Claude Code에 `환경 설정 도와줘`.

## 비용 예상 (v3.6)

| 작업 | 비용 |
|---|---|
| 01 OCR (Claude Sonnet 4.6), 300p 책 | $3~6 (Haiku 옵션 시 $1~2) |
| 02-wiki (Claude Opus 4.7), 300p 책 | $3~7 ⭐ 신규 단계 |
| 02-card (Claude Opus 4.7), 위키 출력 | $2~4 |
| 06b 사례집, 사례 20문제 | $1.5~3 |
| **책 1권 전체 (Sonnet OCR)** | **$10~20** (v3.5.2 $5~10에서 약 2배 증가) |
| **책 1권 전체 (Haiku OCR)** | **$8~16** (저비용 OCR + Opus 위키·카드) |

비용 증가 원인: ①위키화 단계 추가 ②01번 OCR이 Gemini($1.5~3) → Claude Sonnet($3~6)으로 1.5~2배.
책 1권당 5시간 절감으로 시간 대비 효율은 유지. 월 한도 $50 default — 초과 시 자동 중단.

비용 절감 옵션:
- 01번 OCR을 Haiku로 (--model haiku): OCR 정확도 약간 하락하지만 비용 1/4
- 02-wiki를 Sonnet으로 다운그레이드 가능 (별도 옵션 추후 추가)

## 시범 운영 권장 순서 (v3.6 Phase 1)

1. **환경 설정 확인**
2. **01번 단독 테스트**: 첫 청크(100p)만 → 마킹 인식 확인
3. **02-wiki 단독 테스트**: 01번 출력 1청크 → 책 유형 추정·속성 라벨·callout 변환 확인
4. **02-card 단독 테스트**: 위키 출력 1챕터 → 노트 타입 자동 분기·표 분해 확인
5. **06b 단독 테스트**: 사례집 1문제(풀이 포함) → 풀이 영역 식별·검증필요 태그 확인
6. **Anki Import 후 hallucination 측정**: 100장당 3장 초과 → 프롬프트 수정 검토
7. **전체 파이프라인 1회 실행**: 형법총론 또는 민법1 책 1권

## 안전망

- 모든 API 호출 결과는 `logs/`에 timestamp별 저장
- Anki Import 전 TSV 자동 검증 (열·태그 형식·태그 2축·구버전 잔존 경고)
- 06b 카드는 `검증필요::AI추출` 태그 자동 부착 — 사후 검증 필수
- API key는 `.env`에만, git commit 금지 (`.gitignore` 포함)
- 월 비용 한도 초과 시 자동 중단

## v3.5.2 → v3.6 마이그레이션

이미 v3.5.2 카드를 Anki에 갖고 있다면:
1. v3.5.2 카드를 그대로 유지 (보류·검증필요 태그 호환)
2. 새 학습 자료부터 v3.6 파이프라인 사용
3. Anki Browse에서 `tag:유형::*` 검색 → 수동으로 `속성::`+`주제::`로 마이그레이션 (선택)
4. 또는 v3.5.2와 v3.6 카드를 별개 덱으로 운영하다 점진적 통합

## 문의

자세한 작동 방식은 `SKILL.md`. 명령이 막히면 Claude Code에 `현재 상태 알려줘`.
