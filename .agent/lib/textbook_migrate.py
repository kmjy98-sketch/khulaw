#!/usr/bin/env python3
"""교재 원문 청크를 sync/_교재원문/ 하위로 복사 + frontmatter 주입 + 목차 생성.

2026-04-10 1차 이전(6교재) → 2026-04-11 2차 이전(B 11교재 + C 재처리).
이전 작업 원본: 5.기타/_trash/2026-04-10/tmp_scripts/textbook_migrate.py (로직 기반).

주요 개선:
- parse_chunk_filename: 판수 suffix (`_p001-030_26.md`) 지원
- 공백 포함 파일명 지원
- `clean_existing` 옵션: 기존 sync/ 파일을 trash로 이동 후 재생성 (C 재처리용)
- 교재별 `known_prefixes` 커스텀 지원
"""
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"H:\내 드라이브")
OUT_ROOT = ROOT / "sync" / "_교재원문"
TRASH_ROOT = ROOT / "5.기타" / "_trash" / date.today().isoformat()

# fmt: off
TEXTBOOKS = [
    # ── C 재처리 완료 (172 → 195) — 재실행 시 제외 ──
    # 송영곤_논점민법_보충: 이미 처리됨
    #
    # ── B 신규 10교재 (민법 8 / 헌법 1 / 선택법 1) — 전경운 민법3 제외(원본 0byte) ──
    {
        "id": "강혜림_민법1",
        "subject": "민법",
        "display": "강혜림 《민법강의》 1",
        "edition": "26",
        "src": "1.민사/10.강혜림_민법1/교재_추출",
        "include_prefixes": ["민법강의_"],
        "known_prefixes": ["민법강의_"],
        "group_by_book": True,  # 민총/물권/채총/채각 등 서브책자 자동 그룹
        "clean_existing": True,
    },
    # 전경운_민법3 비활성화: 원본 16청크 모두 0byte(추출 실패). OCR 재추출 필요.
    # {
    #     "id": "전경운_민법3",
    #     ...
    # },
    {
        "id": "송영곤_사례",
        "subject": "민법",
        "display": "송영곤 《민사법사례연습 1 — 민총》",
        "edition": "26",
        "src": "1.민사/31.송영곤_사례/교재_추출",
        "include_prefixes": ["송영곤_사례연습_"],
        "known_prefixes": ["송영곤_사례연습_"],
        "group_by_book": True,
        "clean_existing": True,
    },
    {
        "id": "송영곤_사례연습2",
        "subject": "민법",
        "display": "송영곤 《민사법사례연습 2》",
        "edition": "23",
        "src": "1.민사/32.송영곤_사례연습2/교재_추출",
        "include_prefixes": [
            "민사법사례연습2_",
            "송영곤_민사법사례연습2_",
            "송영곤_사례연습2_",
        ],
        "known_prefixes": [
            "송영곤_민사법사례연습2_",
            "송영곤_사례연습2_",
            "민사법사례연습2_",
        ],
        "group_by_book": True,
        "clean_existing": True,
    },
    {
        "id": "송영곤_요건사실론",
        "subject": "민법",
        "display": "송영곤 《요건사실론》",
        "edition": "",
        "src": "1.민사/송영곤_요건사실론_추출",
        "include_prefixes": ["송영곤 요건사실론"],
        "known_prefixes": ["송영곤 요건사실론"],
        "group_by_book": False,
        "clean_existing": True,
    },
    {
        "id": "곽낙규_사례연습",
        "subject": "민법",
        "display": "곽낙규 《민법사례연습》",
        "edition": "2025",
        "src": "1.민사/91.보관/곽낙규_사례연습/교재_추출",
        "include_prefixes": [
            "2025_곽낙규_민사례_",
            "곽낙규_민법사례연습_",
            "민법사례연습_",
        ],
        "known_prefixes": [
            "2025_곽낙규_민사례_OCR",
            "곽낙규_민법사례연습_",
            "민법사례연습_",
        ],
        "group_by_book": True,
        "clean_existing": True,
    },
    {
        "id": "박승수_민법기본사례",
        "subject": "민법",
        "display": "박승수 《민법기본사례》",
        "edition": "23",
        "src": "1.민사/91.보관/박승수_민법기본사례/교재_추출",
        "include_prefixes": [
            "민법기본사례_",
            "TalkFile_민법사례연습_박승수",
            "박승수_기본사례_",
            "박승수_민법기본사례_",
        ],
        "known_prefixes": [
            "박승수_민법기본사례_",
            "박승수_기본사례_민법기본사례_",
            "박승수_기본사례_",
            "민법기본사례_",
            "TalkFile_민법사례연습_박승수",
        ],
        "group_by_book": True,
        "clean_existing": True,
    },
    {
        "id": "윤동환_민법의맥",
        "subject": "민법",
        "display": "윤동환 《민법의 맥》",
        "edition": "24",
        "src": "1.민사/91.보관/윤동환_민법의맥/교재_추출",
        "include_prefixes": ["민법의맥_", "기본사례의맥_"],
        "known_prefixes": ["민법의맥_", "기본사례의맥_"],
        "group_by_book": True,
        "clean_existing": True,
    },
    {
        "id": "민법의해석",
        "subject": "민법",
        "display": "이계정·양천수·권경휘·이성범 《민법의 해석》",
        "edition": "서울법대 법학총서",
        "src": "1.민사/91.보관/참고/교재_추출",
        "include_prefixes": ["민법의해석"],
        "known_prefixes": ["민법의해석"],
        "group_by_book": False,
        "clean_existing": True,
    },
    {
        "id": "강성민_헌법OX",
        "subject": "헌법",
        "display": "강성민 《헌법 최종정리 OX》",
        "edition": "25",
        "src": "3.공법/91.보관/강성민_헌법ox/정리_추출",
        "include_prefixes": ["강성민_헌법_"],
        "known_prefixes": ["강성민_헌법_"],
        "group_by_book": False,
        "clean_existing": True,
    },
    {
        "id": "법조윤리_한권탁_기출",
        "subject": "선택법",
        "display": "법조윤리 한권탁 기출문제집",
        "edition": "2024-2025",
        "src": "4.선택법/10.법조윤리/기출/chunks",
        "include_prefixes": ["법조윤리_한권탁_"],
        "known_prefixes": ["법조윤리_한권탁_"],
        "group_by_book": True,
        "clean_existing": True,
    },
]
# fmt: on


