# 백업 플랜 — Claude Code 단독 처리 모드 (안티그래비티 대체)

작성 2026-06-01. 기본 운영(Phase 2)은 안티그래비티(Gemini 3.5 Flash)가 01 OCR·02-wiki를 담당한다.
이 문서는 **안티그래비티를 못 쓰거나 그 출력을 믿을 수 없을 때**, 01·02-wiki까지 Claude Code가 직접 처리하는 백업 모드다.

## 1. 언제 쓰나

- 안티그래비티 앱 사용 불가/오류
- silent drop·과압축 의심으로 Gemini 출력 신뢰 불가 (메모리: Gemini silent-drop 전력)
- 정확도 우선 챕터(변시 핵심) — Claude의 보존·지시준수가 Flash보다 유리할 때

## 2. 무엇이 바뀌나

Phase 2의 01 OCR·02-wiki를 **안티그래비티 대신 Claude Code(이 환경)** 가 수행한다.
02-card·06은 원래 Claude이므로 동일 → **전 파이프라인을 Claude Code 한 곳에서** 처리.

| 단계 | Phase 2 기본 | 백업 모드 |
|---|---|---|
| 01 OCR | 안티그래비티 | **Claude Code** (`prompts/01_claude_*` 적용) |
| 02-wiki | 안티그래비티 | **Claude Code** (`prompts/02-wiki_claude_*` 적용) |
| 02-card·06a·06b | Claude Opus 4.8 | Claude Opus 4.8 (동일) |
| 무결성 검증 | `integrity_check.py` | `integrity_check.py` (동일) |

> 프롬프트는 이미 `*_claude_*` 버전이 존재하고 글자수 무결성 규칙(보존율 ≥ 0.90, 페이지별 글자수)도 반영돼 있다. **추가 제작 불필요** — 적용 대상만 안티그래비티 → Claude Code로 바뀐다.

## 3. 장점 / 한계

**장점**
- Gemini silent-drop 위험 제거 (Claude의 보존·지시준수가 우수)
- 같은 세션에서 여러 청크 연속 처리 (Gemini PDF 다중턴 회귀버그 없음 — `01_claude` chunking_policy 참조)
- 추출 직후 `integrity_check.py`로 보존율 검증 (외부 앱 왕복 없음)
- 입력 격리·한국법학 4축 가드·마크다운 충돌 회피 규칙이 그대로 적용됨

**한계**
- Claude PDF 읽기: 요청당 최대 약 20페이지, 청크 권장 ≤ 100p → 큰 책은 `scripts/pdf_split_100p.py`로 분할
- 손글씨 형광펜 인식은 스캔 품질에 의존 → **Mode B(전체 추출)** 로 누락 위험 최소화
- 토큰·usage limit → 긴 챕터는 청크 단위로. 한도 임박 시 `STOP:` 앵커로 분할 후 다음 청크 재개

## 4. 워크플로우 (단계별)

```
0. (선택) 분할
   python scripts/pdf_split_100p.py <책.pdf>     → 100p 청크

1. 01 OCR  (Claude Code)
   PDF 첨부(또는 inputs/raw_pdf/) → prompts/01_claude_* 규칙 적용
   PDF를 페이지 단위(≤20p/read)로 읽어 Mode B 전체 추출
   → outputs/01_ocr/<책>_chunk_NNN.md
     (anchor + TOTAL_CHARS + 페이지별 글자수 표 포함)

2. 02-wiki  (Claude Code)
   outputs/01_ocr/...md → prompts/02-wiki_claude_* 규칙 적용
   → outputs/02_wiki/<책>_chunk_NNN_wiki.md
     (INTEGRITY anchor + 보존율 포함)

3. 무결성 검증  (필수)
   python scripts/integrity_check.py --report
   → 보존율 < 90% FAIL 행만 재처리

4. 02-card / 06  (Claude Code, 기존과 동일)
   prompts/02-card_claude_* 또는 06{a,b}_claude_*
   → outputs/02_cards/ | outputs/06_cases/

5. Anki Import  (사용자 수동)
```

## 5. 트리거 (제안)

- "백업 모드", "클로드 코드 단독", "안티그래비티 없이 처리" → 이 문서 적용
- CLAUDE.md #17 자동참조 표에 등록하려면 별도 승인 필요 (현재는 이 문서 + SKILL.md 안내로 운영)

## 6. 기본 모드로 복귀

안티그래비티가 다시 가능해지면 01·02-wiki를 안티그래비티로 되돌린다(SKILL.md Phase 2). 02-card·06은 양쪽 모드에서 동일하므로 바꿀 것이 없다.

## 7. 두 모드 한눈에

| 항목 | Phase 2 (기본, 비용↓) | 백업 (Claude Code 단독, 신뢰↑) |
|---|---|---|
| 01·02-wiki 처리 주체 | 안티그래비티(외부) | Claude Code(이 환경) |
| 강점 | 대용량 저비용 | 누락 위험 최소·즉시 검증·연속 처리 |
| 약점 | silent-drop 위험 | usage limit·PDF 페이지 한계 |
| 적합 | 분량 많고 비핵심 | 분량 적고 정확도 핵심 |
