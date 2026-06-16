# 로스쿨 단권화·사례집 자동 카드화 파이프라인 (v3.6 Phase 2 — 2모델 역할분담)

안티그래비티(Gemini 3.5 Flash) + Claude Opus 4.8 2모델 분담 프롬프트 묶음 패키지.
v3.5.2 수동 워크플로우 → v3.6 자동화 → Phase 1.2 Claude Code 통합 → **Phase 2 2모델 역할분담**.

## v3.6 Phase 2 운영 방식 (2026-06-01)

**2모델 역할분담**으로 비용 극소화 + 카드 퀄리티 최상:
- **안티그래비티(Gemini 3.5 Flash)** = 01 OCR + 02-wiki 위키화 — 방대한 원문을 본문 보존 위키로 구조화 (저비용 대용량, 요약 아님)
- **Claude Opus 4.8** = 02-card·06a·06b 카드화 — 구조화된 위키만 입력받아 정교한 Anki 카드 빌드 (최상급 추론)
- 효과: Opus가 PDF 재OCR 없이 구조화 텍스트만 입력 → 입력 비용↓

| 항목 | 운영 |
|---|---|
| 01 OCR·02-wiki | 안티그래비티 앱(데스크톱, Gemini 3.5 Flash)에 `prompts/{단계}_*` 등록, 원문 PDF 직접 첨부 |
| 02-card·06a·06b | Claude Opus 4.8(Claude.ai Project/Code)에 `prompts/{단계}_claude_*.xml` 적용 |
| 입력 전달 | 02-wiki 위키 마크다운 → 02-card 입력 (원문 직접투입 지양 — 비용 논리 유지) |
| 출력 | outputs/{01_ocr, 02_wiki, 02_cards, 06_cases}/ 저장 |
| 검증 | verification_protocol 체크리스트로 자가 검증 후 보고 |

> 참고: 이전 Phase 1.2(Claude Code 단독 직접처리, 외부도구 미사용) 모드도 카드화 단계는 그대로 사용 가능. 차이는 01 OCR·02-wiki를 안티그래비티(외부)로 분리하는 점.

## v3.6 paradigm shift

| 항목 | v3.5.2 | v3.6 |
|---|---|---|
| 파이프라인 | 5단계 (01·02·04·06) | **4단계 (01·02-wiki·02-card·06)** |
| 책 입력 | 마킹 의존 | **책 유형 자동 식별 → 위키 → 카드** |
| 태그 | `유형::조문` 단축 | **`속성::요건`+`주제::채권자취소권` 2축** |
| Obsidian 통합 | 별도 | **위키 마크다운 vault import 가능** |
| 학습 보조 | NotebookLM 소크라테스 | **Anki 카드 메인** (NotebookLM 보조) |

## 0단계 — Claude Code에 알리기 (카드화 단계)

카드화를 Claude Code로 돌릴 경우, 첫 메시지로:

```
SKILL.md 읽고 v3.6 Phase 2 2모델 역할분담 운영 모드 파악해.
prompts/ 폴더 구조와 적용 방법 확인 후 시범 명령 가능 여부 알려줘.
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
| 01번 OCR 단독 | `inputs/raw_pdf/책이름.pdf 01번 OCR만 (Mode B)` |
| 사후 검증 | `검증필요::AI추출 카드 grounding 페이지 정리` |
| 선행 단서 카드 추가 | `02-card 적용할 때 generate_precursor_cards: true 켜줘` |

## 4가지 워크플로우

### A) 단권화 책 전체 자동 (300p 책 1권 → 약 1.5~2시간)

```
입력: inputs/raw_pdf/책이름.pdf (또는 채팅에 직접 첨부)
명령: "책이름.pdf 처리. 단권화"
실행:
  1. (필요시) 사용자가 100p 단위로 사전 분할
  2. 청크별로 Claude Code가 prompts/01_claude_*.md 적용 → OCR
     → outputs/01_ocr/책이름_chunk_NNN.md
  3. 청크별로 prompts/02-wiki_claude_*.xml 적용 → 위키화 ⭐ v3.6 신규
     - 책 유형 자동 식별 (단권화/사례집/판례집/객관식/...)
     - 속성 라벨 자동 (정의/요건/효과/학설/판례/...)
     - Obsidian callout 변환 ([논점정리] → > [!summary])
     - backlink [[쟁점명]] 부착
     → outputs/02_wiki/책이름_chunk_NNN_wiki.md
  4. 위키 출력 → prompts/02-card_claude_*.xml 적용 → 카드화
     - 속성 라벨로 노트 타입 자동 분기 (rule/case_law/mcq)
     - 표 자동 분해
     → outputs/02_cards/책이름_TSV.txt
출력: Anki Import 가능한 TSV + Obsidian vault import 가능한 위키
```

### B) 사례집 풀이 포함 자동 (06b)

```
입력: inputs/cases/사례집이름.pdf
명령: "사례집이름.pdf 06b"
실행:
  1. Claude Code가 prompts/06b_claude_*.xml 적용
  2. 풀이 영역 자동 식별 + 쟁점 추출
  3. 모든 카드에 `검증필요::AI추출` 태그 자동
  → outputs/06_cases/사례집이름_06b_TSV.txt
