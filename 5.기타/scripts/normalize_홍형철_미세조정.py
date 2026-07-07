# -*- coding: utf-8 -*-
"""
홍형철 기본형법 — 미세조정 정규화 스크립트
============================================
대상  : sync/_교재원문/형법/홍형철_기본형법/ (.md, _백업/_trash 제외)
작성  : 2026-04-29
원칙  : CLAUDE.md #1 (소스 보존), #34 (anchor 보존), #15 (Verify-Before-Act),
        #16 (삭제 금지) — 변경 전 백업은 backup_홍형철_2026-04-29.ps1로 처리

처리 패턴 (4종)
---------------
  A. 단일줄 front matter → 정상 YAML 블록으로 분해
  B. collapsed table (한 줄에 헤더+구분선+여러 행) → 행 단위 분리
  C. 볼드 마커 분할 (`- **\n- ① 긍정설**:`) → 한 항목으로 결합
  D. 헤더 + 본문 같은 줄 (`#### 3. 판례의 태도 판례는 …`) → 분리

원칙
----
* 정규식은 보수적으로 적용. 매칭 안 되면 손대지 않음.
* anchor (조문번호·사건번호·한자)는 절대 변경하지 않음.
* callout(`> [!판례]`) 내부 라인은 변경 대상 아님.
* dry-run이 기본. --apply 명시해야 실제 쓰기.

사용법
------
    # 진단만 (기본)
    python normalize_홍형철_미세조정.py --dry-run

    # 실제 적용 (백업 후)
    python normalize_홍형철_미세조정.py --apply

    # 단일 파일만
    python normalize_홍형철_미세조정.py --dry-run --file 홍형철_쟁점정리_형법_25_p001-030.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------- 경로
SRC_DIR = Path(r"H:\내 드라이브\sync\_교재원문\형법\홍형철_기본형법")
META_DIR = Path(r"H:\내 드라이브\sync\_meta")
TODAY = "2026-04-29"
DRY_REPORT = META_DIR / f"홍형철_정규화_dry_run_{TODAY}.md"
APPLY_REPORT = META_DIR / f"홍형철_정규화_apply_{TODAY}.md"

# ---------------------------------------------------------------------- 통계
@dataclass
class FileStats:
    path: Path
    A_frontmatter: int = 0
    B_collapsed_table: int = 0
    C_bold_split: int = 0
    D_header_inline: int = 0

    def total(self) -> int:
        return (self.A_frontmatter + self.B_collapsed_table
                + self.C_bold_split + self.D_header_inline)


# ---------------------------------------------------------------------- A) Front matter
# 단일 줄 또는 압축된 front matter를 정상 YAML 블록으로 변환.
# 트리거: 첫 줄이 `--- tags:` 또는 `---tags:`로 시작하는 경우.
RE_FM_OPEN = re.compile(r"^---\s*tags:\s*(\[.*?\])\s*$")
RE_FM_CLOSE_INLINE = re.compile(r"\s*---\s*$")

def fix_frontmatter(lines: list[str]) -> tuple[list[str], int]:
    if not lines:
        return lines, 0
    m = RE_FM_OPEN.match(lines[0].rstrip("\n"))
    if not m:
        return lines, 0

    tags = m.group(1)
    # front matter 종결 위치 탐색 (최대 10줄까지)
    close_idx = -1
    for i in range(1, min(len(lines), 12)):
        if lines[i].strip() == "---":
            close_idx = i
            break
        if lines[i].rstrip().endswith("---"):
            # inline close: 본문 마지막에 ---이 붙어있는 경우
            close_idx = i
            break
    if close_idx == -1:
        return lines, 0

    # front matter 내부 메타 라인을 수집
    meta_lines: list[str] = []
    for i in range(1, close_idx + 1):
        line = lines[i].rstrip("\n")
        # close line의 trailing --- 제거
        if i == close_idx and line.rstrip().endswith("---"):
            line = re.sub(r"\s*---\s*$", "", line)
        if not line.strip():
            continue
        # `과목: 형법 주제: ... 포함_페이지: 1-30` 같은 압축된 라인 분해
        # 키워드 후보: 교재, 과목, 주제, 포함_페이지, 포함_쟁점, 출처, 비고
        keywords = ["교재", "과목", "주제", "포함_페이지", "포함_쟁점", "출처", "비고", "판"]
        # 분할: 키워드 앞에 공백이 있고 콜론이 따라오는 위치
        pattern = r"\s+(?=(?:" + "|".join(keywords) + r")\s*[:：])"
        parts = re.split(pattern, line)
        for p in parts:
            p = p.strip()
            if p:
                meta_lines.append(p)

    new_fm = ["---\n", f"tags: {tags}\n"]
    for ml in meta_lines:
        new_fm.append(ml + "\n")
    new_fm.append("---\n")

    new_lines = new_fm + lines[close_idx + 1 :]
    return new_lines, 1


# ---------------------------------------------------------------------- B) Collapsed table
# `| 쟁점 | 제목 | 페이지 | |------|------|------| | 001 | xxx | 16 | | 002 | yyy |`
# → 헤더 / 구분선 / 각 행을 별도 줄로 분리
RE_TABLE_COLLAPSED = re.compile(r"^\|.*\|\s*\|------.*\|.*\|.*$")

def fix_collapsed_table(line: str) -> tuple[list[str], int]:
    if not RE_TABLE_COLLAPSED.match(line.rstrip("\n")):
        return [line], 0

    s = line.rstrip("\n")
    # `| |------` 위치 = 헤더 끝, 구분선 시작
    sep_idx = s.find("| |------")
    if sep_idx == -1:
        return [line], 0
    header = s[: sep_idx + 1].rstrip()
    rest = s[sep_idx + 2 :]  # `|------|...|`
    # 구분선 끝 = 다음 ` | |` 위치 (구분선 다음에 행 시작)
    # 구분선 패턴: `|------|------|...|`
    m = re.match(r"^(\|[\s\-:|]+\|)\s*(.*)$", rest)
    if not m:
        return [line], 0
    sep_line = m.group(1)
    body = m.group(2).strip()

    # body는 `| 001 | xxx | 16 | | 002 | yyy | 18 |` 형태
    # → `| ... |` 단위로 split
    # 각 행은 `|`로 시작해서 끝까지 — 단, `| |` 경계가 있음
    rows: list[str] = []
    if body:
        # `| |` 분리자로 split (단, 행 내부 `|`는 보존)
        # body를 `| |`로 split하면 첫 조각만 `|`로 시작 안 함
        chunks = re.split(r"\s*\|\s*\|\s*", body)
        for j, c in enumerate(chunks):
            c = c.strip()
            if not c:
                continue
            # 첫 조각/마지막 조각 정리
            if not c.startswith("|"):
                c = "| " + c
            if not c.endswith("|"):
                c = c + " |"
            rows.append(c)

    out = [header + "\n", sep_line + "\n"]
    for r in rows:
        out.append(r + "\n")
    return out, 1


# ---------------------------------------------------------------------- C) Bold split
# `- **\n- ① 긍정설**:` → `- **① 긍정설**:`
RE_BOLD_OPEN_BARE = re.compile(r"^- \*\*\s*$")
RE_BOLD_CONTINUE = re.compile(r"^- (.+\*\*[:：].*)$")

def fix_bold_split(lines: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    count = 0
    i = 0
    while i < len(lines):
        cur = lines[i].rstrip("\n")
        if RE_BOLD_OPEN_BARE.match(cur) and i + 1 < len(lines):
            nxt = lines[i + 1].rstrip("\n")
            m = RE_BOLD_CONTINUE.match(nxt)
            if m:
                merged = "- **" + m.group(1)
                out.append(merged + "\n")
                i += 2
                count += 1
                continue
        out.append(lines[i])
        i += 1
    return out, count


# ---------------------------------------------------------------------- D) Header inline
# `#### 3. 판례의 태도 판례는 **개별판단설**의 입장에서 …`
# → `#### 3. 판례의 태도\n\n판례는 …`
# 트리거: 헤더 라벨이 짧은 어구이고 그 뒤에 추가 본문이 붙은 경우.
# 보수적으로 — 헤더가 `N. 라벨` 패턴이고 그 뒤 본문이 `판례는|다음과|학설은|견해의` 등으로 시작.
RE_HEADER_INLINE = re.compile(
    r"^(####?\s+\d+\.\s+[^\n]{2,20}?)\s+(판례는|다음과|학설은|견해의|아래와|이는|이러한|위와|이를)(.+)$"
)

def fix_header_inline(line: str) -> tuple[list[str], int]:
    s = line.rstrip("\n")
    m = RE_HEADER_INLINE.match(s)
    if not m:
        return [line], 0
    header = m.group(1).rstrip()
    body = (m.group(2) + m.group(3)).strip()
    return [header + "\n", "\n", body + "\n"], 1


# ---------------------------------------------------------------------- callout 보호
# `> [!판례]` ... 빈 줄까지 callout 블록으로 간주, 이 블록 내부 라인은 B/D 패턴 적용 제외.
def is_in_callout(idx: int, lines: list[str]) -> bool:
    # 위로 거슬러 올라가며 `> [!` 또는 빈 줄 만날 때까지
    for j in range(idx - 1, -1, -1):
        s = lines[j].lstrip()
        if not s.strip():
            return False
        if s.startswith(">"):
            if "[!" in s:
                return True
            continue
        return False
    return False


# ---------------------------------------------------------------------- 메인 처리
def process_file(path: Path) -> tuple[list[str], FileStats]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    stats = FileStats(path=path)

    # A) front matter
    lines, a_cnt = fix_frontmatter(lines)
    stats.A_frontmatter = a_cnt

    # C) bold split (line-pair 처리)
    lines, c_cnt = fix_bold_split(lines)
    stats.C_bold_split = c_cnt

    # B) + D) 라인 단위
    out: list[str] = []
    for i, line in enumerate(lines):
        if is_in_callout(i, lines):
            out.append(line)
            continue
        # B 시도
        new_b, b_cnt = fix_collapsed_table(line)
        if b_cnt:
            stats.B_collapsed_table += b_cnt
            out.extend(new_b)
            continue
        # D 시도
        new_d, d_cnt = fix_header_inline(line)
        if d_cnt:
            stats.D_header_inline += d_cnt
            out.extend(new_d)
            continue
        out.append(line)

    return out, stats


def write_report(stats_list: list[FileStats], out_path: Path, mode: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 홍형철 미세조정 정규화 — {mode.upper()} 보고",
        f"- 일자: {TODAY}",
        f"- 모드: {mode}",
        f"- 처리 파일: {len(stats_list)}",
        "",
        "## 파일별 변경량",
        "",
        "| 파일 | A. front matter | B. collapsed table | C. bold split | D. header inline | 합계 |",
        "|------|---:|---:|---:|---:|---:|",
    ]
    total = FileStats(path=Path("총합"))
    for s in stats_list:
        lines.append(
            f"| {s.path.name} | {s.A_frontmatter} | {s.B_collapsed_table} "
            f"| {s.C_bold_split} | {s.D_header_inline} | {s.total()} |"
        )
        total.A_frontmatter += s.A_frontmatter
        total.B_collapsed_table += s.B_collapsed_table
        total.C_bold_split += s.C_bold_split
        total.D_header_inline += s.D_header_inline
    lines.append(
        f"| **합계** | **{total.A_frontmatter}** | **{total.B_collapsed_table}** "
        f"| **{total.C_bold_split}** | **{total.D_header_inline}** | **{total.total()}** |"
    )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[보고서] {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True)
    g.add_argument("--apply", action="store_true")
    ap.add_argument("--file", type=str, default=None,
                    help="단일 파일만 처리 (파일명만, 경로 X)")
    args = ap.parse_args()
    apply_mode = bool(args.apply)

    if not SRC_DIR.exists():
        print(f"[FATAL] 소스 폴더 없음: {SRC_DIR}", file=sys.stderr)
        return 2

    files = sorted(SRC_DIR.rglob("*.md"))
    files = [f for f in files
             if "_백업" not in f.parts and "_trash" not in f.parts]
    if args.file:
        files = [f for f in files if f.name == args.file]
        if not files:
            print(f"[FATAL] 파일 미발견: {args.file}", file=sys.stderr)
            return 2

    print(f"[홍형철] 미세조정 — 모드: {'APPLY' if apply_mode else 'DRY-RUN'}")
    print(f"[홍형철] 처리 파일: {len(files)}")
    print()

    stats_list: list[FileStats] = []
    for path in files:
        new_lines, stats = process_file(path)
        stats_list.append(stats)
        marker = "+" if stats.total() > 0 else "·"
        print(f"  {marker} {path.name}  "
              f"A={stats.A_frontmatter} B={stats.B_collapsed_table} "
              f"C={stats.C_bold_split} D={stats.D_header_inline} "
              f"(총 {stats.total()})")
        if apply_mode and stats.total() > 0:
            path.write_text("".join(new_lines), encoding="utf-8")

    print()
    write_report(stats_list, APPLY_REPORT if apply_mode else DRY_REPORT,
                 "apply" if apply_mode else "dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
