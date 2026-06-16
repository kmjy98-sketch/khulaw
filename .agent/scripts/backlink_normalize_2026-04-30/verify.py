"""
백링크 변환 검증 스크립트 (2026-05-05)

검증 방법 (semantic equivalence):
1. 각 변경 파일에 대해 backup vs current 비교
2. backup 파일에 convert.py 로직 재적용 → current와 md5 동등성 확인
3. 등가가 아니면 [확인필요]로 보고

사용:
  python verify.py --zone L2_민법
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime

import convert as C

SYNC = C.SYNC
BACKUP_ROOT = C.BACKUP_ROOT


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def reapply_convert_text(text: str) -> str:
    """convert.py와 동일한 변환을 텍스트에 적용 (파일 I/O 없이)"""
    fm, body = C.split_frontmatter(text)
    masked, placeholders = C.mask_protected_regions(body)
    new_body, _, _ = C.convert_phase_a(masked)
    new_body, _, _ = C.convert_phase_b(new_body)
    new_body = C.unmask(new_body, placeholders)
    return fm + new_body


def verify_zone(zone: str) -> dict:
    """zone 내 backup이 있는 모든 파일 검증"""
    # zone 별 백업 루트
    zone_subdir = zone.replace("L2_", "").replace("L3_", "")
    backup_dirs = []
    if zone.startswith("L2_"):
        backup_dirs.append(BACKUP_ROOT / zone_subdir)
    elif zone.startswith("L3_"):
        backup_dirs.append(BACKUP_ROOT / zone_subdir)

    results = {
        "zone": zone,
        "verified": 0,
        "match": 0,
        "mismatch": 0,
        "missing_current": 0,
        "mismatches": [],
    }

    for bdir in backup_dirs:
        if not bdir.exists():
            continue
        for bp in bdir.rglob("*.md"):
            rel = bp.relative_to(BACKUP_ROOT)
            current = SYNC / rel
            if not current.exists():
                results["missing_current"] += 1
                results["mismatches"].append({
                    "file": str(rel),
                    "reason": "current file missing",
                })
                continue
            try:
                backup_text = bp.read_text(encoding="utf-8")
                current_text = current.read_text(encoding="utf-8")
            except Exception as e:
                results["mismatches"].append({
                    "file": str(rel),
                    "reason": f"read error: {e}",
                })
                continue

            backup_md5 = md5(backup_text.encode("utf-8"))
            current_md5 = md5(current_text.encode("utf-8"))

            # 변환 후 결과 (backup → reapply)
            expected_text = reapply_convert_text(backup_text)
            expected_md5 = md5(expected_text.encode("utf-8"))

            results["verified"] += 1
            if expected_md5 == current_md5:
                results["match"] += 1
            else:
                results["mismatch"] += 1
                # 첫 200자 차이 위치 찾기
                diff_pos = -1
                for i, (a, b) in enumerate(zip(expected_text, current_text)):
                    if a != b:
                        diff_pos = i
                        break
                results["mismatches"].append({
                    "file": str(rel),
                    "backup_md5": backup_md5,
                    "current_md5": current_md5,
                    "expected_md5": expected_md5,
                    "first_diff_pos": diff_pos,
                    "expected_snippet": expected_text[max(0,diff_pos-30):diff_pos+60] if diff_pos >= 0 else "",
                    "current_snippet": current_text[max(0,diff_pos-30):diff_pos+60] if diff_pos >= 0 else "",
                })

    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--zone", required=True)
    args = p.parse_args()

    res = verify_zone(args.zone)

    print(f"=== VERIFY {args.zone} ===")
    print(f"verified: {res['verified']}")
    print(f"  match:    {res['match']}")
    print(f"  mismatch: {res['mismatch']}")
    print(f"  missing:  {res['missing_current']}")

    if res["mismatch"] or res["missing_current"]:
        print("\n불일치 사례 (최대 10개):")
        for m in res["mismatches"][:10]:
            print(f"  - {m['file']}")
            if 'reason' in m:
                print(f"    reason: {m['reason']}")
            elif 'first_diff_pos' in m:
                print(f"    diff_pos={m['first_diff_pos']}")
                print(f"    expected: ...{m['expected_snippet']!r}...")
                print(f"    current : ...{m['current_snippet']!r}...")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"verify_{args.zone}_{ts}.json"
    log_path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n로그: {log_path}")

    sys.exit(0 if res["mismatch"] == 0 and res["missing_current"] == 0 else 1)


if __name__ == "__main__":
    main()
