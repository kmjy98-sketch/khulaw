"""
[표복구필요] 라벨 삽입 후 본문 무결성 검증
- 라벨 한 줄만 추가됐고 다른 본문 변경 없는지 sha 비교
"""
import json
import hashlib
import re
from pathlib import Path

ROOT = Path(r"H:\내 드라이브")
LABEL = "<!-- [표복구필요] 표 손상 흔적 검출 (2026-05-05). 원본 PDF 또는 백업 확인 필요. -->"

manifest = json.loads((ROOT / "9.작업중/클로드/표_복구_2026-05-05.json").read_text(encoding="utf-8"))

errors = 0
verified = 0
for x in manifest["label_log"]:
    if x["result"] != "labeled":
        continue
    path = ROOT / x["file"]
    cur = path.read_text(encoding="utf-8")

    # 라벨 1번 등장 검증
    label_count = cur.count(LABEL)
    if label_count != 1:
        print(f"  ERROR: {x['file']} — 라벨 {label_count}개 (예상 1)")
        errors += 1
        continue

    # 라벨 + 직후 \n 제거하여 원본 복원 시도
    # insert_idx 기준으로 직전이 빈 줄이 아니었으면 prefix \n도 추가됐음
    # 가장 안전: 라벨 줄 통째로 빼고 직전·직후 빈 줄 정규화

    # 라벨 줄을 정확히 찾아 제거
    lines = cur.splitlines(keepends=True)
    found = -1
    for i, line in enumerate(lines):
        if line.strip() == LABEL:
            found = i
            break
    if found < 0:
        print(f"  ERROR: {x['file']} — 라벨 줄 못 찾음")
        errors += 1
        continue

    # 라벨 줄 + 직전 prefix \n (있으면) 제거
    new_lines = lines[:]
    del new_lines[found]
    # 직전이 빈 줄이고 직후도 빈 줄이면 직전 빈 줄 제거 (prefix가 추가됐던 경우 복원)
    if found > 0 and found < len(lines) and lines[found - 1].strip() == "" and (found == len(lines) or lines[found].strip() != ""):
        # 그대로 유지
        pass
    # prefix \n 케이스: 라벨 직전이 비어있지 않은 경우에만 prefix가 추가됐을 것
    # 매니페스트 first_damage_line = insert_at_line - prefix_added
    # 단순히 sha_before == 라벨/prefix 제거 후 sha 인지 확인하는 방법
    restored = "".join(new_lines)
    sha_after_remove = hashlib.sha256(restored.encode("utf-8")).hexdigest()

    # prefix 케이스 처리: 라벨 줄 직전에 추가된 빈 줄 제거 케이스
    if found > 0 and lines[found - 1].strip() == "":
        # 직전 빈 줄도 같이 제거 시도
        new_lines2 = lines[:]
        del new_lines2[found]
        del new_lines2[found - 1]
        restored2 = "".join(new_lines2)
        sha_alt = hashlib.sha256(restored2.encode("utf-8")).hexdigest()
        if sha_alt == x["sha_before"]:
            verified += 1
            continue

    if sha_after_remove == x["sha_before"]:
        verified += 1
        continue

    print(f"  MISMATCH: {x['file']}")
    print(f"    sha_before:    {x['sha_before']}")
    print(f"    after_remove:  {sha_after_remove}")
    errors += 1

print()
print(f"=== 검증 결과 ===")
print(f"  검증 성공 (라벨 외 변경 없음): {verified}")
print(f"  에러: {errors}")
