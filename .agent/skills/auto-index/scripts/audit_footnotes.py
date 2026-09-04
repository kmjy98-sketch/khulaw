#!/usr/bin/env python3
"""
audit_footnotes.py — 옵시디언 볼트 각주 무결성 감사

기능:
  1. 고아 참조 탐지: [^id] 참조가 있으나 정의 없음
  2. 고아 정의 탐지: 정의가 있으나 참조 없음
  3. 인접 페이지 마커에서 각주 정의 후보 제안
  4. 출력: .agent/state/footnote_audit.json
"""

import json
import re
import os
import sys
from pathlib import Path

_p = os.path.abspath(__file__)
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, 'scripts'))
from _vault import VAULT_ROOT, vp  # noqa: E402

# 볼트 경로
BASE = Path(VAULT_ROOT)
VAULTS = [
    BASE / "_4과목_도표추가본_통합본_모음",
    BASE / "_기말_도표추가본_통합본_모음",
]
OUTPUT = BASE / ".agent/state/footnote_audit.json"

# 정규식
RE_REF = re.compile(r"\[\^([^\]]+)\](?!:)")  # [^id] 참조 (정의 아닌 것)
RE_DEF = re.compile(r"^\[\^([^\]]+)\]:", re.MULTILINE)  # [^id]: 정의
RE_PAGE_MARKER = re.compile(
    r"<!--\s*📖\s*교재별\s*페이지\s*\n(.*?)-->", re.DOTALL
)
RE_HEADING2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def find_nearest_page_marker(lines: list[str], ref_line_idx: int) -> str | None:
    """ref_line_idx 위의 가장 가까운 페이지 마커에서 첫 번째 교재+페이지 추출."""
    for i in range(ref_line_idx - 1, -1, -1):
        if "📖" in lines[i] and "교재별 페이지" in lines[i]:
            # 마커 블록 수집
            block = []
            for j in range(i, min(i + 10, len(lines))):
                block.append(lines[j])
                if "-->" in lines[j]:
                    break
            text = "\n".join(block)
            # 첫 번째 교재 라인에서 추출
            for line in block:
                line = line.strip().lstrip("-").strip()
                if line and not line.startswith("<!--") and not line.startswith("-->") and "📖" not in line:
                    return line  # e.g., "기본민강(1-01) ch.1 p.13-42"
    return None


def audit_file(filepath: Path) -> dict:
    """단일 파일의 각주 감사 수행."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")
    fname = filepath.name

    # 참조 수집
    refs = {}
    for i, line in enumerate(lines):
        for m in RE_REF.finditer(line):
            ref_id = m.group(1)
            if ref_id not in refs:
                refs[ref_id] = i + 1  # 1-indexed

    # 정의 수집
    defs = {}
    for i, line in enumerate(lines):
        m = RE_DEF.match(line)
        if m:
            def_id = m.group(1)
            defs[def_id] = i + 1

    # 고아 참조
    orphan_refs = []
    for ref_id, line_num in refs.items():
        if ref_id not in defs:
            suggested = find_nearest_page_marker(lines, line_num - 1)
            entry = {
                "file": fname,
                "line": line_num,
                "ref_id": ref_id,
            }
            if suggested:
                entry["suggested_def"] = suggested
            orphan_refs.append(entry)

    # 고아 정의
    orphan_defs = []
    for def_id, line_num in defs.items():
        if def_id not in refs:
            orphan_defs.append({
                "file": fname,
                "line": line_num,
                "def_id": def_id,
            })

    return {
        "file": fname,
        "total_refs": len(refs),
        "total_defs": len(defs),
        "orphan_refs": orphan_refs,
        "orphan_defs": orphan_defs,
    }


def main():
    all_orphan_refs = []
    all_orphan_defs = []
    total_refs = 0
    total_defs = 0
    file_reports = []

    for vault in VAULTS:
        if not vault.exists():
            continue
        for md_file in sorted(vault.glob("**/*.md")):
            report = audit_file(md_file)
            file_reports.append(report)
            total_refs += report["total_refs"]
            total_defs += report["total_defs"]
            all_orphan_refs.extend(report["orphan_refs"])
            all_orphan_defs.extend(report["orphan_defs"])

    result = {
        "orphan_refs": all_orphan_refs,
        "orphan_defs": all_orphan_defs,
        "file_reports": file_reports,
        "summary": {
            "total_refs": total_refs,
            "total_defs": total_defs,
            "orphan_refs": len(all_orphan_refs),
            "orphan_defs": len(all_orphan_defs),
            "files_scanned": len(file_reports),
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"감사 완료: {len(file_reports)}개 파일, "
          f"고아 참조 {len(all_orphan_refs)}개, 고아 정의 {len(all_orphan_defs)}개")
    print(f"결과: {OUTPUT}")


if __name__ == "__main__":
    main()
