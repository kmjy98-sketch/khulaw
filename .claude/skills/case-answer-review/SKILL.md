---
name: case-answer-review
description: 사례형 답안 채점, 기출 정리, 대비팩 생성. 트리거: "답안 채점", "사례 채점", "내 답안 봐줘", "case review", "답안 평가", "채점해줘"
---

`E:\법학볼트\.agent\skills\case-answer-review\SKILL.md` 를 읽고 지침을 따른다.

참조 워크플로우: `.agent/workflows/case-answer-rag.md`
입력: `problem_index.json`, `alignment.json`, `weak_points`, qmd `law-notes` 검색 결과 (helper: `.agent/lib/qmd_search.py`)
채점 후 취약점은 `learning.json`에 기록한다.
학습 세션(`socratic-loader`)과 분리해서 실행한다. (#35)
배점표 있으면 반영, 없으면 O/△/X. (#25)
IRAC 블록 + 근거 2줄. (#26)

korean-law-mcp 자동 호출:
- 답안 인용 조문의 정확성 검증 시 원문 자동 대조
- 모범답안에 조문 번호만 있으면 원문 자동 조회 삽입
- qmd 검색에 판결요지 없으면 판례 자동 보충
