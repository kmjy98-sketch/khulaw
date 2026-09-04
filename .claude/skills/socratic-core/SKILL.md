---
name: socratic-core
description: 소크라틱 문답 엔진. 대화/생성/채점 모드, 힌트 시스템, 상태 갱신. socratic-loader 이후에만 사용. 트리거: socratic-loader가 세션 부팅한 후 자동 진입
---

`E:\법학볼트\.agent\skills\socratic-core\SKILL.md` 와 다음 docs를 읽고 지침을 따른다:
- `.agent/skills/socratic-core/docs/dialog.md` — 대화 모드
- `.agent/skills/socratic-core/docs/problem.md` — 문제 생성 모드
- `.agent/skills/socratic-core/docs/grading.md` — 채점 모드
- `.agent/skills/socratic-core/docs/subject-detect.md` — 과목 자동 감지

핵심 원칙:
- 질문/힌트 중: 근거 생략 (학습자 사고 유도)
- 최종 답변(정답 공개) 시에만: 근거 2줄 제공
- Reverse-RAG 채점 적용
- 세션 종료 시 `learning.json`, `progress.json`, `srs_log.json` 자동 갱신

law_api.py(verify-text/verify-article, 법제처 직접 API) 자동 호출:
- 정답 공개/해설 단계에서 조문 번호 등장 시 → 원문 자동 조회 후 인용
- 판례 근거 제시 시 → 판결요지 자동 확인
- 질문/힌트 단계에서는 호출 금지 (학습자 사고 유도 유지)
