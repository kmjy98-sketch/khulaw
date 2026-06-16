#!/usr/bin/env python3
"""qmd CLI 래퍼 — 스킬 공통 helper.

사용 예:
    from qmd_search import qmd_search
    hits = qmd_search("통정허위표시", k=5)
    for h in hits:
        print(h["file"], h["score"], h["snippet"])

반환 형식:
    [{"docid": "#xxxxxx",
      "score": 0.81,
      "file": "qmd://law-notes/...",
      "path": "민법/총칙/...",          # qmd:// 제거 + 슬래시 통일
      "title": "...",
      "snippet": "...",
      "context": "..."}, ...]

LanceDB → Obsidian 위키 이전(2026-04-10) 후 socratic-loader, case-answer-review,
law-note-supplement 등이 이 helper 하나로 qmd CLI를 호출하도록 통합.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class QmdSearchError(RuntimeError):
    """qmd 호출 실패."""


_QMD_CMD: list[str] | None = None


def _resolve_qmd() -> list[str]:
    """qmd 실행 명령 리스트 반환.

    Windows에서 .CMD 래퍼를 거치면 한글 인자가 깨지므로, 가능하면 node 스크립트를
    직접 호출. 실패 시 qmd.CMD/qmd 폴백.
    """
    global _QMD_CMD
    if _QMD_CMD:
        return list(_QMD_CMD)
    # 1) node + dist/cli/qmd.js 직접 호출 (Windows .CMD 한글 인자 깨짐 우회)
    npm_js = Path.home() / "AppData" / "Roaming" / "npm" / "node_modules" / "@tobilu" / "qmd" / "dist" / "cli" / "qmd.js"
    if npm_js.exists():
        node = shutil.which("node")
        if node:
            _QMD_CMD = [node, str(npm_js)]
            return list(_QMD_CMD)
    # 2) PATH의 qmd 폴백
    found = shutil.which("qmd")
    if not found:
        raise QmdSearchError(
            "qmd CLI를 찾을 수 없음. `npm i -g @tobilu/qmd` 또는 PATH 확인 필요."
        )
    _QMD_CMD = [found]
    return list(_QMD_CMD)


def _strip_qmd_uri(uri: str) -> str:
    """qmd://collection/path → path 만 반환."""
    m = re.match(r"^qmd://[^/]+/(.+)$", uri)
    return m.group(1) if m else uri


def _run(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise QmdSearchError(f"qmd 실행 실패: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        raise QmdSearchError(
            f"qmd 명령 실패 (exit={exc.returncode}): {exc.stderr.strip() or exc.stdout.strip()}"
        ) from exc
    return proc.stdout


def qmd_search(query: str, *, k: int = 5, mode: str = "search") -> list[dict[str, Any]]:
    """qmd CLI로 검색.

    Args:
        query: 검색 질의 (한국어 가능).
        k: 상위 결과 수.
        mode: "search" (BM25, 빠름), "vsearch" (vector), "query" (BM25+vec+LLM rerank, 느림).

    Returns:
        qmd JSON 결과 + path 필드 추가. 실패 시 빈 리스트.
    """
    if mode not in {"search", "vsearch", "query"}:
        raise ValueError(f"unknown mode: {mode}")
    base = _resolve_qmd()
    cmd = base + [mode, query, "-k", str(k), "--json"]
    raw = _run(cmd)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QmdSearchError(f"qmd JSON 파싱 실패: {exc}\n--- raw ---\n{raw[:500]}") from exc
    if not isinstance(data, list):
        return []
    for item in data:
        item["path"] = _strip_qmd_uri(item.get("file", ""))
    return data


def qmd_get(file_path: str, *, line: int | None = None, length: int | None = None) -> str:
    """qmd get으로 단일 문서 본문 반환.

    Args:
        file_path: 'collection/path/file.md' 또는 'qmd://...' 또는 절대 경로.
        line: 특정 줄 (1-indexed).
        length: line 부터 N줄.
    """
    base = _resolve_qmd()
    target = file_path
    if line is not None:
        target = f"{file_path}:{line}"
    cmd = base + ["get", target]
    if length is not None:
        cmd.extend(["-l", str(length)])
    return _run(cmd)


def qmd_status() -> dict[str, Any]:
    """qmd status 결과(텍스트). 단순 health check 용도."""
    base = _resolve_qmd()
    out = _run(base + ["status"])
    return {"raw": out}


def _self_test() -> int:
    """python qmd_search.py [query] — 간단 동작 확인."""
    q = sys.argv[1] if len(sys.argv) > 1 else "통정허위표시"
    hits = qmd_search(q, k=3)
    print(f"=== qmd_search('{q}', k=3) → {len(hits)}개 ===")
    for i, h in enumerate(hits, 1):
        print(f"\n[{i}] score={h.get('score')} {h.get('path')}")
        print(f"    title: {h.get('title')}")
        snippet = (h.get("snippet") or "").splitlines()
        if snippet:
            print(f"    snippet: {snippet[0][:120]}")
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(_self_test())
