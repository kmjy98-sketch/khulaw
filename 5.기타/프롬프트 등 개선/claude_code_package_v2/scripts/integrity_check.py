#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integrity_check.py — 안티그래비티(Gemini) 출력 글자수 무결성 독립 재계측 (Phase 2)

목적:
  01 OCR · 02-wiki 위키화 출력에서 본문 글자수를 *독립적으로 다시 세어*,
  안티그래비티가 본문을 silent drop(누락)하거나 임의 압축하지 않았는지 검증한다.
  프롬프트의 자가보고(INTEGRITY / TOTAL_CHARS)는 LLM이 부정확/허위로 적을 수 있으므로,
  이 스크립트의 재계측이 실제 강제력(teeth)이다.

핵심 지표 — 한글 글자수 보존율:
  법학 본문은 거의 전부 한글(가-힣)이다. 마크다운 기호(#, *, >, [[ ]])·YAML·HTML 주석은
  한글을 거의 포함하지 않으므로, "한글 글자수"는 마크업 변화에 둔감하면서 본문 누락에는 민감한
  강건한 보존 지표가 된다.
  02-wiki는 '변환'(보존)이지 '요약'이 아니므로(프롬프트 ABSOLUTE RULES), 정상 출력의
  보존율 = 한글(02-wiki 본문) / 한글(01 출력 본문) 은 약 1.0 (구조 추가분으로 약간 ↑).
  보존율 < 임계(기본 0.90)면 누락 의심.

사용법:
  # 기본: 패키지 outputs/01_ocr, outputs/02_wiki 전체 스캔
  python scripts/integrity_check.py

  # 단일 쌍 검사
  python scripts/integrity_check.py --wiki outputs/02_wiki/책_chunk_001_wiki.md \
                                     --src  outputs/01_ocr/책_chunk_001.md

  # 임계값 조정 + 리포트 파일 출력
  python scripts/integrity_check.py --min-ratio 0.90 --report

종료 코드: 무결성 위반(보존율 미달·자가보고 불일치·누락 플래그)이 하나라도 있으면 1, 없으면 0.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 스크립트 위치 기준 패키지 루트 (scripts/ 의 부모)
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OCR_DIR = PACKAGE_ROOT / "outputs" / "01_ocr"
DEFAULT_WIKI_DIR = PACKAGE_ROOT / "outputs" / "02_wiki"
DEFAULT_REPORT = PACKAGE_ROOT / "outputs" / "_integrity_report.md"

HANGUL_RE = re.compile(r"[가-힣]")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
YAML_FM_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
WS_RE = re.compile(r"\s+")

# 본문에서 제외할 메타/앵커 줄 (한글이 섞여 보존율을 왜곡하므로 제거)
META_LINE_PREFIXES = (
    "INTEGRITY:", "CHUNK:", "TOTAL_CHARS:", "source:", "source_page:",
    "book_type", "chunk:", "attribute_distribution", "책 유형 추정",
    "hint 일치", "END_OF_CHUNK", "STOP:", "참고: 모드",
)
# verification 체크리스트 시작 표지 (이 줄부터 청크 끝까지는 본문이 아님)
VERIFICATION_HEADERS = (
    "verification_protocol",
    "verification protocol",
)

# 누락/불명 플래그
FLAG_RE = re.compile(r"\{(누락의심|누락경고|불명|OCR불명)")

# 자가보고 파서
INTEGRITY_RE = re.compile(
    r"INPUT_CHARS\s*=\s*([\d,]+).*?OUTPUT_BODY_CHARS\s*=\s*([\d,]+).*?보존율\s*=\s*(\d+)",
    re.DOTALL,
)
TOTAL_CHARS_RE = re.compile(r"TOTAL_CHARS:\s*([\d,]+)")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def hangul_count(text: str) -> int:
    return len(HANGUL_RE.findall(text))


def nonspace_count(text: str) -> int:
    return len(WS_RE.sub("", text))


def to_int(s: str) -> int:
    return int(s.replace(",", ""))


def extract_body(text: str) -> str:
    """YAML frontmatter·HTML 주석·메타 줄·verification 체크리스트를 제거한 '본문' 추출."""
    body = YAML_FM_RE.sub("", text)
    body = HTML_COMMENT_RE.sub("", body)

    lines = body.splitlines()
    out: list[str] = []
    for ln in lines:
        stripped = ln.strip()
        low = stripped.lower()
        # verification 체크리스트 표지를 만나면 이후는 본문 아님 → 중단
        if any(h in low for h in VERIFICATION_HEADERS):
            break
        if any(stripped.startswith(p) for p in META_LINE_PREFIXES):
            continue
        # 체크리스트 항목 줄 ("- [✓] ...", "- [ ] ...")
        if re.match(r"-\s*\[[ ✓xX]\]", stripped):
            continue
        out.append(ln)
    return "\n".join(out)


def parse_integrity(text: str):
    m = INTEGRITY_RE.search(text)
    if not m:
        return None
    return {
        "input_chars": to_int(m.group(1)),
        "output_body_chars": to_int(m.group(2)),
        "ratio_pct": int(m.group(3)),
    }


def parse_total_chars(text: str):
    m = TOTAL_CHARS_RE.search(text)
    return to_int(m.group(1)) if m else None


def scan_flags(text: str) -> dict:
    counts: dict[str, int] = {}
    for kind in FLAG_RE.findall(text):
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def find_src_for_wiki(wiki_path: Path, ocr_dir: Path):
    """위키 파일에 대응하는 01 OCR 원본 찾기 (stem 에서 _wiki 제거)."""
    stem = wiki_path.stem
    if stem.endswith("_wiki"):
        stem = stem[: -len("_wiki")]
    cand = ocr_dir / f"{stem}.md"
    if cand.exists():
        return cand
    # 폴백: 같은 stem 으로 시작하는 파일 검색
    if ocr_dir.exists():
        for p in sorted(ocr_dir.glob(f"{stem}*.md")):
            return p
    return None


class Row:
    def __init__(self, name):
        self.name = name
        self.kind = ""          # wiki / ocr
        self.src = "—"
        self.h_src = None
        self.h_out = None
        self.ratio = None       # 재계측 보존율 (0~)
        self.self_report = "—"
        self.report_gap = None  # 자가보고 vs 재계측 차이(%p)
        self.flags = ""
        self.status = "OK"
        self.notes: list[str] = []

    def fail(self, note):
        self.status = "FAIL"
        self.notes.append(note)

    def warn(self, note):
        if self.status != "FAIL":
            self.status = "WARN"
        self.notes.append(note)


def check_wiki(wiki_path: Path, ocr_dir: Path, min_ratio: float) -> Row:
    row = Row(wiki_path.name)
    row.kind = "wiki"
    text = read_text(wiki_path)
    body = extract_body(text)
    row.h_out = hangul_count(body)

    flags = scan_flags(text)
    if flags:
        row.flags = ", ".join(f"{k}×{v}" for k, v in flags.items())
        if "누락경고" in flags:
            row.fail("누락경고 플래그 존재")

    src_path = find_src_for_wiki(wiki_path, ocr_dir)
    if src_path is None:
        row.warn("01 원본 없음 — 자가보고만 확인")
    else:
        row.src = src_path.name
        src_body = extract_body(read_text(src_path))
        row.h_src = hangul_count(src_body)
        if row.h_src > 0:
            row.ratio = row.h_out / row.h_src
            if row.ratio < min_ratio:
                row.fail(f"보존율 {row.ratio*100:.0f}% < {min_ratio*100:.0f}% (본문 누락 의심)")
            elif row.ratio > 1.30:
                row.warn(f"보존율 {row.ratio*100:.0f}% — 본문 임의 증식 의심")
        else:
            row.warn("01 원본 본문 한글 0 — 비교 불가")

    rep = parse_integrity(text)
    if rep is None:
        row.warn("INTEGRITY 자가보고 누락")
    else:
        row.self_report = f"{rep['ratio_pct']}%(자가)"
        if row.ratio is not None:
            row.report_gap = rep["ratio_pct"] - row.ratio * 100
            if abs(row.report_gap) > 10:
                row.warn(f"자가보고({rep['ratio_pct']}%) vs 재계측({row.ratio*100:.0f}%) 괴리 {row.report_gap:+.0f}%p")
    return row


def check_ocr(ocr_path: Path) -> Row:
    row = Row(ocr_path.name)
    row.kind = "ocr"
    text = read_text(ocr_path)
    body = extract_body(text)
    row.h_out = hangul_count(body)

    flags = scan_flags(text)
    if flags:
        row.flags = ", ".join(f"{k}×{v}" for k, v in flags.items())
        if "누락의심" in flags:
            row.warn("누락의심 페이지 존재")

    reported = parse_total_chars(text)
    if reported is None:
        row.warn("TOTAL_CHARS 자가보고 누락")
    else:
        actual = nonspace_count(body)
        row.self_report = f"{reported:,}(자가)/{actual:,}(실측)"
        if actual > 0:
            gap = (reported - actual) / actual
            if abs(gap) > 0.15:
                row.warn(f"TOTAL_CHARS 자가보고({reported:,}) vs 실측({actual:,}) 괴리 {gap*100:+.0f}%")
    return row


def fmt(v, pct=False):
    if v is None:
        return "—"
    if pct:
        return f"{v*100:.0f}%"
    return f"{v:,}"


def render_table(rows: list[Row], min_ratio: float) -> str:
    lines = []
    lines.append(f"# 무결성 재계측 리포트 (임계 보존율 {min_ratio*100:.0f}%)")
    lines.append("")
    lines.append("| 파일 | 단계 | 원본(01) | 한글(01) | 한글(출력) | 보존율 | 자가보고 | 플래그 | 상태 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r.name} | {r.kind} | {r.src} | {fmt(r.h_src)} | {fmt(r.h_out)} | "
            f"{fmt(r.ratio, pct=True)} | {r.self_report} | {r.flags or '—'} | {r.status} |"
        )
    notes = [r for r in rows if r.notes]
    if notes:
        lines.append("")
        lines.append("## 비고")
        for r in notes:
            lines.append(f"- **{r.name}**: " + "; ".join(r.notes))
    return "\n".join(lines)


def main(argv=None) -> int:
    # Windows 콘솔(cp949)에서도 UTF-8 출력 (em-dash·≥·→ 등 인코딩 크래시 방지)
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="안티그래비티 출력 글자수 무결성 재계측")
    ap.add_argument("--wiki", type=Path, help="단일 02-wiki 출력 파일")
    ap.add_argument("--src", type=Path, help="--wiki 의 짝이 되는 01 OCR 원본 (생략 시 자동 탐색)")
    ap.add_argument("--ocr-dir", type=Path, default=DEFAULT_OCR_DIR, help="01 OCR 출력 폴더")
    ap.add_argument("--wiki-dir", type=Path, default=DEFAULT_WIKI_DIR, help="02-wiki 출력 폴더")
    ap.add_argument("--min-ratio", type=float, default=0.90, help="보존율 하한 (기본 0.90)")
    ap.add_argument("--report", action="store_true", help="리포트를 outputs/_integrity_report.md 에 저장")
    args = ap.parse_args(argv)

    rows: list[Row] = []

    if args.wiki:
        if not args.wiki.exists():
            print(f"[오류] 파일 없음: {args.wiki}", file=sys.stderr)
            return 2
        ocr_dir = args.src.parent if args.src else args.ocr_dir
        row = check_wiki(args.wiki, ocr_dir, args.min_ratio)
        if args.src and args.src.exists():
            # 명시 원본으로 보존율 재계산
            src_body = extract_body(read_text(args.src))
            row.src = args.src.name
            row.h_src = hangul_count(src_body)
            if row.h_src > 0:
                row.ratio = row.h_out / row.h_src
                row.status = "OK"
                row.notes = []
                if row.ratio < args.min_ratio:
                    row.fail(f"보존율 {row.ratio*100:.0f}% < {args.min_ratio*100:.0f}%")
        rows.append(row)
    else:
        wiki_files = sorted(args.wiki_dir.glob("*_wiki.md")) if args.wiki_dir.exists() else []
        ocr_files = sorted(args.ocr_dir.glob("*.md")) if args.ocr_dir.exists() else []
        if not wiki_files and not ocr_files:
            print(f"[정보] 검사할 출력이 없습니다. ({args.ocr_dir} / {args.wiki_dir})")
            print("       outputs/01_ocr/*.md, outputs/02_wiki/*_wiki.md 생성 후 다시 실행하세요.")
            return 0
        for f in ocr_files:
            rows.append(check_ocr(f))
        for f in wiki_files:
            rows.append(check_wiki(f, args.ocr_dir, args.min_ratio))

    table = render_table(rows, args.min_ratio)
    print(table)

    if args.report:
        DEFAULT_REPORT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_REPORT.write_text(table + "\n", encoding="utf-8")
        print(f"\n[저장] {DEFAULT_REPORT}")

    n_fail = sum(1 for r in rows if r.status == "FAIL")
    n_warn = sum(1 for r in rows if r.status == "WARN")
    print(f"\n요약: 총 {len(rows)}건 / FAIL {n_fail} / WARN {n_warn}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
