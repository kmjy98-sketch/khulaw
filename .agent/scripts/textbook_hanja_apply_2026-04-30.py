"""교재원문 한자→한글 치환 적용 (2026-04-30 batch).

기존 .agent/scripts/fix_ocr_hanja.py 의 RULES/process_line 을 재사용하되:
- 백업 경로를 _백업/2026-04-30/{원본 상대경로} 로 통일
- 김기용_레인보우OX, _재추출, _백업, _trash 제외

dry-run 옵션 지원.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

WORKSPACE_ROOT = Path(VAULT_ROOT)
DEFAULT_ROOT = WORKSPACE_ROOT / "sync" / "_교재원문"
BACKUP_ROOT = WORKSPACE_ROOT / "_백업" / "2026-04-30"

sys.path.insert(0, str(WORKSPACE_ROOT / ".agent" / "scripts"))
fix_ocr_hanja = __import__("fix_ocr_hanja")

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


def is_excluded(path: Path) -> bool:
    s = str(path)
    return any(pat in s for pat in EXCLUDE_PATH_PATTERNS)


def process_file(path: Path, dry_run: bool) -> int:
    original = path.read_text(encoding="utf-8")
    total = 0
    new_lines: list[str] = []
    for line in original.splitlines(keepends=False):
        new_line, n = fix_ocr_hanja.process_line(line)
        new_lines.append(new_line)
        total += n
    if total == 0:
        return 0
    new_text = "\n".join(new_lines)
    if original.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    if new_text == original:
        return 0
    if not dry_run:
        rel = path.relative_to(WORKSPACE_ROOT)
        backup = BACKUP_ROOT / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        # 이미 normalize 단계에서 같은 경로에 백업이 있을 수 있음 — 덮어쓰지 않음
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
            entry = {"path": str(rel), "replacements": n}
            summary["files"].append(entry)
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
