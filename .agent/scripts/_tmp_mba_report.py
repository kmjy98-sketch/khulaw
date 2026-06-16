"""민법의맥 재-OCR 대상 상세 보고."""
import json
from pathlib import Path

OUT = Path(r"H:\내 드라이브\.agent\state\mba_reocr_report.txt")

reocr = json.loads(Path(r"H:\내 드라이브\.agent\state\reocr_targets.json").read_text(encoding="utf-8"))
mba = [d for d in reocr if "민법의맥" in d.get("file", "")]

# 현재 민법의맥 전체 파일 개수
current_dir = Path(r"H:\내 드라이브\sync\_교재원문\민법\윤동환_민법의맥")
total_current = sum(1 for f in current_dir.glob("*.md"))

# 원본 추출 파일
extract_dir = Path(r"H:\내 드라이브\.agent\data\exam_extracts")
extract_files = sorted(f for f in extract_dir.glob("*민법의맥*교재*.md"))

lines = []
lines.append("=" * 70)
lines.append("민법의맥 (윤동환) OCR 재추출 조사 보고")
lines.append("=" * 70)
lines.append("")
lines.append(f"현재 노트: {total_current}개 파일 (sync/_교재원문/민법/윤동환_민법의맥/)")
lines.append(f"원본 추출: {len(extract_files)}개 페이지 청크 (.agent/data/exam_extracts/)")
lines.append(f"  범위: {extract_files[0].name if extract_files else '?'}")
lines.append(f"       ~ {extract_files[-1].name if extract_files else '?'}")
lines.append("")
lines.append(f"OCR 깨짐 의심 노트: {len(mba)}개")
lines.append("")
lines.append(f"{'점수':>4} {'행':>5}  파일")
lines.append("-" * 70)
for d in mba:
    fname = Path(d["file"]).name
    lines.append(f"{d['total_artifacts']:>4} {d['total_lines']:>5}  {fname}")

# 원본과의 매핑 - 토픽별 노트는 페이지 범위 명시 없음
lines.append("")
lines.append("문제: 현재 노트는 토픽 기반 (예: '강행규정_위반_무효_본3_윤동환_민법의맥.md'),")
lines.append("     원본 추출은 페이지 기반 (예: '민법의맥_(교재)_p001-030.md').")
lines.append("     직접 매핑 불가 — 노트별 해당 페이지 범위 파악 필요.")
lines.append("")
lines.append("권장 절차:")
lines.append("  1. 재추출 필요 노트 frontmatter에 원본 페이지 범위 추가 (수동)")
lines.append("  2. 페이지 범위 기준으로 raw extract에서 해당 부분 LLM 재처리")
lines.append("  3. diff로 교체 검증 후 commit")
lines.append("")
lines.append("자동화 가능 서브태스크:")
lines.append("  - raw extract에 대한 동일 클린업 스크립트(hanja/spacing/linebreak) 적용")
lines.append("    → 현재 노트와 비교 쉬워짐")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"보고서 저장: {OUT}")
