#!/usr/bin/env python3
"""정리노트의 ## 0. 소스 범위 표에 김준호 《민법강의》 32판 행 추가.

매핑 소스: .agent/state/kimjunho_chapter_map.json
대상: sync/민법/{총칙,물권,담보물권,채권총론,채권각론}/*.md
동작:
  - 각 정리노트의 ## 0. 소스 범위 표 위치 찾기
  - 표에 김준호 행이 이미 있으면 갱신, 없으면 마지막에 추가
  - 행 형식:
    | 김준호 《민법강의》 32판 — {장} | p.{시작}-{끝} | [[..._교재목차|김준호 민법강의 32판]] |
  - idempotent: 동일 내용이면 건너뜀
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"H:\내 드라이브")
NOTES_BASE = ROOT / "sync" / "민법"
MAP_FILE = ROOT / ".agent" / "state" / "kimjunho_chapter_map.json"

KIMJUNHO_LINK = "[[_교재원문/민법/강혜림_민법1/_교재목차|김준호 민법강의 32판]]"
KIMJUNHO_BOOK_PREFIX = "김준호 《민법강의》 32판"
KIMJUNHO_ROW_PAT = re.compile(r"^\|\s*김준호 《민법강의》[^|]*\|", re.MULTILINE)


def build_kimjunho_row(chapter: str, p_start: int, p_end: int) -> str:
    page_str = f"p.{p_start}-{p_end}" if p_start != p_end else f"p.{p_start}"
    return f"| {KIMJUNHO_BOOK_PREFIX} — {chapter} | {page_str} | {KIMJUNHO_LINK} |"


def process_note(file_path: Path, mapping: dict) -> tuple[bool, str]:
    """정리노트 한 파일 처리. (변경여부, 동작) 반환."""
    text = file_path.read_text(encoding="utf-8")

    # ## 0. 소스 범위 다음의 표 영역 찾기
    section_pat = re.compile(
        r"(## 0\. 소스 범위.*?\n\|.*?\n\|[-:|\s]*\n)((?:\|.*?\n)+)",
        re.DOTALL,
    )
    m = section_pat.search(text)
    if not m:
        return False, "no-source-table"

    header_part = m.group(1)
    rows_part = m.group(2)

    chapter = mapping["장"]
    p_start = mapping["p_start"]
    p_end = mapping["p_end"]
    new_row = build_kimjunho_row(chapter, p_start, p_end) + "\n"

    if KIMJUNHO_ROW_PAT.search(rows_part):
        # 기존 김준호 행 갱신
        new_rows_part = KIMJUNHO_ROW_PAT.sub(
            new_row.rstrip("\n").split("|", 1)[1],  # "| 김준호 ..." → " 김준호 ..."
            rows_part,
        )
        # 더 안전한 방식: 라인 단위 교체
        lines = rows_part.splitlines(keepends=True)
        new_lines = []
        replaced = False
        for line in lines:
            if line.startswith("| 김준호 《민법강의》"):
                new_lines.append(new_row)
                replaced = True
            else:
                new_lines.append(line)
        new_rows_part = "".join(new_lines)
        if not replaced:
            return False, "match-but-no-replace"
        action = "updated"
    else:
        # 표 마지막에 추가
        new_rows_part = rows_part + new_row
        action = "added"

    new_text = text[: m.start()] + header_part + new_rows_part + text[m.end():]
    if new_text == text:
        return False, "no-change"

    file_path.write_text(new_text, encoding="utf-8")
    return True, action


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not MAP_FILE.exists():
        print(f"매핑 파일 없음: {MAP_FILE}")
        return 1

    data = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    mappings = data.get("매핑", {})

    total_notes = 0
    matched = 0
    added = 0
    updated = 0
    skipped = 0
    no_source = 0
    not_in_map = []

    # 카테고리별 처리
    categories = ["총칙", "물권", "담보물권", "채권총론", "채권각론"]
    for category in categories:
        cat_dir = NOTES_BASE / category
        if not cat_dir.exists():
            continue
        cat_map = mappings.get(category, {})
        for note_path in sorted(cat_dir.glob("*.md")):
            if note_path.stem.startswith("_"):
                continue
            total_notes += 1
            stem = note_path.stem
            if stem not in cat_map:
                not_in_map.append(f"{category}/{stem}")
                continue
            matched += 1
            changed, action = process_note(note_path, cat_map[stem])
            if action == "added":
                added += 1
            elif action == "updated":
                updated += 1
            elif action == "no-source-table":
                no_source += 1
            else:
                skipped += 1

    print(f"전체 정리노트(민법): {total_notes}")
    print(f"매핑 매칭: {matched}")
    print(f"  김준호 행 추가: {added}")
    print(f"  김준호 행 갱신: {updated}")
    print(f"  ## 0. 소스 범위 없음: {no_source}")
    print(f"  변경 없음 (이미 동일): {skipped}")
    print(f"  매핑 테이블 미등록: {len(not_in_map)}")
    if not_in_map:
        print()
        print("=== 매핑 미등록 ===")
        for n in not_in_map:
            print(f"  - {n}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
