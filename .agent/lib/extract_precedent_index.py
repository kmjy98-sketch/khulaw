"""판례 식별자(사건번호) 추출 — sync/ 볼트 전수 스캔.

스캔 대상: sync/_교재원문/**/*.md 및 sync/{민법,형법,헌법,국제법,선택법}/**/*.md
추출 패턴:
 - 일반법원: YYYY(다|도|두|누|후|므|스|재|초|카|가단|가합|나|라) + 숫자
 - 헌법재판소: YYYY(헌가|헌나|헌마|헌바|헌사|헌아) + 숫자
 - 전합(전원합의체) 표기 허용

출력:
 - .agent/state/precedent_frequency.json : {판례ID: {count, files:[...]}}
 - .agent/state/precedent_frequency.md   : 상위 빈출 리스트 요약
"""
from __future__ import annotations
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


VAULT = Path(r"H:\내 드라이브\sync")
STATE = Path(r"H:\내 드라이브\.agent\state")

CASE_PATTERNS = [
    # 대법원·하급심·헌재 사건번호. 연도는 1900~2099 사이로 제한.
    re.compile(
        r"(?<![0-9A-Za-z])"
        r"(?P<year>19\d{2}|20\d{2})\s*"
        r"(?P<kind>"
        r"헌가|헌나|헌마|헌바|헌사|헌아"
        r"|다|도|두|누|후|므|스|재|초|카|나"
        r"|가단|가합|고단|고합|노|구|추"
        r")"
        r"(?P<num>\d{1,6})"
        r"(?![0-9])"
    ),
]


def iter_md_files() -> list[Path]:
    files: list[Path] = []
    files.extend(VAULT.glob("_교재원문/**/*.md"))
    for domain in ("민법", "형법", "헌법", "국제법", "선택법"):
        files.extend((VAULT / domain).glob("**/*.md") if (VAULT / domain).exists() else [])
    return files


def extract_cases(text: str) -> list[str]:
    hits: list[str] = []
    for pat in CASE_PATTERNS:
        for m in pat.finditer(text):
            cid = f"{m.group('year')}{m.group('kind')}{m.group('num')}"
            hits.append(cid)
    return hits


def main() -> int:
    index: dict[str, dict] = defaultdict(lambda: {"count": 0, "files": set()})
    files = iter_md_files()
    print(f"[scan] {len(files)} markdown files", file=sys.stderr)
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            print(f"[err] {f}: {e}", file=sys.stderr)
            continue
        for cid in extract_cases(text):
            entry = index[cid]
            entry["count"] += 1
            entry["files"].add(str(f.relative_to(VAULT)))

    # serialize
    out_json = {
        cid: {"count": v["count"], "files": sorted(v["files"])}
        for cid, v in index.items()
    }
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "precedent_frequency.json").write_text(
        json.dumps(out_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # markdown summary — top 100
    top = sorted(out_json.items(), key=lambda kv: (-kv[1]["count"], kv[0]))
    lines = [
        "# 판례 빈도 인덱스",
        "",
        f"- 스캔 파일 수: {len(files)}",
        f"- 고유 판례 수: {len(out_json)}",
        f"- 총 출현 수: {sum(v['count'] for v in out_json.values())}",
        "",
        "## 상위 100건",
        "",
        "| 순위 | 사건번호 | 출현수 | 파일수 |",
        "|---:|---|---:|---:|",
    ]
    for i, (cid, v) in enumerate(top[:100], 1):
        lines.append(f"| {i} | {cid} | {v['count']} | {len(v['files'])} |")
    (STATE / "precedent_frequency.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"[done] unique={len(out_json)} total={sum(v['count'] for v in out_json.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
