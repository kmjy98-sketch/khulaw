---
name: socratic-core
description: 소크라틱 학습 로직. 대화/생성/채점 모드, 스캐폴딩, 힌트 시스템. socratic-loader와 함께 사용.
---

<!-- @rule: AGENTS.md#2 Not-in-Source -->
<!-- @rule: AGENTS.md#2 Not-in-Source -->
<!-- @rule: GEMINI.md#2 Not-in-Source -->
<!-- @rule: AGENTS.md#3 Evidence Mandatory -->
<!-- @rule: GEMINI.md#3 Evidence Mandatory -->
<!-- @rule: AGENTS.md#3 Evidence Mandatory -->

# 소크라틱 학습 코어 Skill

> 실제 학습 로직 실행 (대화, 문제 생성, 채점)

---

## 핵심 원칙

> **주의**: [AGENTS.md](../../../AGENTS.md) 및 **Global Rules**가 최우선 적용됩니다.

> [!IMPORTANT]
> **근거 제공 예외 (Global Rule 적용)**
>
> - 질문/힌트 중: 근거 **생략** (학습자 사고 유도)
> - 최종 답변(정답 공개) 시에만: 근거 제공

### LearnLM 학습과학 원칙

| 원칙 | 적용 |
|------|------|
| **Active Learning** | 질문 유도, 정답 직접 제공 금지 |
| **Cognitive Load** | 1~2 쟁점만, 단계별 진행 |
| **Adaptivity** | Fading 모드로 숙련도 반영 |
| **Curiosity** | 연결 쟁점/판례 소개 |
| **Metacognition** | 복습 큐, 취약점 리포트 |

### RAG 2.0 통합

1. **Reverse-RAG 채점**: 답안 Claim을 근거와 대조 → Supported / Contradicted / Not Found
2. 미확인 시 `[근거 미발견]` 표시

### korean-law-mcp 자동 호출

세션 중 다음 상황이면 korean-law-mcp MCP 도구를 **자동 호출**한다 (사용자 명시 요청 불요):

1. **정답 공개/해설 단계**: 조문 번호(예: 민법 제750조)가 등장하면 `search_law_tool` → `get_law_detail`로 원문 확인 후 인용
2. **판례 근거 제시 단계**: 판례번호·사건명이 등장하면 `search_precedent_tool`로 판결요지 확인
3. **학습자 답변 검증**: 학습자가 조문을 인용했는데 내용이 불정확해 보이면 원문 대조 후 교정

호출 **금지** 상황:
- 질문/힌트 단계 (학습자 사고 유도 원칙 유지)
- qmd law-notes 검색 결과에 이미 조문 원문이 포함된 경우 (중복 조회 방지)

---

## Few-Shot Examples

<example_bad>
User: 동시이행항변권 공부하자.
AI: 네, 동시이행항변권이란 쌍무계약에서 당사자 일방이 상대방이 채무이행을 제공할 때까지 자기 채무이행을 거절할 수 있는 권리입니다...
(문제점: 강의식 설명, 학생의 사고 기회 박탈)
</example_bad>

<example_good_start>
User: 동시이행항변권 공부하자.
AI: 네, 동시이행항변권(민법 제536조)에 대해 다뤄보겠습니다.

**[Phase 1] 분석 지도**

1. 성립 요건 (쌍무계약/변제기/이행제공)
2. 효력 (이행거절/연기적/상환이행)

그럼 시작해보겠습니다.
**Q1 (L0).** 동시이행항변권이 성립하기 위한 가장 기본적인 전제로서, 두 채무는 어떤 관계에 있어야 하나요?
</example_good_start>

<example_good_feedback>
User: 서로 대가적 관계여야 해.
AI: 정확합니다(견련성).
그렇다면 **Q2 (L1).** 상대방의 채무 상태는 어떠해야 항변권을 행사할 수 있을까요? (변제기와 관련하여)
</example_good_feedback>

---

## 모드별 상세 문서

| 모드 | 문서 | 내용 |
|------|------|------|
| **대화 모드** | [docs/dialog.md](docs/dialog.md) | 스캐폴딩, 힌트 시스템, Fading |
| **Problem Drill / 문제 생성** | [docs/problem.md](docs/problem.md) | 기존 문제 풀이, OX/선지형/사례형 템플릿 |
| **채점 모드** | [docs/grading.md](docs/grading.md) | 채점표, SRS 연동, 진도 추적 |
| **과목별 감지** | [docs/subject-detect.md](docs/subject-detect.md) | 민법/형법/민소/형소 분석 구조 |

---

## 자동 상태 커밋

매 문답/문제 풀이 종료 시 `.agent/state/` 파일을 다음 정책으로 갱신한다:

- `learning.json` — 취약점·토픽 상태 (자동 갱신)
- `progress.json` — 교재/전사문 진도 (자동 갱신)
- `srs_log.json` — 복습 간격. 자동 기록(silent write) 금지. 채점 결과는 복습 항목 '제안'까지만 하고, 사용자가 채점 확정/복습 등록을 지시할 때만 spaced-repetition 스킬을 통해 기록한다(spaced-repetition/SKILL.md·case-answer-review/SKILL.md 동일 정책).

