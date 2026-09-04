"""
sync/_교재원문/ 및 sync/ 전체 .md 파일 표 손상 흔적 스캔
- Phase 1 (read-only): 손상 패턴 검출
- Phase 1.5: 백업본 vs 현재본 비교
- 결과: 9.작업중/클로드/표_복구_2026-05-05.json (raw)
사용자 task: 표 복구 / 본문 외 영역 변경 절대 금지
"""
import json
import os
import re
import hashlib
from pathlib import Path
from collections import Counter

ROOT = Path(r"H:\내 드라이브")
SYNC = ROOT / "sync"
TXT = SYNC / "_교재원문"
BACKUP_TXT = SYNC / "_백업" / "2026-04-30" / "_교재원문"
BACKUP_BL = SYNC / "_백업" / "2026-04-30" / "backlink_normalize"
META_DIR = SYNC / "_meta"

# 손상 패턴 정규식
RE_TABLE_ALIGN = re.compile(r"^\s*\|?\s*:?-{3,}\s*(?::|\s)*\s*\|.*$")
RE_TABLE_ROW   = re.compile(r"^\s*\|.+\|\s*$")
RE_TABLE_MARK  = re.compile(r"^\s*[\[\<【\(]\s*표\s*\d*\s*[\]\>】\)]")
RE_HRULE_PDF   = re.compile(r"^\s*[_=─━]{6,}\s*$")
RE_FRONTMATTER = re.compile(r"^---\s*$")
RE_CODEBLOCK   = re.compile(r"^\s*```")


def column_count(line: str) -> int:
    """파이프 표 행의 셀 수 (양 끝 빈 셀 제외)."""
    s = line.strip()
    if not s.startswith("|") and not s.endswith("|"):
        return 0
    parts = s.split("|")
    # 양 끝 빈 부분 제거
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return len(parts)


def is_align_row(line: str) -> bool:
    """정렬 라인 (예: |---|---|, |:--|:--:|).
    최소 1개의 dash 셀이 있어야 함 (빈 셀만이면 False)."""
    s = line.strip()
    if not s or "|" not in s:
        return False
    cells = [c.strip() for c in s.strip("|").split("|")]
    non_empty = [c for c in cells if c]
    if not non_empty:
        return False
    return all(re.match(r"^:?-{2,}:?$", c) for c in non_empty)


