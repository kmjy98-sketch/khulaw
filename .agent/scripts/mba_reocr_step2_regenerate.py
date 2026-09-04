"""Step 2-3: 원본 추출에서 정제된 본문을 생성해 노트 재작성.

동작:
  1. 매핑된 원본 추출을 읽음.
  2. `--- Page NNN ---` 마커 → `<!-- p.NNN -->` 주석으로 변환.
  3. 한자/띄어쓰기/줄바꿈 정리 스크립트를 인메모리로 적용.
  4. 원 노트의 frontmatter + 제목 라인 유지하고 본문만 새로 쓴 내용으로 대체.
  5. 원 노트는 _trash/{date}/mba_reocr/{파일명} 에 백업.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

# 기존 스크립트 모듈 로드 (자기 디렉터리 = .agent/scripts)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

from fix_ocr_hanja import process_line as hanja_process  # type: ignore
from fix_ocr_spacing import process_line as spacing_process  # type: ignore

MAPPING = Path(vp(".agent", "state", "mba_reocr_mapping.json"))
NOTES_DIR = Path(vp("sync", "_교재원문", "민법", "윤동환_민법의맥"))
EXTRACTS_DIR = Path(vp(".agent", "data", "exam_extracts"))
WORKSPACE_ROOT = Path(VAULT_ROOT)
TRASH_DIR = WORKSPACE_ROOT / "5.기타" / "_trash" / date.today().isoformat() / "mba_reocr"

FM_RE = re.compile(r"^(---\n.*?\n---\n)(.*)", re.DOTALL)
TITLE_RE = re.compile(r"^(# [^\n]*\n)", re.MULTILINE)
PAGE_MARKER_RE = re.compile(r"^--- Page (\d+) ---$", re.MULTILINE)


def clean_extract_body(text: str) -> str:
    """원본 추출 본문을 정제 (페이지 마커 변환 + hanja/spacing 적용)."""
    # 1. `--- Page NNN ---` → `<!-- p.NNN -->`
    text = PAGE_MARKER_RE.sub(lambda m: f"<!-- p.{m.group(1)} -->", text)
    # 2. 라인 단위로 hanja + spacing 적용
    new_lines = []
    for line in text.splitlines(keepends=False):
        line, _ = hanja_process(line)
        line, _ = spacing_process(line)
        new_lines.append(line)
    return "\n".join(new_lines)


def regenerate_note(note_path: Path, extract_path: Path) -> dict:
    """한 노트를 재생성. 결과 통계 반환."""
    orig_content = note_path.read_text(encoding="utf-8")
    fm_match = FM_RE.match(orig_content)
    if not fm_match:
        return {"error": "no_frontmatter"}
    frontmatter = fm_match.group(1)
    rest = fm_match.group(2)
    # 원 노트의 제목 라인 추출 (있다면)
    title_match = TITLE_RE.match(rest)
    title_line = title_match.group(1) if title_match else ""

    # 원본 추출 정제
    extract_text = extract_path.read_text(encoding="utf-8")
    cleaned_body = clean_extract_body(extract_text)

    # 새 노트: frontmatter + 제목 + \n + 정제 본문
    new_content = frontmatter + "\n" + title_line + ("\n" if title_line else "") + cleaned_body
    # 끝에 newline 보장
    if not new_content.endswith("\n"):
        new_content += "\n"

    orig_lines = orig_content.count("\n")
    new_lines_count = new_content.count("\n")

    # 백업
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    backup = TRASH_DIR / note_path.name
    if not backup.exists():
        shutil.copy2(note_path, backup)
    note_path.write_text(new_content, encoding="utf-8")

    return {
        "orig_lines": orig_lines,
        "new_lines": new_lines_count,
        "backup": str(backup.relative_to(WORKSPACE_ROOT)),
    }


def main():
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))

    results = []
    for m in mapping:
        note_path = NOTES_DIR / m["note"]
        if not note_path.exists():
            results.append({"note": m["note"], "status": "note_missing"})
            continue

        candidates = m.get("candidate_extracts", [])
        if not candidates:
            results.append({"note": m["note"], "status": "no_extract_candidate"})
            continue

        # 첫 번째 후보 사용 (서브책자 prefix 우선)
        extract_name = candidates[0]
        extract_path = EXTRACTS_DIR / extract_name
        if not extract_path.exists():
            results.append({"note": m["note"], "status": "extract_missing", "candidate": extract_name})
            continue

        stat = regenerate_note(note_path, extract_path)
        stat["note"] = m["note"]
        stat["extract"] = extract_name
        stat["status"] = "regenerated"
        results.append(stat)

    print(f"총 {len(results)}건 처리")
    ok = sum(1 for r in results if r.get("status") == "regenerated")
    print(f"재생성 성공: {ok}건")
    print()
    for r in results:
        status = r.get("status", "?")
        name = r.get("note", "?")
        if status == "regenerated":
            print(f"  [OK] {name}  {r['orig_lines']}→{r['new_lines']}행  ({r.get('extract','?')})")
        else:
            print(f"  [{status}] {name}  {r.get('candidate','')}")

    # 결과 저장
    result_path = Path(vp(".agent", "state", "mba_reocr_result.json"))
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 상세: {result_path}")


if __name__ == "__main__":
    main()
