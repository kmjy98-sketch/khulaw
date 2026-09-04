#!/usr/bin/env python3
"""
Mark a corrected transcript part as completed and trigger follow-up hooks.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from correction_state import COR_SUFFIX, derive_state, merge_mode_files

ROOT = Path(__file__).resolve().parents[4]
STATE_DIR = ROOT / ".agent" / "state"
LOG_PATH = STATE_DIR / "transcription_log.json"
PROGRESS_SCRIPT = ROOT / ".agent" / "skills" / "progress-tracker" / "scripts" / "progress.py"
INDEX_SCRIPT = ROOT / ".agent" / "skills" / "auto-index" / "scripts" / "update_index.py"


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_log() -> dict:
    if LOG_PATH.exists():
        with open(LOG_PATH, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    return {}


def save_log(data: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=4)


def normalize_part(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"part[_-]?(\d+)", value, re.IGNORECASE)
    if not match:
        return None
    return f"part{int(match.group(1)):02d}"


def infer_transcript_path(corrected_path: Path, explicit_path: str | None) -> Path | None:
    if explicit_path:
        candidate = Path(explicit_path)
        return candidate if candidate.exists() else None

    candidates = sorted(corrected_path.parent.glob("*_transcript.txt"))
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    stem = corrected_path.stem
    for suffix in ("_corr_merged", "_교정본_통합", "_corr", "_교정", "_corrected"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    stem = re.sub(r"_part\d+$", "", stem, flags=re.IGNORECASE)

    for candidate in candidates:
        raw_stem = candidate.stem.replace("_transcript", "")
        if raw_stem == stem:
            return candidate
    return candidates[0]


def find_log_key(log_data: dict, transcript_path: Path, corrected_path: Path) -> str:
    transcript_str = str(transcript_path)
    if transcript_str in log_data:
        return transcript_str

    corrected_dir = str(corrected_path.parent)
    for key, value in log_data.items():
        if value.get("original_path") == transcript_str:
            return key
        if value.get("split_dir") == corrected_dir and Path(key).name == transcript_path.name:
            return key
    return transcript_str


def append_note(existing: str, new_note: str | None) -> str:
    if not new_note:
        return existing
    if not existing:
        return new_note
    if new_note in existing:
        return existing
    return f"{existing}\n{new_note}"


def run_hook(command: list[str], dry_run: bool) -> bool:
    if dry_run:
        print(f"[DRY-RUN] {' '.join(command)}")
        return True

    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode == 0:
        if result.stdout.strip():
            print(result.stdout.strip())
        return True

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return False


def collect_mode_files(corrected_path: Path, sync_dir: bool) -> list[str]:
    if sync_dir:
        return [str(path) for path in sorted(corrected_path.parent.glob(f"*{COR_SUFFIX}"))]
    return [str(corrected_path)]


def main() -> int:
    configure_stdio()

    parser = argparse.ArgumentParser(description="전사문 교정 완료 상태 반영")
    parser.add_argument("corrected_file", help="교정 완료된 파일 경로")
    parser.add_argument("--transcript", help="원본 transcript.txt 경로")
    parser.add_argument("--part", help="명시적 part 번호 (예: part01)")
    parser.add_argument("--note", help="로그에 남길 메모")
    parser.add_argument("--mode", choices=("reviewed", "generated"), default="reviewed", help="교정 반영 모드")
    parser.add_argument("--sync-dir", action="store_true", help="같은 폴더의 모든 *_corr.md를 함께 반영")
    parser.add_argument("--skip-progress", action="store_true", help="progress.py 호출 생략")
    parser.add_argument("--skip-index", action="store_true", help="update_index.py 호출 생략")
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 계획만 출력")
    args = parser.parse_args()

    corrected_path = Path(args.corrected_file)
    if not corrected_path.exists():
        print(f"교정 파일을 찾을 수 없습니다: {corrected_path}")
        return 1

    transcript_path = infer_transcript_path(corrected_path, args.transcript)
    if transcript_path is None:
        print("원본 transcript.txt를 찾을 수 없습니다. --transcript로 지정하세요.")
        return 1

    log_data = load_log()
    log_key = find_log_key(log_data, transcript_path, corrected_path)
    existing = log_data.get(log_key, {})
    mode_files = collect_mode_files(corrected_path, sync_dir=args.sync_dir)
    generated_files, reviewed_files = merge_mode_files(
        existing,
        corrected_path.parent,
        args.mode,
        mode_files,
    )
    state_info = derive_state(
        existing,
        corrected_path.parent,
        generated_files=generated_files,
        reviewed_files=reviewed_files,
    )

    note_text = append_note(existing.get("notes", ""), args.note)
    latest_reviewed = reviewed_files[-1] if reviewed_files else None
    updated_entry = {
        "corrected": state_info["corrected"],
        "correction_state": state_info["correction_state"],
        "corrected_file": latest_reviewed,
        "corrected_files": reviewed_files,
        "reviewed_files": reviewed_files,
        "generated_files": generated_files,
        "duplicate_of": state_info["duplicate_of"],
        "duplicate_reason": state_info["duplicate_reason"],
        "notes": note_text,
        "original_path": existing.get("original_path", str(transcript_path)),
        "split_dir": existing.get("split_dir", str(corrected_path.parent)),
        "raw_path": existing.get("raw_path", str(transcript_path)),
        "part_count": state_info["part_count"],
        "expected_total": state_info["expected_total"],
        "stale_reason": state_info["stale_reason"],
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    log_data[log_key] = updated_entry

    part = normalize_part(args.part) or normalize_part(corrected_path.stem)

    print(f"원본 전사문: {transcript_path}")
    print(f"교정 파일: {corrected_path}")
    print(f"로그 키: {log_key}")
    print(f"모드: {args.mode}")
    print(f"상태: {state_info['correction_state']}")
    print(f"리뷰 파일 수: {len(reviewed_files)} / {state_info['expected_total']}")
    print(f"자동생성 파일 수: {len(generated_files)}")
    if part:
        print(f"파트: {part}")
    else:
        print("파트: 확인 불가")

    if args.dry_run:
        print(json.dumps(updated_entry, ensure_ascii=False, indent=2))
    else:
        save_log(log_data)
        print(f"전사 로그 업데이트 완료: {LOG_PATH}")

    if not state_info["corrected"]:
        print("완료 판정이 아니어서 후속 훅을 건너뜁니다.")
        return 0

    if not args.skip_progress and part:
        progress_cmd = [sys.executable, str(PROGRESS_SCRIPT), "--complete", part, "--type", "transcript"]
        if not run_hook(progress_cmd, args.dry_run):
            print("진도 업데이트 실패")
    elif not part and not args.skip_progress:
        print("파트를 읽지 못해 진도 업데이트를 건너뜁니다.")

    if not args.skip_index:
        index_cmd = [sys.executable, str(INDEX_SCRIPT), str(corrected_path)]
        if not run_hook(index_cmd, args.dry_run):
            print("인덱스 업데이트 실패")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
