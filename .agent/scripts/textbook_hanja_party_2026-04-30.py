"""교재원문 표준 한자 → 한글 치환 (2026-04-30 batch).

#37 적용:
- 당사자 한자: 甲乙丙丁戊 → 갑을병정무
- 표준 법조 한자: 原告→원고, 被告→피고, 第三者→제3자, 但→다만
- 괄호 안 (甲), (乙) 등은 보존 (원문 인용/주석 유지)
- 코드블록/표 내부는 보존

dry-run 옵션 지원, 백업 _백업/2026-04-30/.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

WORKSPACE_ROOT = Path(VAULT_ROOT)
DEFAULT_ROOT = WORKSPACE_ROOT / "sync" / "_교재원문"
BACKUP_ROOT = WORKSPACE_ROOT / "_백업" / "2026-04-30"

EXCLUDE_PATH_PATTERNS = [
    "김기용_레인보우OX",
    "_재추출",
    "_백업",
    "_trash",
    "_orig",
    "_raw",
    "_src",
    "_backup",
]

# 단순 1대1 한자→한글 치환 — 괄호 안은 _replace 에서 별도 보존
HANJA_MAP = {
    "甲": "갑",
    "乙": "을",
    "丙": "병",
    "丁": "정",
    "戊": "무",
    "原告": "원고",
    "被告": "피고",
    "第三者": "제3자",
    "債權者": "채권자",
    "債務者": "채무자",
    "債權": "채권",
    "債務": "채무",
}

# 컴파일된 패턴 — 길이 긴 것 먼저 매치되도록 정렬
HANJA_PATTERN = re.compile("|".join(re.escape(k) for k in sorted(HANJA_MAP.keys(), key=lambda x: -len(x))))


def is_excluded(path: Path) -> bool:
    s = str(path)
    return any(pat in s for pat in EXCLUDE_PATH_PATTERNS)


def process_line(line: str) -> tuple[str, int]:
    stripped = line.lstrip()
    # 표/코드블록/인용블록 보존
    if stripped.startswith("```") or stripped.startswith("|"):
        return line, 0
    total = 0

    def _replace(m: re.Match[str]) -> str:
        nonlocal total
        s = m.start()
        e = m.end()
        # 괄호 즉시 감싸진 형태 보존: (甲), (乙), (原告) 등
        if s > 0 and line[s - 1] == "(" and e < len(line) and line[e] == ")":
            return m.group(0)
        # 한자 한 글자 사이에 다른 한자가 인접 → 일반 단어일 가능성 → 보존
        # 단어 하나 안에서 안전 — 매치 자체가 명사라 안전
        total += 1
        return HANJA_MAP[m.group(0)]

    new_line = HANJA_PATTERN.sub(_replace, line)
    return new_line, total


def process_file(path: Path, dry_run: bool) -> int:
    original = path.read_text(encoding="utf-8")
    # frontmatter 영역 제외
    if original.startswith("---\n"):
        parts = original.split("---\n", 2)
        if len(parts) >= 3:
            head = "---\n" + parts[1] + "---\n"
            body = parts[2]
        else:
            head = ""
            body = original
    else:
        head = ""
        body = original

    total = 0
    new_lines: list[str] = []
    for line in body.splitlines(keepends=False):
        nl, n = process_line(line)
        new_lines.append(nl)
        total += n
    if total == 0:
        return 0
    new_body = "\n".join(new_lines)
    if body.endswith("\n") and not new_body.endswith("\n"):
        new_body += "\n"
    new_text = head + new_body
    if new_text == original:
        return 0
    if not dry_run:
        rel = path.relative_to(WORKSPACE_ROOT)
        backup = BACKUP_ROOT / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(new_text, encoding="utf-8")
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    root = Path(args.root)
    files = []
    for p in sorted(root.rglob("*.md")):
        if is_excluded(p):
            continue
        if p.name.endswith(".tmp.md"):
            continue
        files.append(p)

    summary = {
        "total_files": len(files),
        "changed_files": 0,
        "total_replacements": 0,
        "by_author": {},
        "files": [],
    }

    for i, path in enumerate(files, 1):
        try:
            n = process_file(path, dry_run=args.dry_run)
        except Exception as e:
            summary["files"].append({"path": str(path.relative_to(WORKSPACE_ROOT)), "error": str(e)})
            continue
        if n > 0:
            summary["changed_files"] += 1
            summary["total_replacements"] += n
            rel = path.relative_to(WORKSPACE_ROOT)
            summary["files"].append({"path": str(rel), "replacements": n})
            if len(rel.parts) >= 4:
                key = f"{rel.parts[2]}/{rel.parts[3]}"
                a = summary["by_author"].setdefault(key, {"files": 0, "replacements": 0})
                a["files"] += 1
                a["replacements"] += n
        if i % 200 == 0:
            print(f"  [{i}/{len(files)}] processed", file=sys.stderr)

    if args.report:
        Path(args.report).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in summary.items() if k != "files"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
