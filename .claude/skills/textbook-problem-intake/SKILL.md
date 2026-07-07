---
name: textbook-problem-intake
description: 교재 PDF에서 문제 후보를 스캔하고 problem_index에 등록하는 intake 파이프라인. 트리거: "교재 문제 등록", "문제 스캔", "intake", "교재 투입", "textbook intake"
---

`E:\법학볼트\.agent\skills\textbook-problem-intake\SKILL.md` 를 읽고 지침을 따른다.

실행 순서: `pdf-ingest` → `run_textbook_intake.py` → `scan` → `register (dry-run/apply)`
파이프라인 로그: `.agent/state/textbook_problem_pipeline_log.json`
