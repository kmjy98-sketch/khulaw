"""OCR 정리 파이프라인 오케스트레이터.

파일럿:
  python run_pipeline.py --pilot [--dry-run]
  → index → 파일럿 20개 선정 → split → sonnet review → validate → (dry-run이면 중단)
  → merge_and_apply

전면 (파일럿 승인 후):
  python run_pipeline.py --all
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent
PYTHON = sys.executable


def run(script: str, *args: str) -> int:
    cmd = [PYTHON, str(SCRIPTS / script), *args]
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main() -> None:
    pilot = "--pilot" in sys.argv
    dry_run = "--dry-run" in sys.argv
    run_all = "--all" in sys.argv

    if not pilot and not run_all:
        print("옵션 필요: --pilot | --all")
        sys.exit(1)

    if pilot:
        # 1. 인덱싱 + 파일럿 선정
        rc = run("index_all_files.py", "--pilot")
        if rc != 0:
            sys.exit(rc)

        # 2. 청크 분할
        rc = run("split_to_chunks.py", "--pilot")
        if rc != 0:
            sys.exit(rc)

        # 3. Sonnet 검토 (실시간 API)
        rc = run("review_chunk_sonnet.py", "--pilot")
        if rc != 0:
            sys.exit(rc)

        # 4. diff 검증
        rc = run("validate_chunk_diff.py", "--pilot")
        if rc != 0:
            sys.exit(rc)

        if dry_run:
            # 5. dry-run 병합 (실제 교체 안 함)
            run("merge_and_apply.py", "--pilot", "--dry-run")
            print("\n[파일럿 DRY-RUN 완료] 검토 후 --pilot 없이 merge_and_apply.py 실행")
        else:
            print("\n파일럿 결과를 확인한 후 merge_and_apply.py --pilot 을 실행하세요.")
            print("  python merge_and_apply.py --pilot")

    elif run_all:
        print("전면 실행은 파일럿 승인 후 단계별로 진행합니다.")
        print("  1. python index_all_files.py")
        print("  2. python split_to_chunks.py")
        print("  3. python review_chunk_sonnet.py --all  (Batches API)")
        print("  4. python validate_chunk_diff.py --all")
        print("  5. python merge_and_apply.py --all")
        sys.exit(0)


if __name__ == "__main__":
    main()
