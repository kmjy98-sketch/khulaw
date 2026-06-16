"""sync/_교재원문 하위 모든 MD의 frontmatter를 파싱하고
원본 PDF 존재 + 페이지수 정합성을 검증한다.

사용법:
    python _md_pdf_audit.py            # 풀스캔, 콘솔 + JSON
    python _md_pdf_audit.py --quick    # 처음 200건만
"""
from __future__ import annotations
import re
import sys
import json
import argparse
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("ERROR: pymupdf 필요. `pip install pymupdf`", file=sys.stderr)
    sys.exit(1)

DRIVE = Path(r"H:\내 드라이브")
SYNC = DRIVE / "sync" / "_교재원문"

# --- 1. frontmatter 파서 (느슨) ---
KEY_RE = re.compile(r"([가-힣A-Za-z_][가-힣A-Za-z0-9_]*)\s*:\s*")


def split_frontmatter(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    return text[3:end].strip()


def parse_loose_yaml(block: str) -> dict:
    """`A: 1 B: 2 C: [x, y]` 같은 한 줄 다중키도 파싱."""
    fm: dict = {}
    if not block:
        return fm
    text = block.replace("\r", "")
    # 키 위치 인덱스 수집
    key_positions = [
        (m.start(), m.end(), m.group(1)) for m in KEY_RE.finditer(text)
    ]
    for i, (s, e, k) in enumerate(key_positions):
        next_s = key_positions[i + 1][0] if i + 1 < len(key_positions) else len(text)
        raw_val = text[e:next_s].strip()
        # 쉼표/줄바꿈 끝 깔끔하게
        raw_val = raw_val.rstrip(",").strip()
        # 리스트면 [ ] 안 그대로
        fm[k] = raw_val
    return fm


PAGE_RANGE_NUM_RE = re.compile(r"(\d+)\s*[-–~]\s*(\d+)")


def claim_last_page(fm: dict) -> int | None:
    # 1) 포함_페이지: [1, 2, 3] → 최댓값
    p = fm.get("포함_페이지")
    if p:
        nums = re.findall(r"\d+", str(p))
        if nums:
            return max(int(x) for x in nums)
    # 2) 페이지: "271-300"
    p = fm.get("페이지")
    if p:
        m = PAGE_RANGE_NUM_RE.search(str(p))
        if m:
            return int(m.group(2))
    # 3) pdf_pages: "pp.11–22"
    p = fm.get("pdf_pages")
    if p:
        m = PAGE_RANGE_NUM_RE.search(str(p))
        if m:
            return int(m.group(2))
    # 4) 교재_pages
    p = fm.get("교재_pages")
    if p:
        m = PAGE_RANGE_NUM_RE.search(str(p))
        if m:
            return int(m.group(2))
    return None


# --- 2. PDF 인덱스 ---
def build_pdf_index() -> dict[str, list[Path]]:
    """DRIVE 전체에서 PDF 수집, stem(소문자)→경로 리스트."""
    idx: dict[str, list[Path]] = {}
    # 과목 디렉터리 + sync (sync 안에도 PDF 있을 수 있음)
    roots = []
    for d in DRIVE.iterdir():
        if d.is_dir() and re.match(r"^\d+\.", d.name):
            roots.append(d)
    roots.append(SYNC)
    for root in roots:
        for p in root.rglob("*.pdf"):
            idx.setdefault(p.stem.lower(), []).append(p)
    return idx


def resolve_pdf(md: Path, fm: dict, pdf_index: dict[str, list[Path]]):
    """PDF 후보 결정: (path, source_label) 또는 (None, reason)."""
    # ① 명시적 pdf_원본
    pdf_orig = fm.get("pdf_원본", "") or ""
    pdf_orig = pdf_orig.strip().strip("'\"")
    if pdf_orig and not pdf_orig.startswith("미확인"):
        cand = DRIVE / pdf_orig.replace("/", "\\")
        if cand.exists():
            return cand, "explicit_pdf_원본"
        return None, f"explicit_not_found:{pdf_orig}"

    # ② 같은 폴더의 PDF 중 이름 토큰 겹침
    md_stem_norm = re.sub(r"_p\d+-\d+$", "", md.stem).lower()
    md_tokens = set(re.split(r"[_\-\s]+", md_stem_norm))
    md_tokens.discard("")
    siblings = list(md.parent.glob("*.pdf"))
    best_sib, best_score = None, 0
    for sib in siblings:
        sib_tokens = set(re.split(r"[_\-\s]+", sib.stem.lower()))
        score = len(md_tokens & sib_tokens)
        if score > best_score:
            best_sib, best_score = sib, score
    if best_sib and best_score >= 2:
        return best_sib, "sibling_token_match"
    if best_sib and best_score == 1 and len(siblings) == 1:
        return best_sib, "sibling_only_pdf"

    # ③ 전역 PDF 인덱스에서 stem 직접 매칭
    if md_stem_norm in pdf_index:
        return pdf_index[md_stem_norm][0], "global_stem_exact"

    # ④ 전역 토큰 매칭 (≥3 토큰 겹침으로 엄격하게)
    if len(md_tokens) >= 2:
        best_p, best_score = None, 0
        for stem, paths in pdf_index.items():
            sib_tokens = set(re.split(r"[_\-\s]+", stem))
            score = len(md_tokens & sib_tokens)
            if score > best_score:
                best_score, best_p = score, paths[0]
        if best_p and best_score >= 3:
            return best_p, f"global_token_match(score={best_score})"

    return None, "no_pdf_found"


# --- 3. 메인 ---
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default="_md_pdf_audit_result.json")
    args = ap.parse_args()

    print("PDF 인덱스 구축 중...")
    pdf_index = build_pdf_index()
    print(f"  PDF 총 {sum(len(v) for v in pdf_index.values())}개 / 고유 stem {len(pdf_index)}개")

    all_md = list(SYNC.rglob("*.md"))
    if args.quick:
        all_md = all_md[:200]
    print(f"MD 총 {len(all_md)}개 스캔...")

    pdf_page_cache: dict[str, int] = {}

    def get_pdf_pages(p: Path) -> int | None:
        key = str(p)
        if key in pdf_page_cache:
            return pdf_page_cache[key]
        try:
            doc = fitz.open(str(p))
            n = doc.page_count
            doc.close()
        except Exception as e:
            n = None
        pdf_page_cache[key] = n
        return n

    cat_no_fm = []
    cat_no_page_info = []
    cat_no_pdf_info = []  # 페이지 정보 있지만 PDF 못 찾음
    cat_pdf_explicit_missing = []
    cat_match = []
    cat_mismatch = []
    cat_pdf_open_fail = []

    for i, md in enumerate(all_md):
        if i % 200 == 0:
            print(f"  ... {i}/{len(all_md)}")
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            continue

        block = split_frontmatter(text)
        rel = str(md.relative_to(SYNC))
        if block is None:
            cat_no_fm.append(rel)
            continue
        fm = parse_loose_yaml(block)

        last_p = claim_last_page(fm)
        pdf_path, src = resolve_pdf(md, fm, pdf_index)

        if pdf_path is None:
            if src.startswith("explicit_not_found"):
                cat_pdf_explicit_missing.append({"md": rel, "claimed_pdf": src.split(":", 1)[1]})
            else:
                cat_no_pdf_info.append({"md": rel, "last_page": last_p})
            continue

        actual = get_pdf_pages(pdf_path)
        if actual is None:
            cat_pdf_open_fail.append({"md": rel, "pdf": str(pdf_path)})
            continue

        if last_p is None:
            # PDF 찾았지만 페이지 정보 없음 — 일단 매치로 분류, 페이지 비교 불가
            cat_match.append({"md": rel, "pdf": pdf_path.name, "actual_pages": actual, "claimed_last": None, "match_via": src})
            continue

        if last_p <= actual + 3:
            cat_match.append({"md": rel, "pdf": pdf_path.name, "actual_pages": actual, "claimed_last": last_p, "match_via": src})
        else:
            cat_mismatch.append({
                "md": rel, "pdf": str(pdf_path.relative_to(DRIVE)),
                "actual_pages": actual, "claimed_last": last_p, "diff": last_p - actual,
                "match_via": src,
            })

    summary = {
        "total_md": len(all_md),
        "no_frontmatter": len(cat_no_fm),
        "no_page_info_no_pdf": len(cat_no_pdf_info),
        "explicit_pdf_path_invalid": len(cat_pdf_explicit_missing),
        "pdf_open_fail": len(cat_pdf_open_fail),
        "matched_ok": len(cat_match),
        "page_mismatch": len(cat_mismatch),
    }

    out = {
        "summary": summary,
        "no_frontmatter": cat_no_fm,
        "no_pdf_info": cat_no_pdf_info,
        "explicit_pdf_missing": cat_pdf_explicit_missing,
        "pdf_open_fail": cat_pdf_open_fail,
        "page_mismatch": cat_mismatch,
        # matched_ok 는 너무 많으므로 샘플 30개만 저장
        "matched_ok_sample": cat_match[:30],
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== 요약 ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\n결과 저장: {args.out}")


if __name__ == "__main__":
    main()
