---
name: case-answer-review
description: 사례답안지 채점, 범위 기출 정리, 교재/자료 문제 대비팩 생성이 필요할 때 사용. 현재 과목의 교재 목록, problem_index, alignment, weak_points, RAG 검색 결과를 묶어 사례형 답안의 초벌 평가와 후속 학습 자료를 만든다.
---

# Case Answer Review Skill

사례답안 채점과 대비자료 생성을 위한 통합 스킬이다.

## 목적

- 사례답안 초벌 채점
- 교재/정렬정보 기반 관련 쟁점 파악
- 질문지/모범답안/해설지와 답안의 일치 여부 검토
- 교재 RAG를 통한 모답-해설-교재 연결 검토
- 선택형 문제의 O/X 드릴 전환
- 해당 범위 기출/자료 문제 수집
- 관련 쟁점, 조문, 판례, 설명 정리
- 약점 분석 및 후속 복습 항목 도출

## 기본 원칙

- 근거는 현재 워크스페이스의 교재, 문제 인덱스, 상태 파일, RAG 검색 결과만 사용한다.
- 질문 텍스트나 모범답안이 없으면 채점은 `초벌 평가`로만 표시한다.
- 모범답안이 있어도 해설지나 교재 RAG 근거가 없으면 `교재·해설 검증 보류`로 표시한다.
- 약점은 기존 `learning.json`의 `weak_points`와 새로 발견된 누락 포인트를 함께 본다.
- 현재 민법 학습 진도 파일과 별개로 `case_answer_packet.json`에 패킷을 저장한다.
- `case_material_index.json`이 있으면 lecture 기준으로 질문지/해설지 묶음을 자동 매칭한다.
- 현재 인덱스에서는 직접 O/X 문제만 바로 드릴화할 수 있고, 숫자선지는 `choices`가 저장된 경우에만 선지별 O/X로 변환한다.
- `problem_index.json`의 `problems.textbook`이 채워지면 그 값을 우선 사용하고, 비어 있어도 `textbook_problem_candidates.json`에서 현재 topic과 맞는 교재 문제 후보를 바로 읽어 요약에 포함한다.

## 사용 자료

- `.agent/state/problem_index.json`
- `.agent/state/progress.json`
- `.agent/state/learning.json`
- `.agent/state/alignment.json`
- `.agent/state/curriculum.json`
- `.agent/state/tag_index.json`
- `.agent/state/untyped_files.json`
- `.agent/state/case_material_index.json`
- `.agent/state/textbook_problem_candidates.json`
- `qmd law-notes` 검색 결과

## 빠른 실행

```powershell
python .agent/skills/case-answer-review/scripts/render_case_answer_review.py --subject 민법 --topic 행위능력 --text "답안 본문..." --output "H:\내 드라이브\tmp\case_answer_review.md"
```

```powershell
python .agent/skills/case-answer-review/scripts/render_case_answer_review.py "C:\path\답안.pdf" --subject 민법 --lecture 1 --output "H:\내 드라이브\tmp\case_answer_review.md"
```

```powershell
python .agent/skills/case-answer-review/scripts/render_case_answer_review.py --subject 민법 --topic 행위능력 --text "답안 본문..." --question-text "사례문..." --model-answer-text "모범답안..." --explanation-text "해설지..." --output "H:\내 드라이브\tmp\case_answer_review.md"
```

## 출력물

1. 마크다운 보고서
2. `.agent/state/case_answer_packet.json`
3. 보고서 주요 섹션
   - 관련 쟁점 파악
   - 모범답안/해설지/교재 일치 검토
   - 객관식 문제 O/X 변환
   - 추가 필요사항 조사
4. 진행로그/보조 인덱스
   - `.agent/state/case_material_index.json`
   - `.agent/state/case_material_index_log.json`
   - `.agent/state/textbook_problem_candidates.json`
   - `.agent/state/textbook_problem_scan_log.json`

## 통합 방향

- `problem-index`: 해당 범위 문제와 해설 경로 수집
- `alignment/curriculum`: 교재 페이지 및 개념 범위 연결
- `qmd law-notes`: 관련 설명 청크 검색
- `learning.json`: 기존 약점과 중첩 분석
- `srs_log.json`: 채점이 자동 기록(silent write)하지 않는다. 아래 "약점 연동" 규칙으로 복습 항목을 **제안**하고, 사용자가 채점 확정/복습 등록을 지시할 때만 spaced-repetition 스킬로 기록한다.
- `korean-law-mcp`: 아래 규칙에 따라 자동 호출

