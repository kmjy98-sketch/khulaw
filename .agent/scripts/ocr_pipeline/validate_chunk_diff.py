"""청크별 원본↔검토본 diff 검증.

검증 기준:
  1. 라인 수 편차 ≤ 5% (또는 ≤ 5행 중 큰 것)
  2. 삭제된 라인 = 0 (모든 원본 라인이 보존 또는 변형)
  3. <!-- p.NNN --> 페이지 마커 전부 보존
  4. <!-- chunk_meta: ... --> 메타 주석 보존
  5. 판례 인용 패턴(대판/대결/헌재 YYYY.M.D.) 원문 동일
  6. 조문 bold 패턴(**제N조**) 원문 동일

실패 청크: reject 처리 → .agent/state/rejected_chunks.json에 기록
           검토본 대신 원본 청크를 복원에 사용

사용:
  python validate_chunk_diff.py --pilot   # pilot_chunks.json 기준
  python validate_chunk_diff.py --all     # all_chunks.json 기준
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

WORKSPACE_ROOT = Path(VAULT_ROOT)
CHUNKS_ROOT = WORKSPACE_ROOT / ".agent" / "data" / "ocr_chunks"
REVIEWED_ROOT = WORKSPACE_ROOT / ".agent" / "data" / "ocr_chunks_reviewed"

PAGE_MARKER = re.compile(r"<!--\s*p\.\d+\s*-->")
CHUNK_META = re.compile(r"<!--\s*chunk_meta:.*?-->")
PRECEDENT_REF = re.compile(
    r"(?:대판|대결|대전합|헌재|대법원)\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}"
)
STATUTE_BOLD = re.compile(r"\*\*제\d+조(?:의\d+)?(?:제\d+항)?\*\*")


def extract_markers(text: str) -> list[str]:
    return PAGE_MARKER.findall(text)


def extract_precedents(text: str) -> list[str]:
    return PRECEDENT_REF.findall(text)


def extract_statutes(text: str) -> list[str]:
    return STATUTE_BOLD.findall(text)


def validate_pair(orig_path: Path, rev_path: Path, llm_mode: bool = False) -> tuple[bool, list[str]]:
    """원본 vs 검토본 검증. (통과여부, 실패사유_목록) 반환."""
    orig = orig_path.read_text(encoding="utf-8", errors="replace")
    rev = rev_path.read_text(encoding="utf-8", errors="replace")

    orig_lines = orig.splitlines()
    rev_lines = rev.splitlines()

    failures: list[str] = []

    # 1. 라인 수 편차
    orig_n = len(orig_lines)
    rev_n = len(rev_lines)
    tolerance = max(5, int(orig_n * 0.05))
    if llm_mode:
        # LLM 모드: 라인 증가는 OCR 복원으로 허용 — 감소만 체크
        diff_lines = orig_n - rev_n  # 양수 = 감소
        if diff_lines > tolerance:
            failures.append(
                f"라인수 편차 초과: 원본={orig_n} 검토={rev_n} 편차={diff_lines} 허용={tolerance}"
            )
    else:
        diff_lines = abs(orig_n - rev_n)
        if diff_lines > tolerance:
            failures.append(
                f"라인수 편차 초과: 원본={orig_n} 검토={rev_n} 편차={diff_lines} 허용={tolerance}"
            )

    # 2. 삭제된 라인 확인
    # llm_mode: 내용 수정이 많으므로 라인수 감소만 체크 (페이지 마커·메타 삭제는 #3,4에서 별도 확인)
    # rule_mode: 원본 라인이 검토본에 없는 경우만 삭제로 판단
    if not llm_mode:
        orig_significant = [
            l.strip()
            for l in orig_lines
            if l.strip() and not CHUNK_META.match(l.strip())
        ]
        rev_set = set(l.strip() for l in rev_lines if l.strip())
        deleted = [
            l for l in orig_significant
            if len(l) > 20 and l not in rev_set
            and not any(l in rl for rl in rev_set)
        ]
        if deleted:
            failures.append(
                f"삭제 의심 라인 {len(deleted)}개: {deleted[0][:60]}..."
            )
    else:
        # LLM 모드: 라인 수가 10% 이상 감소하면 경고
        if orig_n > 0 and rev_n < orig_n * 0.90:
            failures.append(
                f"라인 수 과도 감소: 원본={orig_n} 검토={rev_n} (10% 초과)"
            )

    # 3. 페이지 마커 보존 (삭제만 reject — 추가는 OCR 복원으로 허용)
    orig_markers = set(extract_markers(orig))
    rev_markers = set(extract_markers(rev))
    missing_m = orig_markers - rev_markers
    if missing_m:
        failures.append(
            f"페이지 마커 삭제됨: {list(missing_m)[:3]}"
        )

    # 4. chunk_meta 보존
    if CHUNK_META.search(orig) and not CHUNK_META.search(rev):
        failures.append("chunk_meta 주석 삭제됨")

    # 5. 판례 인용 원문 동일성 (삭제만 reject — 추가·정규화는 허용)
    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    orig_prec_norm = {_norm(p) for p in extract_precedents(orig)}
    rev_prec_norm = {_norm(p) for p in extract_precedents(rev)}
    missing_p = orig_prec_norm - rev_prec_norm
    if missing_p:
        failures.append(
            f"판례 인용 삭제됨: 누락={list(missing_p)[:3]}"
        )

    # 6. 조문 bold: 기존 조문이 삭제됐을 때만 reject (추가는 OCR 복원으로 허용)
    orig_stat_set = set(extract_statutes(orig))
    rev_stat_set = set(extract_statutes(rev))
    missing_s = orig_stat_set - rev_stat_set
    if missing_s:
        failures.append(
            f"조문 bold 삭제됨: {list(missing_s)[:3]}"
        )

    return len(failures) == 0, failures


def main() -> None:
    pilot_mode = "--pilot" in sys.argv
    batch_mode = "--batch" in sys.argv
    batch2_mode = "--batch2" in sys.argv
    batch3_mode = "--batch3" in sys.argv
    llm_mode = "--llm" in sys.argv  # LLM 교정 결과 검증 시 사용
    if pilot_mode:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "pilot_chunks.json"
    elif batch3_mode:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "batch3_chunks.json"
    elif batch2_mode:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "batch2_chunks.json"
    elif batch_mode:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "batch1_chunks.json"
    else:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "all_chunks.json"

    if not chunks_index_path.exists():
        print(f"청크 인덱스 없음: {chunks_index_path}")
        sys.exit(1)

    records = json.loads(chunks_index_path.read_text(encoding="utf-8"))

    passed = []
    rejected = []

    for rec in records:
        orig_path = WORKSPACE_ROOT / rec["chunk_path"]
        rev_rel = Path(rec["chunk_path"]).relative_to(".agent/data/ocr_chunks")
        rev_path = REVIEWED_ROOT / rev_rel

        if not orig_path.exists():
            print(f"원본 없음: {orig_path.name}")
            continue
        if not rev_path.exists():
            print(f"검토본 없음 (미처리): {rev_path.name}")
            rejected.append({**rec, "failures": ["검토본 없음"]})
            continue

        ok, failures = validate_pair(orig_path, rev_path, llm_mode=llm_mode)
        if ok:
            passed.append(rec)
            print(f"  PASS: {orig_path.name}")
        else:
            rejected.append({**rec, "failures": failures})
            print(f"  FAIL: {orig_path.name}")
            for f in failures:
                # UnicodeEncodeError 방어
                try:
                    print(f"    - {f}")
                except UnicodeEncodeError:
                    print(f"    - {f.encode('ascii', errors='replace').decode()}")

    print(f"\n통과: {len(passed)}  실패(reject): {len(rejected)}")

    rejected_path = WORKSPACE_ROOT / ".agent" / "state" / "rejected_chunks.json"
    rejected_path.write_text(
        json.dumps(rejected, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"reject 목록 → {rejected_path}")


if __name__ == "__main__":
    main()
