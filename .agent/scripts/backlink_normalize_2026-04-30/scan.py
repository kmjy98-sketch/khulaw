"""
백링크 패턴 현황 스캐너 (2026-04-30)

영역별 패턴 통계 수집:
  L1: sync/_교재원문/
  L2: sync/{민법,형법,헌법,상법,...}/  (정리노트)
  L3: sync/wiki/

탐지 패턴:
  1) [[§N]]                — 표준 조문 백링크
  2) §N (평문)             — 비표준 조문 평문 (§10 이상만)
  3) [[YY?da/도/헌가/...N]]  — 표준 단축형 판례 백링크
  4) [[대판 YY.M.D, ...]]   — 풀형식 판례 백링크 (변환 대상)
  5) 대판 YY.M.D. NNdaN (평문) — 비표준 판례 평문
"""
import os
import re
import json
from collections import defaultdict, Counter
from pathlib import Path

SYNC = Path(r"H:\내 드라이브\sync")

# 영역 분류
def classify(path: Path) -> str:
    parts = path.relative_to(SYNC).parts
    if not parts:
        return "ROOT"
    head = parts[0]
    if head == "_교재원문":
        return "L1_교재원문"
    if head == "wiki":
        return "L3_wiki"
    if head.startswith("_"):
        return f"META_{head}"
    if head in ("민법", "형법", "헌법", "상법", "선택법", "국제법"):
        return f"L2_{head}"
    return f"OTHER_{head}"

# ==== 패턴 정의 ====
# 조문
PAT_ARTICLE_LINK = re.compile(r"\[\[§(\d{1,4})(?:[^\]]*)?\]\]")
PAT_ARTICLE_PLAIN = re.compile(r"(?<![\[\w가-힣])§(\d{1,4})\b")
# 백링크 안에 들어 있는 §는 PAT_ARTICLE_LINK로 별도 처리

# 판례 단축형 백링크: [[YY?대결/da/도/헌가/헌마/헌바/두/누/다/카/그/사/마/카기...N]]
# 가장 일반적인 사건번호 정규식
CASE_NUMBER = r"\d{2,4}(?:다|도|헌가|헌마|헌바|헌라|헌사|두|누|다카|카|그|마|마기|모|드|드합|드단|므|므합|구합|구단|허|후|타기|차|초기|호|허재|허단|허허)\d+"
PAT_CASE_LINK_SHORT = re.compile(rf"\[\[({CASE_NUMBER})\]\]")
# 풀형식: [[대판 1999.3.12, 98다18124]] 또는 [[헌재 2007.6.28., 2004헌마643]]
PAT_CASE_LINK_FULL = re.compile(
    r"\[\[((?:대판|대결|헌재|대법원|전합|대판\(전\)|대법원\s*\(전\))[^\]]*?(" + CASE_NUMBER + r")[^\]]*)\]\]"
)
# 평문 판례: 대판 YYYY.M.D, NNdaN  (백링크 밖)
PAT_CASE_PLAIN = re.compile(
    r"(?<!\[\[)(대판|대결|헌재|대법원)\s*[\(전합\)]*\s*\d{4}[.\s]\s*\d{1,2}[.\s]\s*\d{1,2}[.,\s]+\s*(" + CASE_NUMBER + r")"
)

EXCLUDE_DIRS = {".obsidian", ".trash", ".smart-env", "Clippings", "_백업",
                "__pycache__", "_meta", "_inbox", "_ocr_extracted",
                "_답안지", "_발제", "_조문원문", "_판례색인",  # _판례색인은 정의 본문이므로 별도
                }

def iter_md_files():
    for root, dirs, files in os.walk(SYNC):
        # exclude
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f.endswith(".md"):
                yield Path(root) / f

def strip_code_blocks(text: str) -> str:
    """코드블록 안은 백링크 검사 제외 (#35 규칙)"""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]+`", "", text)
    return text

def in_table_or_footnote(line: str) -> bool:
    """표/각주 라인 판단 (단순 휴리스틱)"""
    s = line.strip()
    if s.startswith("|") and s.endswith("|"):
        return True
    if re.match(r"^\[\^", s):
        return True
    return False

def main():
    stats = defaultdict(lambda: {
        "files": 0,
        "article_link": 0,        # [[§N]]
        "article_plain": 0,       # §N 평문
        "case_link_short": 0,     # [[NNdaN]]
        "case_link_full": 0,      # [[대판 ..., NNdaN]]
        "case_plain": 0,          # 대판 ... NNdaN 평문
    })

    examples = defaultdict(lambda: defaultdict(list))

    for fp in iter_md_files():
        try:
            text = fp.read_text(encoding="utf-8")
        except Exception:
            continue
        zone = classify(fp)
        stats[zone]["files"] += 1

        # 코드블록 제거
        scanned = strip_code_blocks(text)

        # 라인별 (표/각주 제외 안 함 — 통계만 수집, 변환 시점에 분리)
        for m in PAT_ARTICLE_LINK.finditer(scanned):
            stats[zone]["article_link"] += 1
            if len(examples[zone]["article_link"]) < 3:
                examples[zone]["article_link"].append((fp.name, m.group(0)))
        for m in PAT_ARTICLE_PLAIN.finditer(scanned):
            n = int(m.group(1))
            if n < 10:  # §1~§9 제외 (CLAUDE.md #35)
                continue
            stats[zone]["article_plain"] += 1
            if len(examples[zone]["article_plain"]) < 3:
                examples[zone]["article_plain"].append((fp.name, m.group(0)))
        for m in PAT_CASE_LINK_SHORT.finditer(scanned):
            stats[zone]["case_link_short"] += 1
            if len(examples[zone]["case_link_short"]) < 3:
                examples[zone]["case_link_short"].append((fp.name, m.group(0)))
        for m in PAT_CASE_LINK_FULL.finditer(scanned):
            stats[zone]["case_link_full"] += 1
            if len(examples[zone]["case_link_full"]) < 3:
                examples[zone]["case_link_full"].append((fp.name, m.group(0)))
        for m in PAT_CASE_PLAIN.finditer(scanned):
            stats[zone]["case_plain"] += 1
            if len(examples[zone]["case_plain"]) < 3:
                examples[zone]["case_plain"].append((fp.name, m.group(0)))

    # 출력
    out = {
        "stats_by_zone": dict(stats),
        "examples_by_zone": {k: dict(v) for k, v in examples.items()},
    }
    out_path = Path(__file__).parent / "scan_result.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # 표 형태로 콘솔 출력
    print(f"{'zone':<25} {'files':>7} {'art_lnk':>8} {'art_plain':>10} {'cs_short':>9} {'cs_full':>8} {'cs_plain':>9}")
    print("-" * 90)
    for zone in sorted(stats.keys()):
        s = stats[zone]
        print(f"{zone:<25} {s['files']:>7} {s['article_link']:>8} {s['article_plain']:>10} {s['case_link_short']:>9} {s['case_link_full']:>8} {s['case_plain']:>9}")

    # 합계
    total = Counter()
    for s in stats.values():
        for k, v in s.items():
            total[k] += v
    print("-" * 90)
    print(f"{'TOTAL':<25} {total['files']:>7} {total['article_link']:>8} {total['article_plain']:>10} {total['case_link_short']:>9} {total['case_link_full']:>8} {total['case_plain']:>9}")
    print(f"\n결과: {out_path}")

if __name__ == "__main__":
    main()
