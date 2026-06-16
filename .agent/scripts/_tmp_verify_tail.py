"""재생성 노트 끝 20줄과 원본 재정제 끝 20줄 비교 결과를 JSON으로 저장."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"H:\내 드라이브\.agent\scripts")
from fix_ocr_hanja import process_line as hanja_process
from fix_ocr_spacing import process_line as spacing_process


def process_extract(extract_path: Path) -> str:
    text = extract_path.read_text(encoding="utf-8")
    text = re.sub(r"^--- Page (\d+) ---$", lambda m: f"<!-- p.{m.group(1)} -->", text, flags=re.MULTILINE)
    cleaned = []
    for line in text.splitlines():
        line, _ = hanja_process(line)
        line, _ = spacing_process(line)
        cleaned.append(line)
    return "\n".join(cleaned)


def body_of_note(note_path: Path) -> str:
    text = note_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    if m:
        text = text[m.end():]
    text = re.sub(r"^#[^\n]*\n", "", text, count=1)
    return text.lstrip("\n").rstrip()


def compare(note_path: Path, extract_path: Path) -> dict:
    expected = process_extract(extract_path).rstrip()
    got = body_of_note(note_path)

    expected_lines = expected.split("\n")
    got_lines = got.split("\n")

    tail_n = 20
    expected_tail = expected_lines[-tail_n:]
    got_tail = got_lines[-tail_n:]

    return {
        "note": note_path.name,
        "extract": extract_path.name,
        "expected_total_lines": len(expected_lines),
        "got_total_lines": len(got_lines),
        "tail_match": expected_tail == got_tail,
        "expected_tail": expected_tail,
        "got_tail": got_tail,
    }


note = Path(r"H:\내 드라이브\sync\_교재원문\민법\윤동환_민법의맥\기출분석_법원행정고시_본3_윤동환_민법의맥.md")
extract = Path(r"H:\내 드라이브\.agent\data\exam_extracts\1-1_민법_윤동환_민법의맥_(교재)_p031-060.md")
result = compare(note, extract)

out = Path(r"H:\내 드라이브\.agent\state\_tmp_tail_compare.json")
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"저장: {out}")
print(f"expected_total={result['expected_total_lines']}  got_total={result['got_total_lines']}  tail_match={result['tail_match']}")