# 파일명 끝 패턴: _p{start}-{end}[_{edition}].md (판수 suffix 허용)
CHUNK_PAT = re.compile(r"_p(\d+)-(\d+)(?:_\d+)?\.md$")
# 대안 패턴: _p{N}.md (단일 페이지)
SINGLE_PAGE_PAT = re.compile(r"_p(\d+)(?:_\d+)?\.md$")


def parse_chunk_filename(name: str, known_prefixes: list[str]) -> tuple[str | None, int | None, int | None]:
    """파일명에서 (book_part, page_start, page_end) 추출.

    규칙:
    1. 끝에서 `_p{N}-{M}[_{edition}]?.md` 또는 `_p{N}[_{edition}]?.md` 제거
    2. 남은 stem에서 판수 suffix(`_\\d{2}`) 제거
    3. known_prefixes 중 하나로 시작하면 그것을 제거, 남은 부분이 book_part
    """
    m = CHUNK_PAT.search(name)
    if m:
        p_start, p_end = int(m.group(1)), int(m.group(2))
        stem = name[: m.start()]
    else:
        m = SINGLE_PAGE_PAT.search(name)
        if not m:
            return None, None, None
        p_start = int(m.group(1))
        p_end = p_start
        stem = name[: m.start()]

    # 끝의 판수 suffix 제거 (예: _24, _25, _26)
    stem = re.sub(r"_\d{2,4}$", "", stem)
    stem = stem.strip("_ ")

    book_part = None
    for p in known_prefixes:
        if stem.startswith(p):
            rest = stem[len(p):].lstrip("_ ")
            if rest:
                book_part = rest
            break
    # 매칭 안 되면 stem 자체가 book_part
    if book_part is None and stem:
        book_part = stem
    return book_part, p_start, p_end


def build_frontmatter(
    tb: dict,
    book_part: str | None,
    p_start: int | None,
    p_end: int | None,
    chapter_num: int,
    total_chapters: int,
) -> str:
    parts = [
        "---",
        f"tags: [교재원문, {tb['subject']}, {tb['id']}]",
        f"교재: {tb['display']}",
    ]
    if tb.get("edition"):
        parts.append(f"판: {tb['edition']}")
    parts.append(f"과목: {tb['subject']}")
    if book_part:
        parts.append(f"서브책자: {book_part}")
    parts.append(f"챕터번호: {chapter_num:02d}")
    parts.append(f"전체챕터: {total_chapters}")
    if p_start is not None and p_end is not None:
        parts.append(f"페이지: {p_start}-{p_end}")
    parts.append("---")
    parts.append("")
    return "\n".join(parts)


def clean_existing_output(tb: dict) -> int:
    """기존 sync/_교재원문/{과목}/{tb_id}/ 내 파일을 trash로 이동."""
    out_dir = OUT_ROOT / tb["subject"] / tb["id"]
    if not out_dir.exists():
        return 0
    trash_dir = TRASH_ROOT / f"교재원문_{tb['id']}_pre"
    trash_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    for f in list(out_dir.glob("*.md")):
        dst = trash_dir / f.name
        shutil.move(str(f), str(dst))
        moved += 1
    return moved


