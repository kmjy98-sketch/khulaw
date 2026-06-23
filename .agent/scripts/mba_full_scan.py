"""민법의맥 전체 331개 파일을 원본 extract와 비교해 재생성 후보 탐색.

기준:
- frontmatter의 서브책자/페이지 범위로 원본 추출 파일 매핑
- 노트 vs 원본 품질 비교 (노트의 OCR 잔존 지표 vs 원본의 양호성)
- 노트가 원본보다 열세면 재생성 후보로 분류
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

NOTES_DIR = Path(vp("sync", "_교재원문", "민법", "윤동환_민법의맥"))
EXTRACTS_DIR = Path(vp(".agent", "data", "exam_extracts"))

SUBBOOK_PREFIX = {
    "교재": "1-1_민법_윤동환_민법의맥_(교재)_",
    "민법의맥": "1-1_민법_윤동환_민법의맥_(교재)_",
    "목차": "1-2_민법_윤동환_민법의맥_목차_(교재)_",
    "민총": "1-3_민법_윤동환_민법의맥_민총_(교재)_",
    "물권": "1-4_민법_윤동환_민법의맥_물권_(교재)_",
    "채총": "1-5_민법_윤동환_민법의맥_채총_(교재)_",
    "채각": "1-6_민법_윤동환_민법의맥_채각_(교재)_",
    "친상": "1-7_민법_윤동환_민법의맥_친상_(교재)_",
    "서론": "1-8_민법_윤동환_민법의맥_서론_(교재)_",
    "정리": "2-2_민법_윤동환_민법의맥기초_(정리)_",
}

FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# OCR 잔존 지표
OCR_BAD = re.compile(
    r"[芮雨因]"                                    # 희귀 한자
    r"|[가-힣]{25,}"                                 # 25자 이상 공백 없는 한글
    r"|이행불능이된|경우에는그|하는그[가-힣]{2,4}"  # 띄어쓰기 누락 패턴
    r"|X1I\d+|저I\d{3,4}조|제\s?\d+죄\b"            # 파편 인용
    r"|\bZ[이은는을를의에와과도]"                    # Z 잔존
)

# 당사자 맥락에서만 '한자 잔존'을 센다
PARTY_CONTEXT = re.compile(r"[갑을병정무]|[甲乙丙丁戊]")


def parse_frontmatter(text: str) -> dict:
    m = FM_RE.match(text)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def find_extract(subbook: str, page_range: str) -> Path | None:
    m = re.match(r"(\d+)-(\d+)", page_range)
    if not m:
        return None
    start, end = int(m.group(1)), int(m.group(2))
    prefix = SUBBOOK_PREFIX.get(subbook)
    if not prefix:
        # 24_ocr_x 등 — 모든 prefix 시도
        for p in SUBBOOK_PREFIX.values():
            for suffix in [f"p{start:03d}-{end:03d}.md", f"p{start:04d}-{end:04d}.md"]:
                candidate = EXTRACTS_DIR / (p + suffix)
                if candidate.exists():
                    return candidate
        return None
    for suffix in [f"p{start:03d}-{end:03d}.md", f"p{start:04d}-{end:04d}.md"]:
        candidate = EXTRACTS_DIR / (prefix + suffix)
        if candidate.exists():
            return candidate
    return None


def count_bad(text: str) -> int:
    return len(OCR_BAD.findall(text))


def main():
    results = []
    stats = defaultdict(int)

    for md in sorted(NOTES_DIR.glob("*.md")):
        content = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        if not fm:
            stats["no_frontmatter"] += 1
            continue
        subbook = fm.get("서브책자", "")
        page_range = fm.get("페이지", "")
        extract = find_extract(subbook, page_range)
        if not extract:
            stats["no_extract"] += 1
            continue

        note_bad = count_bad(content)
        extract_bad = count_bad(extract.read_text(encoding="utf-8"))
        delta = note_bad - extract_bad
        stats["has_extract"] += 1
        if delta > 5:  # 노트가 extract보다 OCR 잔존 많음
            results.append({
                "note": md.name,
                "note_bad": note_bad,
                "extract_bad": extract_bad,
                "delta": delta,
                "extract": extract.name,
                "subbook": subbook,
                "page_range": page_range,
            })

    results.sort(key=lambda x: -x["delta"])
    out = Path(vp(".agent", "state", "mba_full_scan.json"))
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"전체 MBA 노트: {stats['has_extract'] + stats['no_extract'] + stats['no_frontmatter']}개")
    print(f"  원본 매핑 가능: {stats['has_extract']}개")
    print(f"  매핑 불가: {stats['no_extract']}개")
    print(f"  frontmatter 없음: {stats['no_frontmatter']}개")
    print()
    print(f"재생성 후보 (노트가 원본보다 OCR 잔존 많음): {len(results)}건")
    print()
    print(f"{'점수':>5} {'노트OCR':>6} {'원본OCR':>6}  파일")
    print("-" * 80)
    for r in results[:30]:
        print(f"{r['delta']:>5} {r['note_bad']:>6} {r['extract_bad']:>6}  {r['note']}")
    print(f"\n결과 저장: {out}")


if __name__ == "__main__":
    main()
