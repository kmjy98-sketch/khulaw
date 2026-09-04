---
name: dispatch
description: 자연어 작업 단일 진입점. 작업을 분류 → LLM(판단)/코드(결정적) 자동 분배 → 실행 → 결과 보고. 트리거 "이거 처리해줘", "알아서 해줘", "뭐부터 할까", "/dispatch", "/do", 그리고 대상이 애매한 포괄 작업 발화.
---

# Dispatch — 작업 라우터 (단일 진입점)

> 목적: "작업 하나 던지면 알아서 분류·분배·실행·보고". 수동 트리거 부담을 줄인다.
> 상위룰: **#45-B(에이전트-기본·결정적-코어)**, #16/#16-B/#16-C(파일안전), #21(소크라틱 우선), #17(파일럿 후 전체). 충돌 시 이들이 dispatch보다 우선.

## 0. 작동 원리 (#45-B)
- **에이전트가 결정 → 코드가 실행·로그 → 에이전트가 검수.**
- 판단(분류·채점·합성·계획)=에이전트. 결정적·무결성·고빈도(sha256·apkg·정규식배치·JSON상태·파일이동)=코드.
- 내용 의존 판단은 메타데이터로 끝내지 말고 **내용을 읽는다**(NL).

## 1. 분류 의사결정 순서
1. **기존 스킬 트리거 정확매칭** → 즉시 그 스킬로 위임(dispatch는 *애매할 때만* 개입).
2. routes 표(아래) 신호 매칭 → 최상위. 동점이면 1줄 확인.
3. **불명확하면 묻는다(#2 추측 금지)** — 후보 2~3개 제시 후 선택. 위험작업(이동·대량생성·OCR apply) 자동발동 금지.
4. **가드**: 대상이 `0.공유드라이브/`면 쓰기·이동 전면 차단(#16-B 최우선).
5. 학습 질문(개념·풀이)은 #21 소크라틱이 dispatch보다 우선.

## 2. 라우팅 표 (작업유형 → 핸들러·재사용)
| 작업유형 | 신호 | 핸들러 | 호출(재사용) | 결정적 단계 | 확인 |
|---|---|---|---|---|---|
| 일일 드릴 | "오늘 공부/문제/드릴/복습" | hybrid | daily-drill | build_session.py → 출제(LLM) → log_result.py | no |
| 주간 리뷰 | "주간리뷰/이번주 정리" | LLM+집계 | weekly-review | 상태 집계(코드) → 계획(LLM) | no |
| 사례 채점 | "올렸어/업로드함/사례 채점" | hybrid | case-answer-review | render_case_answer_review.py(수집·초벌) → LLM 채점 | no |
| 진도 조회 | "어디까지/진도/현황" | python+LLM | progress-tracker | progress.json(보조 snapshot) read → LLM 요약, 정밀진도=논점 frontmatter(#19-B 정본) | no |
| 책 카드화 | "카드화/단권화" | hybrid-fanout | card-wiki-pipeline | 위키화(LLM) → build_v37_apkg.py(genanki) | yes |
| 위키 아티클 | "쟁점 아티클/위키화" | LLM-fanout | card-wiki-pipeline | (순수 LLM) → _index 갱신 | no |
| OCR 교정 | "OCR 교정/corrections" | python-chain | #13 (LlamaParse 로컬→교정→apply) | haiku/sonnet/apply_corrections.py | yes(apply) |
| 파일 정리/이동 | "분류/정리/이동/move" | python-mandatory | file-classification + file_ops_log | log_file_op.py --execute(sha256·#16-C) | yes |
| 메모리 정비 | "메모리 정비/lint/컴파일" | hybrid | memory-maintenance | lint.py 전수점검(활성) · consolidate-memory · flush/compile=동결 | no |
| 학습 질문 | "왜/이해하고 싶어/설명" | LLM | socratic-loader→core | (순수 LLM, #21 우선) | no |

**검증(checker) 축 — 산출 직후(#45-C 자기정합·#49):** 카드화·노트보강·OCR·채점 = `law_api.py verify-text` 대조 + C1~C6 ON · 진도조회·메모리정비·대화성 = OFF(과잉방지). 검증자=Explore(읽기전용)·보류/보고만(자동수정 금지). 불일치 → `.agent/state/consistency_log.jsonl`.

## 3. 분배 규칙
- **생성 목적지(생성시 분류)**: 산출물(노트·카드·OCR·찌라시·문서)은 작성 직전 `resolve_output_path.py`로 목적지 확정(미매칭=사람 확인 1회). 사후 이동 0건화로 #16-C 부담↓(#42). ※ 스킬 전면 배선은 1책 dry-run 통과 후.
- `LLM`: 직접 처리(스크립트 없음).
- `python*`: 해당 스크립트 그대로 호출(인자만). 파일이동은 **무조건** log_file_op.py 경유(#16-C).
- `hybrid`: 결정적(상태·렌더·빌드)=코드, 판단(출제·채점·계획)=LLM. routes 순서 고정.
- `*-fanout`: 독립 단위(챕터·쟁점)는 **포그라운드 병렬** 서브에이전트(백그라운드 장시간은 죽으므로 금지). 공유파일(_index.md·master.*·apkg)은 직렬 강제, fan-out 산출은 메인이 모아 1회 반영.

## 4. 보고 형식
`[라우트: X | 핸들러: Y | 단계: a✓→b✓ | 상태파일: 갱신목록]` + 1줄 요약.

## 5. 파일럿 게이트(#17)
대량 병렬(카드 전량·룰 변경) 전 **1청크 파일럿**(앞/뒤/빈칸 확인) → 통과 시에만 전체 fan-out. 파일럿 없이 전량 금지.
