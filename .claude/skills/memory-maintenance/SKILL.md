---
name: memory-maintenance
description: '메모리·정합성 정기 정비 단일 진입점(#41): lint.py 전수 정합점검 + consolidate-memory + 포인터 무결성. 트리거: "메모리 정비", "lint", "메모리 컴파일", "메모리 점검", "memory maintenance"'
---

`E:\법학볼트\.agent\skills\memory-maintenance\SKILL.md` 를 읽고 지침을 따른다.

CLAUDE.md #41 진입점. lint/consolidate/포인터점검을 하나로 묶는다. flush.py·compile.py는 동결 — 호출 금지. 삭제 금지(#16), 이동은 사용자 승인 + log_file_op.py(#16-C).
