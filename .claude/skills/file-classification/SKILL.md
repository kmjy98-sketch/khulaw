---
name: file-classification
description: 파일 분류, 이름 변경, 미분류 파일 정리 요청 시 사용. 트리거: "분류", "정리", "이름 변경", "파일 정리", "classify", "rename files"
---

`E:\법학볼트\.agent\skills\file-classification\SKILL.md` 를 읽고 지침을 따른다.

분류 규칙은 `.agent/workflows/classification-rules_v2.md` 기준이다. 작업 전 반드시 현재 파일 상태를 확인한다(Verify-Before-Act). 삭제 금지 — 불필요 파일은 루트 `_trash/{YYYY-MM-DD}/` 로 이동 (2026-06-11 단일화, CLAUDE.md #16).
