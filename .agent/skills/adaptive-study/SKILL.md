---
name: adaptive-study
description: 적응형 학습 루프(쟁점 그래프 + 전파 활성화 + cutoff 공부권고). "적응 학습", "약점 강화 풀기", "약점보드", "쟁점 그래프" 요청 시 사용. SRS 리스트만 주는 대신 문제를 출제하고, 틀리면 약한 연관쟁점을 강화 출제, 일정 횟수 넘으면 교재 학습을 권고한다.
---

# Adaptive Study Loop

> 신규 2026-06-23. SRS·패널이 "리스트"만 주던 한계를 보완 — 쟁점 그래프 위에서 문제를 출제하고, 오답 시 약한 연관쟁점을 강화하며, 반복 실패는 "공부하라"로 escalate.
> 우선순위: 루트 `CLAUDE.md`(정본) > `card-wiki-pipeline.md` > 본 SKILL. AGENTS.md = 비클로드 에이전트용 운영 기준(참고) — 충돌 시 CLAUDE.md 우선.

## 0. 모델
쟁점 그래프 위의 **전파 활성화(spreading activation)** — 가중 그래프 + 노드 강도 + 헤비안식 강화. 진짜 NN 아님.

## 1. 부품 (현재 `.agent/scripts/`, 로컬 이관은 후속 — #16-C 로그 제약)

| 부품 | 파일 | 역할 |
|---|---|---|
| 엔진 | `_study_engine.py` | 선택→전파활성화→cutoff→baseline. `StudyEngine`, `grade_objective`(OX/Cloze 정확매칭) |
| 그래프 생성기 | `_issue_graph_build.py` | 5신호 병합·정규화 + **과목 분리(#35)**. `build_graph`, `to_engine_edges/sources` |
| 어댑터 | `_study_session_runner.py` | 엔진↔provider(전달)/panel(사례채점)/SRS제안. `SessionRunner`, `Problem` |
| 강화학습 | `_reinforce_learn.py` | co-failure 엣지 강화(학습자 혼동 클러스터). `accumulate_cofail`, `reinforce_edges` |
| 약점보드 | `_weakness_board.py` | 옵시디언 대시보드. `build_board` |
| (연동) | `spaced-repetition/_srs_review_type.py` | 오류유형→초기 due |

## 2. 루프
```
그래프(5신호+과목분리) → [+co-fail 강화] → StudyEngine
loop: next_problem(쟁점) → provider 출제 → 채점(OX/Cloze=정확매칭, 사례=case-answer-panel-grade)
      → 맞음: 강도↑·마스터  /  틀림: 약한 연관쟁점 강화 + 본인 재드릴
      → fails≥cutoff: "이 파트 공부하라"(교재 위치) + 드릴 중단
finish(): 공부권고 + SRS제안(silent write 금지 #16) → 약점보드
```

## 3. 핵심 규칙
- **과목 분리(#35)**: 민/형/공 교차 엣지·강화 금지(같은 판례 인용해도). 키워드 동음 오연결 차단.
- **채점 분기**: OX/Cloze=`grade_objective`(정확매칭), 사례=`case-answer-panel-grade` 워크플로(해설 절대 #1).
- **silent write 금지(#16)**: finish()는 SRS *제안*까지만. 기록은 사용자 확정 시 spaced-repetition로.
- **cutoff escalate**: 무한 드릴 금지 — 반복 실패는 교재 학습 권고로 전환(토끼굴 차단).
- **백링크(#35)**: 약점보드 표 셀 [[]] 금지, 콜아웃·리스트 허용.

## 4. 실연동 (로컬)
- provider ← `socratic-core`(problem_index 매칭/생성)
- panel ← `case-answer-panel-grade` 워크플로
- 강도/이력 ← `learning.json`/`srs_log`(갱신은 사용자 확정)
- 실 그래프 ← `discover_related_issues`(render_case_answer_review.py)+`crossref_all_subjects.py`+`연계::`+wiki 백링크+problem_index 공출현
- 공부권고 위치 ← wiki 쟁점 아티클 / `alignment`

## 5. 상태
파일럿(합성 검증) 완료 — 테스트: 엔진 6 / 그래프 9 / 강화 5 / 보드 6. **데모 작동 실증**(전체 루프: 출제→채점→강화→cutoff→마스터; 윈도우 cp949 콘솔 출력가드 추가 2026-06-25).
**① 실연동 글루 스펙**(provider/panel/state/graph 바인딩) = `9.작업중/클로드/적응형학습_실연동_글루스펙_2026-06-25.md`. 실연동은 런타임 산출물(problem_index·learning.json·실그래프) 채워진 후.
설계·검증 경위: `9.작업중/클로드/옵시디언_안키_통합_검토_핸드오프_2026-06-23.md` §9.
