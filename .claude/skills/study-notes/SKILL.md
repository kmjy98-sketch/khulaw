---
name: study-notes
description: 전사문/교재/기출 기반 학습 노트 자동 생성·정리. 트리거: "노트 정리", "요약", "정리해줘", "학습 노트", "study notes", "노트 만들어"
---

`E:\법학볼트\.agent\skills\study-notes\SKILL.md` 를 읽고 지침을 따른다.

워크플로우 참조: `.agent/workflows/lecture-notes.md`
소스 우선순위: 사례형 교재 > 사례형 자료 > 선택형 자료 > 정리 자료 (#27)

law_api.py(verify-text/verify-article, 법제처 직접 API) 자동 호출:
- 조문 번호 언급 시 원문 없으면 자동 조회 삽입
- 판례 판결요지 없으면 자동 보충
- qmd `law-notes` 검색 결과 우선, 없을 때만 law_api.py 호출

노트 생성 후 보완 필요 시: `law-note-supplement` 스킬로 전환 (augment/review/restructure)