def migrate_chunk_textbook(tb: dict) -> dict:
    src_dir = ROOT / tb["src"]
    if not src_dir.exists():
        return {"tb": tb["id"], "error": f"소스 없음: {src_dir}", "files": 0}

    out_dir = OUT_ROOT / tb["subject"] / tb["id"]

    # clean_existing: 기존 파일 trash로 이동 (C 재처리)
    moved = 0
    if tb.get("clean_existing"):
        moved = clean_existing_output(tb)

    out_dir.mkdir(parents=True, exist_ok=True)

    chunks = []
    skipped_parse = 0
    for f in sorted(src_dir.glob("*.md")):
        if f.stat().st_size == 0:
            continue
        include = tb.get("include_prefixes") or []
        if include and not any(f.name.startswith(p) for p in include):
            continue
        exclude = tb.get("exclude_prefixes") or []
        if exclude and any(f.name.startswith(p) for p in exclude):
            continue
        if "목차" in f.name or "판례색인" in f.name:
            continue
        known = tb.get("known_prefixes") or tb.get("include_prefixes") or []
        book_part, p_start, p_end = parse_chunk_filename(f.name, known)
        if p_start is None:
            skipped_parse += 1
            continue
        chunks.append({
            "src": f,
            "book_part": book_part,
            "p_start": p_start,
            "p_end": p_end,
        })

    if not chunks:
        return {
            "tb": tb["id"],
            "error": "청크 파일 0개",
            "files": 0,
            "skipped_parse": skipped_parse,
        }

    # 챕터 배치
    if tb.get("group_by_book"):
        groups: dict[str, list[dict]] = defaultdict(list)
        for c in chunks:
            key = c["book_part"] or "본문"
            groups[key].append(c)
        for key in groups:
            groups[key].sort(key=lambda c: c["p_start"])
        chapter_num = 0
        all_out = []
        for key in sorted(groups.keys()):
            for c in groups[key]:
                chapter_num += 1
                all_out.append((chapter_num, c))
        total = chapter_num
    else:
        chunks.sort(key=lambda c: (c["book_part"] or "", c["p_start"]))
        all_out = [(i + 1, c) for i, c in enumerate(chunks)]
        total = len(all_out)

    # 파일 생성
    toc_entries = []
    for chap_num, c in all_out:
        src_f = c["src"]
        content = src_f.read_text(encoding="utf-8", errors="replace")
        fm = build_frontmatter(tb, c["book_part"], c["p_start"], c["p_end"], chap_num, total)
        out_name = (
            f"{tb['id']}_ch{chap_num:02d}_p{c['p_start']:04d}-{c['p_end']:04d}.md"
        )
        out_f = out_dir / out_name
        title_bits = [tb["display"]]
        if c["book_part"]:
            title_bits.append(c["book_part"])
        title_bits.append(f"ch{chap_num:02d} (p.{c['p_start']}-{c['p_end']})")
        title = " — ".join(title_bits)
        body = fm + f"# {title}\n\n" + content
        out_f.write_text(body, encoding="utf-8")
        toc_entries.append({
            "num": chap_num,
            "book_part": c["book_part"],
            "p_start": c["p_start"],
            "p_end": c["p_end"],
            "filename": out_name,
            "stem": out_name[:-3],
        })

    # 교재 목차 생성
    toc_lines = [
        "---",
        f"tags: [교재목차, {tb['subject']}, {tb['id']}]",
        f"교재: {tb['display']}",
    ]
    if tb.get("edition"):
        toc_lines.append(f"판: {tb['edition']}")
    toc_lines += [
        f"과목: {tb['subject']}",
        "---",
        "",
        f"# {tb['display']} — 교재 목차",
        "",
        f"> **과목**: {tb['subject']}",
        f"> **전체 챕터**: {total}",
        f"> **소스**: `{tb['src']}`",
        "",
        "## 챕터 목록",
        "",
    ]
    if tb.get("group_by_book"):
        last_part = None
        for e in toc_entries:
            if e["book_part"] != last_part:
                toc_lines.append("")
                toc_lines.append(f"### {e['book_part'] or '본문'}")
                toc_lines.append("")
                last_part = e["book_part"]
            toc_lines.append(
                f"- ch{e['num']:02d} p.{e['p_start']}-{e['p_end']} — [[{e['stem']}]]"
            )
    else:
        for e in toc_entries:
            toc_lines.append(
                f"- ch{e['num']:02d} p.{e['p_start']}-{e['p_end']} — [[{e['stem']}]]"
            )
    toc_lines.append("")
    (out_dir / "_교재목차.md").write_text("\n".join(toc_lines), encoding="utf-8")

    return {
        "tb": tb["id"],
        "files": len(toc_entries),
        "out_dir": str(out_dir.relative_to(ROOT)),
        "skipped_parse": skipped_parse,
        "cleaned": moved,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    results = []
    for tb in TEXTBOOKS:
        result = migrate_chunk_textbook(tb)
        results.append(result)
        if result.get("error"):
            print(f"[ERR] {result['tb']}: {result['error']}")
        else:
            cleaned_note = f" (cleaned {result['cleaned']})" if result.get("cleaned") else ""
            skipped_note = (
                f" [skipped_parse={result['skipped_parse']}]"
                if result.get("skipped_parse")
                else ""
            )
            print(f"[OK]  {result['tb']}: {result['files']} files → {result['out_dir']}{cleaned_note}{skipped_note}")

    total_files = sum(r.get("files", 0) for r in results)
    total_skipped = sum(r.get("skipped_parse", 0) for r in results)
    print()
    print(f"=== 요약 ===")
    print(f"  처리 교재: {len(results)}")
    print(f"  총 청크 이전: {total_files}")
    if total_skipped:
        print(f"  파싱 실패 스킵: {total_skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
