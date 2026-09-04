"""
이동된 파일의 본문 sha256를 raw 시점 hash와 재대조하여 무결성 검증.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MOVES = json.loads(Path(r"H:\내 드라이브\9.작업중/클로드\_ocr_extracted_통합_매니페스트_2026-04-30_moves.json").read_text(encoding="utf-8"))


def strip_yaml(text):
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:]
    return text


def fingerprint(body):
    body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL)
    body = re.sub(r'^---+$', '', body, flags=re.MULTILINE)
    body = re.sub(r'^#+\s.*$', '', body, flags=re.MULTILINE)
    body = re.sub(r'^\s*[-*]\s+', '', body, flags=re.MULTILINE)
    chars = re.findall(r'[가-힣A-Za-z0-9]+', body)
    return "".join(chars)


# 송영곤 사례 폴더 보정 후 위치 재계산
MOVED_AGAIN = {
    "송영곤_사례연습_가족_26_p0051-0089.md": r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_가족\송영곤_사례연습_가족_26_p0051-0089.md",
    "송영곤_사례연습_담보_26_p0051-0100.md": r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_담보\송영곤_사례연습_담보_26_p0051-0100.md",
    "송영곤_사례연습_담보_26_p0101-0125.md": r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_담보\송영곤_사례연습_담보_26_p0101-0125.md",
    "송영곤_사례연습_물권_26_p0051-0100.md": r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_물권\송영곤_사례연습_물권_26_p0051-0100.md",
    "송영곤_사례연습_물권_26_p0101-0150.md": r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_물권\송영곤_사례연습_물권_26_p0101-0150.md",
    "송영곤_사례연습_물권_26_p0151-0171.md": r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_물권\송영곤_사례연습_물권_26_p0151-0171.md",
    "송영곤_사례연습_민총_26_p0051-0100.md": r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_민총\송영곤_사례연습_민총_26_p0051-0100.md",
    "송영곤_사례연습_민총_26_p0101-0150.md": r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_민총\송영곤_사례연습_민총_26_p0101-0150.md",
    "송영곤_사례연습_민총_26_p0151-0153.md": r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_민총\송영곤_사례연습_민총_26_p0151-0153.md",
}

ok = 0
mismatch = 0
missing = 0
mismatches = []
for m in MOVES:
    cls = m["classification"]
    if cls == "A":
        # _trash로 이동만
        dst = Path(m["dst"])
        if dst.exists():
            ok += 1
        else:
            missing += 1
            print(f"[MISSING A] {dst}")
        continue
    expected_hash = m["raw_hash"]
    dst_path = Path(m["dst"])
    # 송영곤 사례_가족/담보/물권/민총 보정: _재추출/ → root로 옮겨졌을 수 있음
    if not dst_path.exists() and dst_path.parent.name == "_재추출":
        alt = dst_path.parent.parent / dst_path.name
        if alt.exists():
            dst_path = alt
    if not dst_path.exists():
        missing += 1
        print(f"[MISSING] {dst_path}")
        continue
    text = dst_path.read_text(encoding="utf-8", errors="replace")
    body = strip_yaml(text)
    actual_hash = hashlib.sha256(fingerprint(body).encode()).hexdigest()
    if actual_hash == expected_hash:
        ok += 1
    else:
        mismatch += 1
        mismatches.append({
            "file": str(dst_path),
            "expected": expected_hash[:16],
            "actual": actual_hash[:16],
        })
        print(f"[MISMATCH] {dst_path.name}")

print(f"\n총 {len(MOVES)}건  OK: {ok}  MISMATCH: {mismatch}  MISSING: {missing}")

# 보고서 저장
report = {
    "total": len(MOVES),
    "ok": ok,
    "mismatch": mismatch,
    "missing": missing,
    "mismatches": mismatches,
}
Path(r"H:\내 드라이브\9.작업중/클로드\_ocr_extracted_sha256_검증_2026-04-30.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
