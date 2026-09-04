---
name: legal-review
description: 계약서·NDA 조항별 GREEN/YELLOW/RED 검토, redline 제안, fallback 포지션, business impact 분석. 트리거: "계약 검토", "NDA 검토", "계약서 리뷰", "조항 분석", "legal review", "계약 분석"
---

`E:\법학볼트\.agent\skills\legal-review\SKILL.md` 를 읽고 지침을 따른다.

플레이북: `.agent/state/legal_playbook.md`
실행: `python .agent/skills/legal-review/scripts/render_review.py "<파일경로>" --mode contract-review`
전체 suite 드라이런: `python .agent/skills/legal-review/scripts/run_legal_suite.py --preset vendor-saas --text "<텍스트>"`

검토 후 조문 원문 필요 시 → `law_api.py`(verify-text/verify-article, 법제처 직접 API)
RAG 선례 검색 → qmd `law-notes` (`.agent/lib/qmd_search.py`)
외부 커넥터 연결 시 → `legal:review-contract` 플러그인 병행
