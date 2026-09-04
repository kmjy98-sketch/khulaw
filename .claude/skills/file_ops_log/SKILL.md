---
name: file_ops_log
description: '파일·폴더 이동·이름변경·복사·trash 이동 시 경로·해시·사유를 master.{csv,jsonl,md}에 자동 기록(#16-C). 트리거: "이동", "이름변경", "rename", "move", "옮겨", "trash로", "파일 정리"'
---

`E:\법학볼트\.agent\skills\file_ops_log\SKILL.md` 를 읽고 지침을 따른다.

CLAUDE.md #16-C 의무 로그. 이동·이름변경·복사·trash 이동은 `log_file_op.py`로 `.agent/file_ops_log/master.{csv,jsonl,md}`에 1작업=1행 기록. 공유드라이브(`0.공유드라이브/`)는 #16-B로 제외.
