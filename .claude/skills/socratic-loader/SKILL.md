---
name: socratic-loader
description: 소크라틱 학습 세션 시작. 상태 파일 로드 + RAG 검색 + 세션 부팅. 반드시 socratic-core 전에 실행. 트리거: "소크라틱", "학습 시작", "문제 풀어줘", "공부 시작", "/socratic"
---

`E:\법학볼트\.agent\skills\socratic-loader\SKILL.md` 를 읽고 지침을 따른다.

**순서 고정**: `socratic-loader` → `socratic-core` (절대 역순 불가)

Phase 0 초기화 순서:
1. `.agent/state/progress.json` — 현재 진도 확인
2. `.agent/state/learning.json` — 취약점 확인
3. `.agent/state/srs_log.json` — 복습 일정 확인
4. `.agent/state/problem_index.json` — 관련 문제 검색
5. qmd `law-notes` — BM25+벡터 검색 (helper `.agent/lib/qmd_search.py`)
6. `law_api.py`(verify-text/verify-article, 법제처 직접 API) — 법령 API 가용 상태 확인 → 세션 배너에 표시
