---
name: weekly-review
description: 주간 학습 리뷰 — 드릴·SRS·사례 결과 집계 + 약점 종합 + 시험일 역산 페이싱 + 다음주 과목별 3토픽. 트리거: "주간리뷰", "주간 회고", "이번주 정리", "이번주 복습 점검", "weekly review", "이번주 어땠어", 토요일 학습 마감.
---

`E:\법학볼트\.agent\skills\weekly-review\SKILL.md` 를 읽고 지침을 따른다.

집계 상태파일: `.agent/state/drill_log.jsonl`, `srs_log.json`, `learning.json`, `progress.json`, `goals.json`.
코드는 상태 집계만, 판단·계획은 LLM. 자동 상태쓰기 금지(#16, 사용자 확정 시만 갱신).