사후 검증 필수: Anki에서 tag:검증필요::AI추출 검색 → 풀이와 대조
```

### C) 사례집 정밀 (06a)

```
입력: inputs/cases/문제번호.md (case_problem + user_issue_list)
명령: "문제번호.md 06a"
실행: Claude Code가 prompts/06a_claude_*.xml 적용
출력: 검증필요 태그 없음 (사용자가 이미 검증한 쟁점)
```

### D) 02-wiki 단독 (Obsidian vault 위해서)

```
입력: inputs/raw_pdf/책이름.pdf
명령: "책이름.pdf 위키화만"
실행: 01번 OCR (선택) → 02-wiki까지만
출력: outputs/02_wiki/ (Obsidian vault에 그대로 복사 가능)
```

## 폴더 구조

```
claude_code_package_v2/
├── README.md              ← 이 파일
├── SKILL.md               ← Claude Code 자동 읽음
├── INSTRUCTIONS.md        ← 첫 명령 가이드
│
├── prompts/               ← v3.6 Phase 1 프롬프트 12개 (Claude Code가 system context로 흡수)
│   ├── 01_claude_마킹_구조_조문_추출_v3.6.md       ⭐ v3.6 Phase 1.1 신규
│   ├── 01_gemini3.1pro_마킹_구조_조문_추출_v3.6.md  (legacy)
│   ├── 02-wiki_claude_위키화_v3.6.xml              ⭐ 신규
│   ├── 02-wiki_gemini3.1pro_위키화_v3.6.md         (legacy)
│   ├── 02-card_claude_Anki카드화_v3.6.xml
│   ├── 02-card_gemini3.1pro_Anki카드화_v3.6.md     (legacy)
│   ├── 04_notebooklm_소크라테스.md                 (보조용)
│   ├── 05_anki_덱구조_태그_모델라우팅.md
│   ├── 06a_claude_사례집문제_manual_v3.6.xml
│   ├── 06a_gemini3.1pro_사례집문제_manual_v3.6.md  (legacy)
│   ├── 06b_claude_사례집문제_extract_v3.6.xml
│   └── 06b_gemini3.1pro_사례집문제_extract_v3.6.md (legacy)
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
├── [legacy 보존 — Phase 1.2 Claude Code 단독모드 잔재, Phase 2에서도 직접 미사용]
│   ├── .env, .env.example   ← Opus 4.8 모델 지정 (카드화 API 자동화 시)
│   ├── requirements.txt
│   ├── scripts/             ← 외부 API 자동화 (Anthropic API key 필요)
│   └── logs/                ← scripts 실행 로그
│
└── .gitignore
```

## 환경 설정 (Phase 2)

- **01 OCR·02-wiki**: 안티그래비티 앱(데스크톱)에 프롬프트 등록 (앱 계정·설정은 별도 관리)
- **02-card·06a·06b**: Claude.ai Project 또는 Claude Code(구독)에 프롬프트 적용 — API 키 불필요

추후 카드화 단계 외부 API 자동화 사용 시:
1. Anthropic Console에서 API key 발급
2. `.env.example` → `.env`로 복사 후 키 입력 (모델 = claude-opus-4-8)
3. `pip install -r requirements.txt`
4. `python scripts/02_card.py ...` 호출 (01 OCR·02-wiki는 안티그래비티 측 처리)

## 비용 (Phase 2 — 2모델 분담)

- **01 OCR·02-wiki (안티그래비티/Gemini 3.5 Flash)**: 방대한 원문을 저비용 대용량 처리, 본문 보존 위키로 구조화
- **02-card·06a·06b (Claude Opus 4.8)**: 구조화된 위키만 입력 → PDF 재OCR 불필요, 입력 비용↓
- Claude Code 구독으로 카드화 단계를 처리하면 별도 API 비용 없이 usage limit 내 운영 가능
- 비용 절감 효과는 API 종량 과금 기준. 구독 정액제에서는 usage limit 절감으로 환산됨

## 시범 운영 권장 순서 (v3.6 Phase 2)

1. **01번 OCR (안티그래비티)**: 50p 시범 PDF → 마킹·구조 인식 확인
2. **02-wiki (안티그래비티)**: 01번 출력 → 책 유형 추정·속성 라벨·callout 변환·본문 보존율(≥0.90) 확인
3. **02-card (Opus 4.8)**: 위키 출력 → 노트 타입 자동 분기·표 분해 확인
4. **06b (Opus 4.8)**: 사례집 1문제 → 풀이 영역 식별·검증필요 태그 확인
5. **Anki Import 후 hallucination 측정**: 100장당 3장 초과 → 프롬프트 수정 검토
6. **전체 파이프라인 1회 실행**: 형법총론 또는 민법1 책 1권

## 안전망

- Claude Code가 verification_protocol 체크리스트로 자가 검증
- 06b 카드는 `검증필요::AI추출` 태그 자동 부착 — 사후 검증 필수
- 환각·누락 100장당 3장 초과 시 작업 중단 보고
- 한자 병기 금지 (CLAUDE.md #37 준수)
- 모든 출력은 outputs/에 저장 — 사용자 검토 가능

## v3.5.2 → v3.6 마이그레이션

1. v3.5.2 카드 그대로 유지 (보류·검증필요 태그 호환)
2. 새 학습 자료부터 v3.6 파이프라인 사용
3. Anki Browse에서 `tag:유형::*` 검색 → 수동으로 `속성::`+`주제::`로 마이그레이션 (선택)
4. 또는 v3.5.2와 v3.6 카드를 별개 덱(`변시::v35`·`변시::v36`)으로 운영

## 백업

원본 백업: `5.기타/패키지백업/2026-05-21/claude_code_package_v2/` (2026-05-21 보존)

## 문의

자세한 작동 방식은 `SKILL.md`. 명령이 막히면 Claude Code에 `현재 상태 알려줘`.
