#!/usr/bin/env python3
"""
korean-law MCP 등록 python 교체 패치 (일회성).

목적:
    ~/.claude.json 의 mcpServers."korean-law".command 가 손상된 Store python
    (WindowsApps\\PythonSoftwareFoundation.Python.3.13...\\python.exe) 을 가리켜
    서버가 기동되지 않는 문제를 정상 python.org 인터프리터로 교체한다.

중요:
    Claude Code 가 ~/.claude.json 을 종료 시 통째로 덮어쓰므로,
    반드시 Claude Code 를 "완전히 종료한 상태"에서 실행할 것.
    실행 중에 패치하면 종료 시 옛 설정으로 복구되어 무효가 된다.

실행:
    "C:\\Users\\111\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" \
        ".agent/scripts/_fix_korean_law_mcp_python.py"
"""
import json
import os
import shutil
import sys
from datetime import datetime

CONFIG = os.path.expanduser("~/.claude.json")
GOOD_PY = r"C:\Users\111\AppData\Local\Programs\Python\Python313\python.exe"
SERVER = "korean-law"


def main():
    if not os.path.exists(CONFIG):
        print(f"[중단] 설정 파일 없음: {CONFIG}")
        return 1
    if not os.path.exists(GOOD_PY):
        print(f"[중단] 정상 python 경로 없음: {GOOD_PY}")
        return 2

    with open(CONFIG, "r", encoding="utf-8") as f:
        data = json.load(f)

    servers = data.get("mcpServers", {})
    srv = servers.get(SERVER)
    if not isinstance(srv, dict):
        print(f"[중단] mcpServers.{SERVER} 등록을 찾지 못함")
        return 3

    old = srv.get("command", "")
    print(f"[현재] command = {old}")

    if old == GOOD_PY:
        print("[변경 없음] 이미 정상 python 으로 설정되어 있음")
        return 0

    backup = CONFIG + ".bak-korean-law-" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(CONFIG, backup)
    print(f"[백업] {backup}")

    srv["command"] = GOOD_PY
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[변경] command = {GOOD_PY}")
    print("[완료] Claude Code 를 다시 시작하면 korean-law MCP 가 기동됩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