def scan_file(path: Path) -> dict:
    """단일 파일 스캔. 손상 흔적 list 반환."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"error": str(e), "patterns": []}

    lines = content.splitlines()
    in_frontmatter = False
    in_codeblock = False
    frontmatter_seen = 0
    patterns = []

    # 표 영역 추적
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # 프론트매터 탐지
        if RE_FRONTMATTER.match(line):
            if not in_frontmatter and frontmatter_seen == 0 and i < 3:
                in_frontmatter = True
                frontmatter_seen += 1
            elif in_frontmatter:
                in_frontmatter = False
            i += 1
            continue
        if in_frontmatter:
            i += 1
            continue
        if RE_CODEBLOCK.match(line):
            in_codeblock = not in_codeblock
            i += 1
            continue
        if in_codeblock:
            i += 1
            continue

        stripped = line.strip()

        # 1. 표 마커 직후 평문 (broken_marker)
        if RE_TABLE_MARK.match(stripped):
            # 직후 5줄 안에 표 형식 등장 여부
            has_table = False
            for j in range(i + 1, min(i + 6, n)):
                if is_align_row(lines[j]) or RE_TABLE_ROW.match(lines[j]):
                    has_table = True
                    break
            if not has_table:
                patterns.append({"line": i + 1, "type": "broken_marker", "snippet": stripped[:80]})

        # 2. PDF 가로선 흔적 (___ 또는 === 다수)
        if RE_HRULE_PDF.match(stripped):
            patterns.append({"line": i + 1, "type": "pdf_hrule", "snippet": stripped[:60]})

        # 3. 정렬라인 검출 + 헤더 검증
        if is_align_row(line):
            # 정렬라인 직전 줄이 헤더이어야 함
            prev = lines[i - 1] if i > 0 else ""
            if not RE_TABLE_ROW.match(prev):
                ctx = f"prev:{prev.strip()[:40]} | sep:{stripped[:40]}"
                patterns.append({"line": i + 1, "type": "orphan_separator", "snippet": ctx[:120]})
            else:
                # 칼럼 수 일치 확인
                hc = column_count(prev)
                ac = column_count(line)
                if hc != ac and hc > 0 and ac > 0:
                    patterns.append({"line": i + 1, "type": "header_align_mismatch",
                                     "snippet": f"header={hc}, align={ac}"})

                # 표 본문 칼럼 수 검증
                j = i + 1
                col_counts = []
                while j < n and RE_TABLE_ROW.match(lines[j]) and not is_align_row(lines[j]):
                    col_counts.append(column_count(lines[j]))
                    j += 1

                if col_counts:
                    counter = Counter(col_counts)
                    most_common, _ = counter.most_common(1)[0]
                    if most_common != hc and hc > 0:
                        patterns.append({"line": i + 1, "type": "body_align_mismatch",
                                         "snippet": f"header={hc}, body_mode={most_common}"})
                    # 칼럼 수 불일치 행 개수
                    inconsistent = sum(1 for c in col_counts if c != most_common and c != hc)
                    if inconsistent > 0:
                        patterns.append({"line": i + 1, "type": "unbalanced_columns",
                                         "snippet": f"inconsistent_rows={inconsistent}/{len(col_counts)}"})
                # 표 끝까지 점프
                i = j
                continue

        # 4. 단독 표 행 (직전·직후 표 행 없음) — 칼럼 3+ 만 (2 이하는 OCR 노이즈)
        if RE_TABLE_ROW.match(line) and not is_align_row(line):
            prev = lines[i - 1] if i > 0 else ""
            nxt = lines[i + 1] if i + 1 < n else ""
            prev_is_table = RE_TABLE_ROW.match(prev) or is_align_row(prev)
            nxt_is_table = RE_TABLE_ROW.match(nxt) or is_align_row(nxt)
            if not prev_is_table and not nxt_is_table:
                cc = column_count(line)
                # 칼럼 3+ 만 진짜 깨진 표 후보로 본다 (1-2 칼럼은 OCR 노이즈)
                if cc >= 3:
                    patterns.append({"line": i + 1, "type": "isolated_pipe_row",
                                     "snippet": stripped[:120]})
        i += 1

    return {"patterns": patterns, "total_lines": n,
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}


def find_backup(path: Path):
    """현재 본 path 에 대응하는 백업 후보 찾기."""
    rel = path.relative_to(SYNC)
    candidates = []
    # _교재원문 백업
    bck1 = BACKUP_TXT.parent.parent / "_백업" / "2026-04-30" / rel
    if bck1.exists():
        candidates.append(("_백업/2026-04-30/_교재원문", bck1))
    # backlink_normalize 백업 (정리노트 류)
    bck2 = BACKUP_BL / rel
    if bck2.exists():
        candidates.append(("_백업/2026-04-30/backlink_normalize", bck2))
    # 같은 폴더 내 _백업 (홍형철 케이스)
    try:
        parent_bck = path.parent / "_백업"
        if parent_bck.exists() and parent_bck.is_dir():
            for sub in parent_bck.iterdir():
                try:
                    if sub.is_dir():
                        for f in sub.iterdir():
                            if f.is_file() and path.stem in f.name and f.suffix == ".md":
                                candidates.append((str(sub.relative_to(SYNC)).replace("\\", "/"), f))
                except OSError:
                    continue
    except OSError:
        pass
    return candidates


def count_tables(content: str):
    """파일 내 표 블록 개수와 총 표 행 수."""
    lines = content.splitlines()
    blocks = 0
    rows = 0
    in_table = False
    in_codeblock = False
    in_frontmatter = False
    fm_count = 0
    for i, line in enumerate(lines):
        if RE_FRONTMATTER.match(line):
            if not in_frontmatter and fm_count == 0 and i < 3:
                in_frontmatter = True
                fm_count += 1
            elif in_frontmatter:
                in_frontmatter = False
            continue
        if in_frontmatter:
            continue
        if RE_CODEBLOCK.match(line):
            in_codeblock = not in_codeblock
            continue
        if in_codeblock:
            continue
        if is_align_row(line) or RE_TABLE_ROW.match(line):
            rows += 1
            if not in_table:
                blocks += 1
                in_table = True
        else:
            in_table = False
    return blocks, rows


def main():
    md_files = sorted([p for p in TXT.rglob("*.md")
                       if "_백업" not in p.parts and "_trash" not in p.parts])
    notes_files = []
    for sub in ["민법", "형법", "헌법", "wiki"]:
        sub_dir = SYNC / sub
        if sub_dir.exists():
            notes_files.extend(p for p in sub_dir.rglob("*.md")
                               if "_백업" not in p.parts and "_trash" not in p.parts)
    notes_files = sorted(notes_files)

    print(f"[Phase 1] _교재원문 {len(md_files)}개, 정리노트 {len(notes_files)}개 스캔...")

    all_results = []
    type_counter = Counter()
    files_with_damage = 0

    for path in md_files + notes_files:
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        result = scan_file(path)
        if "error" in result:
            print(f"  ERROR {rel}: {result['error']}")
            continue
        if not result["patterns"]:
            continue
        files_with_damage += 1

        # 백업 후보
        backups = find_backup(path)
        backup_info = []
        for label, bck_path in backups:
            try:
                bck_content = bck_path.read_text(encoding="utf-8", errors="replace")
                bck_blocks, bck_rows = count_tables(bck_content)
                cur_content = path.read_text(encoding="utf-8", errors="replace")
                cur_blocks, cur_rows = count_tables(cur_content)
                backup_info.append({
                    "source": label,
                    "path": str(bck_path.relative_to(ROOT)).replace("\\", "/"),
                    "backup_table_blocks": bck_blocks,
                    "backup_table_rows": bck_rows,
                    "current_table_blocks": cur_blocks,
                    "current_table_rows": cur_rows,
                    "table_rows_lost": bck_rows - cur_rows,
                    "sha256_backup": hashlib.sha256(bck_content.encode("utf-8")).hexdigest(),
                })
            except Exception as e:
                backup_info.append({"source": label, "error": str(e)})

        for p in result["patterns"]:
            type_counter[p["type"]] += 1

        all_results.append({
            "file": rel,
            "patterns": result["patterns"],
            "pattern_count": len(result["patterns"]),
            "backups": backup_info,
            "sha256_current": result["sha256"],
            "total_lines": result["total_lines"],
        })

    # 손상 흔적 패턴 분포
    print(f"\n[결과] 손상 의심 파일 {files_with_damage}개")
    print("[패턴 분포]")
    for t, c in type_counter.most_common():
        print(f"  {t}: {c}")

    # 백업 매칭 통계
    has_backup = sum(1 for r in all_results if r["backups"])
    print(f"\n[백업 매칭] {has_backup}/{len(all_results)} 파일에 백업본 있음")

    # 표 행 손실 (백업 vs 현재) 큰 파일 top 30
    candidates = [r for r in all_results
                  if r["backups"] and any(b.get("table_rows_lost", 0) > 0 for b in r["backups"])]
    candidates.sort(key=lambda r: max((b.get("table_rows_lost", 0) for b in r["backups"]), default=0), reverse=True)
    print(f"\n[표 행 손실 의심 (백업>현재)] {len(candidates)}개")
    for r in candidates[:30]:
        max_loss = max(b.get("table_rows_lost", 0) for b in r["backups"])
        print(f"  -{max_loss:3d} {r['file']}")

    META_DIR.mkdir(exist_ok=True)
    out_json = META_DIR / "표_복구_2026-05-05_scan.json"
    out_json.write_text(json.dumps({
        "scan_date": "2026-05-05",
        "total_files_scanned": len(md_files) + len(notes_files),
        "files_with_damage": files_with_damage,
        "pattern_distribution": dict(type_counter),
        "results": all_results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[저장] {out_json}")


if __name__ == "__main__":
    main()
