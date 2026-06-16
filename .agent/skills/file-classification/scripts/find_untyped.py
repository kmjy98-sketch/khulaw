# -*- coding: utf-8 -*-
"""
유형번호가 없는 파일 찾기
유형번호 패턴: (1-01), (2-03), (3-02) 등
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path


TYPE_PATTERN = re.compile(r"^\(\d+-\d+\)")
DEFAULT_SCAN_ROOTS = (
    "1.민사",
    "2.형사",
    "3.공법",
    "4.선택법",
    "9.로스쿨입시",
    "민사",
    "형사",
    "공법",
    "선택법",
    "로스쿨",
)
EXCLUDE_PARTS = {
    ".agent",
    "_trash",
    "_inbox",
    "_RAG_데이터",
    "_노트앱",
    "0.공유드라이브",
    "공유드라이브",
}


def find_workspace_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".agent").is_dir():
            return candidate
    return None


def resolve_workspace_root(raw_root: str | None) -> Path:
    if raw_root:
        root = Path(raw_root).expanduser().resolve()
        if not (root / ".agent").is_dir():
            raise SystemExit(f"워크스페이스 루트 아님: {root}")
        return root

    cwd_root = find_workspace_root(Path.cwd().resolve())
    if cwd_root is not None:
        return cwd_root

    script_root = find_workspace_root(Path(__file__).resolve().parent)
    if script_root is not None:
        return script_root

    raise SystemExit("워크스페이스 루트를 찾을 수 없습니다. --root를 지정하세요.")


def resolve_scan_roots(workspace_root: Path, raw_dir: str | None) -> list[Path]:
    if raw_dir:
        scan_root = Path(raw_dir).expanduser()
        if not scan_root.is_absolute():
            scan_root = (workspace_root / scan_root).resolve()
        else:
            scan_root = scan_root.resolve()
        if not scan_root.exists():
            raise SystemExit(f"스캔 디렉토리 없음: {scan_root}")
        return [scan_root]

    seen: set[Path] = set()
    roots: list[Path] = []
    for name in DEFAULT_SCAN_ROOTS:
        candidate = (workspace_root / name).resolve()
        if candidate.exists() and candidate not in seen:
            seen.add(candidate)
            roots.append(candidate)
    return roots


def is_excluded_dir(path: Path, workspace_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(workspace_root.resolve())
    except ValueError:
        return False
    return any(part in EXCLUDE_PARTS for part in rel.parts)


def collect_untyped_files(workspace_root: Path, scan_roots: list[Path]) -> list[dict]:
    untyped_files: list[dict] = []

    for scan_root in scan_roots:
        for dirpath, dirnames, filenames in os.walk(scan_root):
            current_dir = Path(dirpath).resolve()
            if is_excluded_dir(current_dir, workspace_root):
                dirnames[:] = []
                continue

            dirnames[:] = [
                dirname
                for dirname in dirnames
                if dirname not in EXCLUDE_PARTS
            ]

            for filename in filenames:
                if TYPE_PATTERN.match(filename):
                    continue
                full_path = (current_dir / filename).resolve()
                untyped_files.append(
                    {
                        "path": str(full_path),
                        "dir": str(current_dir),
                        "filename": filename,
                    }
                )

    untyped_files.sort(key=lambda item: item["path"].lower())
    return untyped_files


def print_summary(untyped_files: list[dict], output_file: Path, scan_roots: list[Path], workspace_root: Path) -> None:
    print(f"유형번호 없는 파일: {len(untyped_files)}개")
    print(f"저장 위치: {output_file}")

    if scan_roots:
        display_roots = []
        for root in scan_roots:
            try:
                display_roots.append(str(root.relative_to(workspace_root)))
            except ValueError:
                display_roots.append(str(root))
        print(f"스캔 루트: {', '.join(display_roots)}")

    by_folder: Counter[str] = Counter()
    for item in untyped_files:
        folder = Path(item["dir"]).name or "."
        by_folder[folder] += 1

    print("\n폴더별 분포:")
    for folder, count in by_folder.most_common():
        print(f"  {folder}: {count}개")


def main() -> int:
    parser = argparse.ArgumentParser(description="유형번호 없는 파일 찾기")
    parser.add_argument("--dir", "-d", help="스캔 디렉토리 (기본: 과목 루트 전체)")
    parser.add_argument("--root", help="워크스페이스 루트")
    args = parser.parse_args()

    workspace_root = resolve_workspace_root(args.root)
    output_file = workspace_root / ".agent" / "state" / "untyped_files.json"
    scan_roots = resolve_scan_roots(workspace_root, args.dir)
    untyped_files = collect_untyped_files(workspace_root, scan_roots)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(untyped_files, handle, ensure_ascii=False, indent=2)

    print_summary(untyped_files, output_file, scan_roots, workspace_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
