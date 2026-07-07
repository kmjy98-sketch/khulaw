#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_safety_guard.py — PreToolUse 안전 가드 (warn-only 파일럿)
=========================================================
CLAUDE.md #16/#16-B/#16-C 기계적 보강. Edit/Write/Bash 직전 위험 신호를 '경고만' 한다.
warn-only: 절대 차단하지 않는다(어떤 경우에도 exit 0). enforce 승격은 1주 무오탐 후 별도 결정.
한계: settings.json PreToolUse 훅은 '직접 도구호출'만 포착 — 서브에이전트·MCP 간접호출은 미포착.

입력(stdin): {"tool_name": "...", "tool_input": {...}}
점검: ①0.공유드라이브 쓰기·이동(#16-B 최우선) ②삭제 명령(#16) ③이동이 log_file_op 미경유(#16-C)
"""
import json
import sys

SHARED = "0.공유드라이브"
DELETE_PAT = ("rm ", "rm -", "del ", "rmdir", "Remove-Item", "remove-item")
MOVE_PAT = ("mv ", "move ", "Move-Item", "move-item")


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)  # 파싱 실패해도 차단 금지
    try:
        tool = data.get("tool_name", "")
        ti = data.get("tool_input", {}) or {}
        blob = json.dumps(ti, ensure_ascii=False)
        warns = []

        if SHARED in blob and tool in ("Edit", "Write", "NotebookEdit"):
            warns.append("[#16-B] 0.공유드라이브 쓰기 시도 — 공유 드라이브 이동·쓰기 금지(최우선)")

        if tool == "Bash":
            cmd = str(ti.get("command", ""))
            if any(p in cmd for p in DELETE_PAT):
                warns.append("[#16] 삭제 명령 감지 — 삭제 금지, _trash/_retired 이동으로 대체")
            if any(p in cmd for p in MOVE_PAT) and "log_file_op" not in cmd:
                warns.append("[#16-C] 이동 명령이 log_file_op.py 미경유 — 이동 로그 의무")
            if SHARED in cmd:
                warns.append("[#16-B] 0.공유드라이브 관련 명령 — 쓰기·이동 차단 대상")

        for w in warns:
            sys.stderr.write("safety-guard(warn): " + w + "\n")
    except Exception:
        pass
    sys.exit(0)  # warn-only: 무조건 통과


if __name__ == "__main__":
    main()
