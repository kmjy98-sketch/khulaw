"""Step 1: 민법의맥 재-OCR 대상 10개 노트 → 원본 추출 파일 매핑.

입력:
  .agent/state/reocr_targets.json  (민법의맥 깨짐 후보)

출력:
  .agent/state/mba_reocr_mapping.json
  각 노트에 대해 {note_path, 서브책자, 원본_chunk, 페이지, candidate_extract_files}
"""

import json
import re
from pathlib import Path

REOCR_TARGETS = Path(r"H:\내 드라이브\.agent\state\reocr_targets.json")
OUT = Path(r"H:\내 드라이브\.agent\state\mba_reocr_mapping.json")
NOTES_DIR = Path(r"H:\내 드라이브\sync\_교재원문\민법\윤동환_민법의맥")
EXTRACTS_DIR = Path(r"H:\내 드라이브\.agent\data\exam_extracts")

# 서브책자별 원본 파일 prefix 매핑 (관찰된 패턴)
SUBBOOK_PREFIX = {
    "교재": "1-1_민법_윤동환_민법의맥_(교재)_",
    "민법의맥": "1-1_민법_윤동환_민법의맥_(교재)_",  # 전체 교재
    "목차": "1-2_민법_윤동환_민법의맥_목차_(교재)_",
    "민총": "1-3_민법_윤동환_민법의맥_민총_(교재)_",
    "물권": "1-4_민법_윤동환_민법의맥_물권_(교재)_",
    "채총": "1-5_민법_윤동환_민법의맥_채총_(교재)_",
    "채각": "1-6_민법_윤동환_민법의맥_채각_(교재)_",
    "친상": "1-7_민법_윤동환_민법의맥_친상_(교재)_",
    "서론": "1-8_민법_윤동환_민법의맥_서론_(교재)_",
    "정리": "2-2_민법_윤동환_민법의맥기초_(정리)_",
    "24_ocr_x": None,  # OCR 실패 청크 — 페이지 범위로 모든 prefix 검색
}

FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    m = FM_RE.match(text)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def find_extracts(subbook: str, page_range: str) -> list[str]:
    """서브책자와 페이지 범위로 원본 추출 파일 후보 반환."""
    # 페이지 범위 파싱 "31-60" → "p031-060"
    m = re.match(r"(\d+)-(\d+)", page_range)
    if not m:
        return []
    start, end = int(m.group(1)), int(m.group(2))
    # 원본 파일명 형식: "...p031-060.md" 또는 "...p0031-0060.md"
    candidates = []
    if subbook == "24_ocr_x":
        # 모든 서브책자 prefix 중 페이지 일치
        for prefix in SUBBOOK_PREFIX.values():
            if prefix is None:
                continue
            for suffix_fmt in [f"p{start:03d}-{end:03d}.md", f"p{start:04d}-{end:04d}.md"]:
                fpath = EXTRACTS_DIR / (prefix + suffix_fmt)
                if fpath.exists():
                    candidates.append(str(fpath.name))
    else:
        prefix = SUBBOOK_PREFIX.get(subbook)
        if prefix:
            for suffix_fmt in [f"p{start:03d}-{end:03d}.md", f"p{start:04d}-{end:04d}.md"]:
                fpath = EXTRACTS_DIR / (prefix + suffix_fmt)
                if fpath.exists():
                    candidates.append(str(fpath.name))
    return candidates


def main():
    reocr = json.loads(REOCR_TARGETS.read_text(encoding="utf-8"))
    mba = [d for d in reocr if "윤동환_민법의맥" in d.get("file", "")]

    mapping = []
    for entry in mba:
        note_path = NOTES_DIR / Path(entry["file"]).name
        if not note_path.exists():
            continue
        content = note_path.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        subbook = fm.get("서브책자", "").strip()
        page_range = fm.get("페이지", "").strip()
        orig_chunk = fm.get("원본_chunk", "").strip()
        extracts = find_extracts(subbook, page_range)
        mapping.append({
            "note": note_path.name,
            "score": entry["total_artifacts"],
            "lines": entry["total_lines"],
            "subbook": subbook,
            "page_range": page_range,
            "original_chunk": orig_chunk,
            "candidate_extracts": extracts,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"매핑 생성: {len(mapping)}건")
    print(f"저장 위치: {OUT}")
    print()
    print("결과 요약:")
    print(f"{'노트':<48} {'서브':<10} {'페이지':<12} {'원본후보'}")
    for m in mapping:
        nname = m["note"][:45]
        subb = m["subbook"][:9]
        pr = m["page_range"][:11]
        cands = ", ".join(m["candidate_extracts"]) or "(미발견)"
        print(f"{nname:<48} {subb:<10} {pr:<12} {cands}")


if __name__ == "__main__":
    main()