### korean-law-mcp 자동 호출

채점·대비자료 생성 중 다음 상황이면 korean-law-mcp MCP 도구를 **자동 호출**한다:

1. **채점 근거 보강**: 답안이 인용한 조문의 정확성을 검증할 때 `get_law_detail`로 원문 대조
2. **모범답안 조문 첨부**: 모범답안/해설에 조문 번호만 있고 원문이 없으면 자동 조회 → 보고서에 원문 인용 삽입
3. **관련 판례 보강**: 쟁점에 판례 근거가 필요한데 `qmd law-notes`에서 판결요지가 나오지 않으면 `search_precedent_tool`로 보충
4. **대비팩 생성**: 관련 쟁점 조문 목록을 조회해 대비팩 하단에 `참조 조문` 섹션 자동 추가

`qmd law-notes` 청크에 이미 조문 원문/판결요지가 포함되어 있으면 중복 조회하지 않는다.

## 채점 방식 — 해설 원문 기준 LLM 비교 (2026-06-23 확정)

채점은 파이썬 키워드/substring 매칭이 아니라 **해설 원문 전체를 기준으로 한 LLM 비교**다.

1. **해설(모범답안) 원문 전체를 제시하고 학생 답안과 대조한다.** 해설을 필드·키워드로 분해하지 않는다. (판례번호·쟁점 문자열 리터럴 매칭 금지 — 학생은 답안에 사건번호를 쓰지 않는다.)
2. **채점관은 LLM(이 스킬)이다.** 쟁점/법리/포섭/결론을 해설 기준으로 의미 비교한다. 아래 루브릭 가중치는 LLM이 적용하는 *관점*이지 스크립트가 계산하는 공식이 아니다.
3. **해설은 절대 기준 — 틀리는 시나리오 없음(#1).** LLM은 해설을 뒤집거나 재가공하지 않는다. 감점·누락 단정에는 해설 발췌+위치를 명시(#3), 해설에 없는 것은 보류(#2).
4. **헌법 예외(후순위 구현, 현재 미적용)**: 헌법은 논리가 타당하면 결론이 해설과 달라도 인정될 수 있어 결론 불일치를 곧 감점으로 보지 않는다. 지금은 보류, 추후 구현.
5. **코드 역할 = 오케스트레이션만**: 문제·해설·답안 로드, LLM 판정 결과를 약점/SRS에 기록(오류유형→초기 due는 spaced-repetition `_srs_review_type`), 복습간격 관리. `render_case_answer_review.py`는 자료 수집·패킷 생성용이며 그 `provisional_grade`(coverage)는 채점 본체가 아니다.

## 패널 채점·집계 (2026-06-23 실증)

단일 채점관의 변동성·누락을 줄이기 위해 **독립 채점관 N명(기본 3)**에게 동일한 `채점관_프롬프트_v1.md` + 해설 + 답안을 병렬 투입한다.

**집계 규칙:**
- **등급 = 다수결.** 갈리면 "검토필요"로 사용자에 표시(자동 확정 금지).
- **약점 = 전원 `누락_약점`의 합집합(중복 제거)** → SRS 등록(`_srs_review_type` 초기 due). 단일 채점관이 놓친 약점을 메운다.
- **개별 채점관 노이즈**(약점 아닌 항목 혼입 등)는 집계 시 필터.

**실증(사례1, 강한 grounding):** 명백 결함 답안 3/3 △ 합의, 경계 답안 3/3 O(법리 △) 합의 — grounded 채점관은 등급에서 잘 안 갈린다. 따라서 패널 주가치는 '불일치 표출'이 아니라 ①합의=신뢰 ②약점 합집합 완전성 ③노이즈 필터. **비용 절감 옵션: 2명 + 불일치 시에만 3번째.** 실사용 시 Workflow(패널 N + 집계).

**Workflow 저장:** `.claude/workflows/case-answer-panel-grade.js` (2026-06-23 검증). 호출 `Workflow({name:"case-answer-panel-grade", args:{과목,문제,해설,답안,배점표}})` — args 미지정 시 사례1 데모. 파이프라인: 채점관 3명 병렬 → JS 집계(등급 다수결·항목별 다수결·불일치 표출) → 집계자 1명(약점 dedup+review_type) → due 매핑(`_srs_review_type` 표) → 복습 등록안. 검증 실행에서 같은 답안이 등급 2:1(O/△)로 갈려 `검토필요=[법리,포섭,등급]` 자동 표출 — 단일 채점관이 놓칠 감점을 패널이 포착.

## 채점 루브릭·약점 연동 (2026-06-16 신설)

> ⚠️ **디프리케이트(2026-06-23)**: 아래 가중 루브릭(쟁점0.25/키워드0.20/…)과 `render_case_answer_review.py`의 `provisional_grade`(coverage)는 **채점 본체가 아니다.** 채점은 위 "해설 원문 기준 LLM 비교"(패널)가 한다. 가중치 표는 **LLM이 참고하는 관점**일 뿐 스크립트 점수가 아니다. `provisional_grade`는 패킷의 coverage 신호로만 잔존(채점 점수로 쓰지 말 것).

출처: `sync/_meta/CODEX_BOOTSTRAP_REPORT.md` §17~19의 채택분. 기존 "초벌 평가"를 고정 루브릭으로 구체화한다.
> ※ 현재 스펙 문서화 단계 — render_case_answer_review.py(provisional_grade는 coverage 기반)에 본 가중치 루브릭·약점 연동이 아직 코드 반영되지 않았다(후속 과제, codex이관_claude환원_검토_2026-06-16.md §5). 채점 시 문서 루브릭은 수동 적용하고 자동 점수는 초벌로 해석한다.

### 채점 루브릭 (가중치)

질문지·모범답안·해설/교재 근거가 있을 때 적용한다. 근거 없으면 항목을 `보류`로 두고 가중에서 제외한다.

| 항목 | 가중 | 기준 |
|---|---:|---|
| 쟁점 발견 | 0.25 | 예상 issue가 답안에 드러나는가 (발견 1.0 / 부분 0.5 / 누락 0.0) |
| 키워드 일치 | 0.20 | required_keywords·동의어 충족도 |
| 구조 일치 | 0.20 | answer_structure 순서·주요 항목 포함 |
| 결론 일치 | 0.15 | conclusion_patterns와 실질 일치 (일치 1.0 / 부분 0.5 / 반대 0.0) |
| 포섭 | 0.20 | 사실↔법리 연결. 사실 없는 법리 진술만이면 최대 0.5, 핵심사실 누락 시 최대 0.6 |

- **배점표가 소스에 있으면 그것을 우선 반영**한다(AGENTS #25-3). 배점표가 없으면 위 가중 대신 항목별 O/△/X만 표기할 수 있다.
- **감점·누락 단정에는 반드시 source(파일·위치)를 남긴다.** source 없는 감점은 하지 않는다(AGENTS #1·#2).
- 소스에서 확인 불가한 법리는 점수화하지 않고 "자료 부족—보류"로 둔다.

### 약점 → 복습 → 카드 연동 규칙

채점 결과로 다음을 **제안**한다(자동 기록 아님. spaced-repetition·카드 생성은 별도 확정 단계):

| 상황 | 조치 |
|---|---|
| 1회성 경미한 누락 | 복습큐 제안만 (카드 생성 안 함) |
| 같은 유형 2회 반복 | Anki 카드 후보 생성/갱신 제안 |
| 결론 오류 | 카드 후보 즉시 생성 제안 (conclusion_pattern) |
| 쟁점 누락(반복) | issue_outline·keyword_recall 후보 제안 |
| 포섭 약점 | application_checkpoint 단기복습 제안 (소스 체크포인트 있을 때만) |
| 자료 부족 | 카드 생성 금지, "자료 부족—보류" |

- 복습간격은 spaced-repetition 스킬의 "답안 채점 연동 간격" 표를 따른다(채점 점수는 본 루브릭의 0.0~1.0 척도이며 그 표의 임계값도 동일 척도로 읽는다).
- 카드 후보는 card-wiki-pipeline §8(note_key·중복방지)을 준수한다 — 같은 note_key 있으면 갱신, 중복 생성 금지.
