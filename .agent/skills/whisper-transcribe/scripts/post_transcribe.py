#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전사 후처리 자동화 스크립트
Colab 전사 완료 후 실행:
  1. output/ 전사문 감지
  2. 전사문 분할 (transcript-tools)
  3. qmd 재인덱싱 (law-notes 컬렉션, 2026-04-10 LanceDB 대체)
  4. 진도 업데이트 (progress-tracker)

사용법:
  python post_transcribe.py [--dry-run]
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# === 경로 설정 ===
DRIVE_ROOT = Path(r"h:\내 드라이브")
AGENT_DIR = DRIVE_ROOT / ".agent"
SKILLS_DIR = AGENT_DIR / "skills"
LIB_DIR = AGENT_DIR / "lib"

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

INPUT_DIR  = DRIVE_ROOT / "5.기타" / "_inbox" / "녹음"
OUTPUT_DIR = INPUT_DIR / "output"
DONE_DIR   = INPUT_DIR / "processed"
PROCESSED_TRANSCRIPTS_DIR = DONE_DIR / "transcripts"

# 스킬 스크립트 경로
SPLIT_SCRIPT    = SKILLS_DIR / "transcript-tools" / "scripts" / "split_transcript.py"
# 2026-04-10: lancedb-rag 아카이브됨. qmd CLI 사용.
# INGEST_SCRIPT 경로는 더 이상 사용되지 않음 (index_to_vectordb() 함수는 qmd로 대체).
PROGRESS_SCRIPT = SKILLS_DIR / "progress-tracker" / "scripts" / "progress.py"

from transcript_naming import canonicalize_transcript_name

# 전사문 저장 기본 폴더 (매핑 실패 시)
UNMATCHED_DIR = INPUT_DIR / "unmatched_transcripts"
TRANSCRIPTION_LOG = AGENT_DIR / "state" / "transcription_log.json"

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def find_new_transcripts():
    """output/ 폴더에서 미처리 전사문(txt) 및 오디오(mp3/m4a) 파일 검색 및 분류"""
    if not OUTPUT_DIR.exists():
        print(f"  ⚠️ OUTPUT_DIR ({OUTPUT_DIR}) does not exist.")
        return []
    
    # 기존 로그 로드
    processed_originals = set()  # 원본 오디오 파일명 (확장자 포함)
    processed_transcripts = set()  # 전사 결과 파일명 (_transcript.txt)
    
    if TRANSCRIPTION_LOG.exists():
        try:
            with open(TRANSCRIPTION_LOG, "r", encoding="utf-8-sig") as f:
                log_data = json.load(f)
                for path_key, info in log_data.items():
                    # 1) 로그 key / original_path 모두에서 전사 파일명 후보 수집
                    candidate_names = {os.path.basename(path_key).lower()}

                    orig_path = info.get("original_path")
                    if orig_path:
                        candidate_names.add(os.path.basename(orig_path).lower())

                    for name in candidate_names:
                        if name.endswith("_transcript.txt"):
                            processed_transcripts.add(name)
                            canonical = canonicalize_transcript_name(DRIVE_ROOT, name)
                            processed_transcripts.add(canonical["canonical_name"].lower())

                    # 2) 오디오 원본 파일명 수집 (구 스키마/신 스키마 모두 호환)
                    audio_path = info.get("audio_path")
                    if audio_path:
                        processed_originals.add(os.path.basename(audio_path).lower())
                    elif orig_path and str(orig_path).lower().endswith(('.mp3', '.m4a', '.wav', '.wma')):
                        processed_originals.add(os.path.basename(orig_path).lower())
        except Exception as e:
            print(f"  ⚠️ 로그 읽기 오류: {e}")
    
    transcripts = []
    print(f"  🔍 Scanning {OUTPUT_DIR} for duplicates and new files...")
    
    count_audio_moved = 0
    count_txt_skipped = 0
    
    for f in OUTPUT_DIR.iterdir():
        if not f.is_file(): continue
        
        f_name_lower = f.name.lower()
        
        # A. 오디오 파일 (.mp3, .m4a) 처리
        if f_name_lower.endswith(('.mp3', '.m4a', '.wav', '.wma')):
            if f_name_lower in processed_originals:
                # 이미 전사 완료된 원본인 경우 processed 폴더로 자동 이동
                DONE_DIR.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(f), str(DONE_DIR / f.name))
                    count_audio_moved += 1
                except Exception as e:
                    print(f"  ⚠️ 파일 이동 실패 ({f.name}): {e}")
            continue
            
        # B. 전사문 파일 (_transcript.txt) 처리
        if f_name_lower.endswith("_transcript.txt"):
            canonical = canonicalize_transcript_name(DRIVE_ROOT, f.name)
            canonical_lower = canonical["canonical_name"].lower()
            if f_name_lower in processed_transcripts or canonical_lower in processed_transcripts:
                count_skipped_txt = 0 # Dummy for logic
                count_txt_skipped += 1
                continue
            transcripts.append(f)
    
    if count_audio_moved > 0 or count_txt_skipped > 0:
        print(f"  ♻️  Cleanup: Moved {count_audio_moved} processed audios | Skipped {count_txt_skipped} existing transcripts")
    
    print(f"  ✅ To process: {len(transcripts)} new transcripts")
    return sorted(transcripts)


def split_transcript(transcript_path: Path, output_dir: Path, parts: int = 10, dry_run: bool = False):
    """전사문을 파트별로 분할"""
    print(f"  ✂️  분할: {transcript_path.name} → {parts}파트")
    
    if dry_run:
        print(f"     [DRY-RUN] split_transcript.py {transcript_path} --parts {parts} --output {output_dir}")
        return True
    
    if SPLIT_SCRIPT.exists():
        cmd = [
            sys.executable,
            str(SPLIT_SCRIPT),
            str(transcript_path),
            "--parts",
            str(parts),
            "--output",
            str(output_dir),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            if result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    print(f"     {line}")
            return True
        print("     ⚠️ 외부 분할 실패, 폴백 분할로 전환")
        if result.stderr.strip():
            print(f"     {result.stderr.strip()[:200]}")

    return fallback_split(transcript_path, output_dir, parts)


def fallback_split(transcript_path: Path, output_dir: Path, parts: int):
    """split_transcript.py가 없을 때 직접 분할"""
    print(f"     ↳ 폴백 분할 실행 중...")
    
    with open(transcript_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 헤더와 본문 분리 (--- 구분자 기준)
    header = ""
    body = content
    if "---" in content:
        parts_split = content.split("---", 2)
        if len(parts_split) >= 3:
            header = parts_split[0] + "---" + parts_split[1] + "---\n\n"
            body = parts_split[2].strip()
    
    lines = body.split("\n")
    chunk_size = max(1, len(lines) // parts)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = transcript_path.stem.replace("_transcript", "")
    
    for i in range(parts):
        start = i * chunk_size
        end = start + chunk_size if i < parts - 1 else len(lines)
        chunk_lines = lines[start:end]
        
        if not chunk_lines:
            continue
        
        part_path = output_dir / f"{stem}_part{i+1:02d}.md"
        with open(part_path, "w", encoding="utf-8") as f:
            if i == 0:
                f.write(header)
            f.write("\n".join(chunk_lines))
        
        print(f"     📄 {part_path.name}")
    
    print(f"     ✅ 폴백 분할 완료 ({parts}파트)")
    return True


def save_original_transcript(
    transcript_path: Path,
    output_dir: Path,
    target_name: str | None = None,
    dry_run: bool = False,
):
    """전사 원본(txt) 저장"""
    raw_path = output_dir / (target_name or transcript_path.name)
    print(f"  💾 원본 저장: {raw_path}")

    if dry_run:
        print(f"     [DRY-RUN] copy {transcript_path} -> {raw_path}")
        return raw_path

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(str(transcript_path), str(raw_path))
        return raw_path
    except Exception as e:
        print(f"     ⚠️ 원본 저장 실패: {e}")
        return None


def archive_processed_transcript(
    transcript_path: Path,
    target_name: str | None = None,
    dry_run: bool = False,
):
    """처리 완료 전사본을 processed/transcripts/YYYY-MM-DD/로 이동"""
    date_dir = PROCESSED_TRANSCRIPTS_DIR / datetime.now().strftime("%Y-%m-%d")
    dest_path = date_dir / (target_name or transcript_path.name)
    print(f"  📦 처리완료 이동: {dest_path}")

    if dry_run:
        print(f"     [DRY-RUN] move {transcript_path} -> {dest_path}")
        return dest_path

    date_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(transcript_path), str(dest_path))
        return dest_path
    except Exception as e:
        print(f"     ⚠️ 처리완료 이동 실패: {e}")
        return None


def index_to_vectordb(transcript_dir: Path, dry_run: bool = False):
    """전사문을 qmd law-notes 컬렉션에 재인덱싱 (2026-04-10 LanceDB 대체).

    전사문은 sync/ 볼트 밖에 저장되므로 qmd가 자동 인덱싱하지 않는다.
    의미 있는 검색 대상으로 만들려면 sync/ 하위로 복사 후 별도 처리해야 한다.
    여기서는 qmd update만 호출해 sync/ 쪽 변동분을 반영한다.
    """
    print(f"  📊 qmd 재인덱싱 (law-notes): {transcript_dir}")

    if dry_run:
        print(f"     [DRY-RUN] qmd update && qmd embed")
        return True

    try:
        qmd_lib = LIB_DIR / "qmd_search.py"
        if not qmd_lib.exists():
            print(f"     ⚠️ qmd_search.py 미발견: {qmd_lib} — 인덱싱 건너뜀")
            return True
        # qmd CLI: update (파일 변동 스캔) + embed (벡터 갱신)
        for step in ("update", "embed"):
            result = subprocess.run(
                ["qmd", step],
                capture_output=True, text=True, encoding='utf-8', errors='replace'
            )
            if result.returncode != 0:
                print(f"     ⚠️ qmd {step} 실패: {result.stderr[:200]}")
                return False
        print(f"     ✅ qmd update + embed 완료")
        return True
    except FileNotFoundError:
        print(f"     ⚠️ qmd CLI를 찾을 수 없음 — 인덱싱 건너뜀")
        return True


def update_progress(part_name: str, dry_run: bool = False):
    """진도 업데이트"""
    print(f"  📅 진도 업데이트: {part_name}")
    
    if dry_run:
        print(f"     [DRY-RUN] progress.py --complete {part_name} --type transcript")
        return True
    
    cmd = [
        sys.executable, str(PROGRESS_SCRIPT),
        "--complete", part_name,
        "--type", "transcript"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode == 0:
            print(f"     ✅ 진도 업데이트 완료")
            return True
        else:
            err_msg = result.stderr[:200] if result.stderr else "Unknown error"
            print(f"     ⚠️ 진도 업데이트 실패: {err_msg}")
            return False
    except FileNotFoundError:
        print(f"     ⚠️ progress.py를 찾을 수 없습니다: {PROGRESS_SCRIPT}")
        return False


def update_transcription_log(transcript_path: Path, split_dir: Path, raw_path: Path = None, status: bool = True, source_path: Path = None):
    """전사 로그 업데이트

    파일 이동(archive) 시 기존 key entry도 보존하고 archived_to 필드로 추적한다.
    매 update 시 .bak 백업을 생성해 로그 손실을 방지한다.
    """
    log_file = TRANSCRIPTION_LOG
    if not log_file.parent.exists():
        log_file.parent.mkdir(parents=True, exist_ok=True)

    log_data = {}
    if log_file.exists():
        # 로그 파일 자동 백업 (직전 상태 보존)
        try:
            shutil.copy2(str(log_file), str(log_file) + ".bak")
        except Exception:
            pass
        try:
            with open(log_file, 'r', encoding='utf-8-sig') as f:
                log_data = json.load(f)
        except Exception:
            pass

    key = str(transcript_path)
    existing = log_data.get(key, {})

    # 이동된 경우: source_path (이동 전 경로)의 entry를 살려둔 채 archived_to 플래그만 추가
    if source_path and str(source_path) != key:
        src_key = str(source_path)
        src_entry = log_data.get(src_key, {})
        src_entry["archived_to"] = key
        src_entry["archived_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_data[src_key] = src_entry
        # 새 key로 이관할 때 원본 필드 상속
        for field in ("corrected", "correction_state", "corrected_file", "corrected_files",
                      "reviewed_files", "generated_files", "notes", "part_count",
                      "expected_total"):
            if field in src_entry and field not in existing:
                existing[field] = src_entry[field]

    log_data[key] = {
        "corrected": existing.get("corrected", False),
        "correction_state": existing.get("correction_state", "uncorrected"),
        "corrected_file": existing.get("corrected_file"),
        "corrected_files": existing.get("corrected_files", []) or ([existing.get("corrected_file")] if existing.get("corrected_file") else []),
        "reviewed_files": existing.get("reviewed_files", []) or ([existing.get("corrected_file")] if existing.get("corrected_file") else []),
        "generated_files": existing.get("generated_files", []),
        "duplicate_of": existing.get("duplicate_of", ""),
        "duplicate_reason": existing.get("duplicate_reason", ""),
        "notes": existing.get("notes", ""),
        "original_path": str(transcript_path),
        "archived_from": str(source_path) if source_path else existing.get("archived_from"),
        "split_dir": str(split_dir),
        "raw_path": str(raw_path) if raw_path else None,
        "part_count": existing.get("part_count", 0),
        "expected_total": existing.get("expected_total", 0),
        "stale_reason": existing.get("stale_reason", ""),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)
    print(f"  💾 전사 로그 업데이트 완료: {transcript_path.name}")


def extract_metadata(transcript_path: Path):
    """전사문 파일명에서 메타데이터 추출
    
    예상 파일명 패턴:
    - 송영곤_기본민법_1-2_transcript.txt
    - 헌1_1-1_transcript.txt
    - 형1_1-3_transcript.txt
    """
    info = canonicalize_transcript_name(DRIVE_ROOT, transcript_path.name)
    entry = info.get("entry", {}) or {}
    stem = transcript_path.stem.replace("_transcript", "")

    return {
        "filename": transcript_path.name,
        "stem": stem,
        "canonical_name": info["canonical_name"],
        "canonical_stem": info["canonical_stem"],
        "course_folder": entry.get("course_folder", ""),
        "citation_title": entry.get("citation_title", ""),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }


def main():
    parser = argparse.ArgumentParser(description="전사 후처리 자동화")
    parser.add_argument("--dry-run", action="store_true", help="실제 실행 없이 계획만 출력")
    parser.add_argument("--skip-split", action="store_true", help="분할 건너뛰기")
    parser.add_argument("--skip-index", action="store_true", help="벡터DB 인덱싱 건너뛰기")
    parser.add_argument("--skip-progress", action="store_true", help="진도 업데이트 건너뛰기")
    parser.add_argument("--parts", type=int, default=10, help="분할 파트 수 (기본: 10)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔄 전사 후처리 파이프라인")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️  DRY-RUN 모드 (실제 실행 없음)\n")
    
    # 1. 전사문 탐색
    transcripts = find_new_transcripts()
    
    if not transcripts:
        print("\n📭 처리할 전사문이 없습니다.")
        print(f"   Colab 전사 완료 후 '{OUTPUT_DIR}'에 파일이 생성됩니다.")
        return
    
    print(f"\n📋 처리 대상: {len(transcripts)}개 전사문\n")
    
    for idx, t_path in enumerate(transcripts, 1):
        print(f"\n{'─' * 50}")
        print(f"📝 [{idx}/{len(transcripts)}] {t_path.name}")
        print(f"{'─' * 50}")
        
        meta = extract_metadata(t_path)
        stem = meta["stem"]
        canonical_stem = meta.get("canonical_stem") or stem
        canonical_name = meta.get("canonical_name") or t_path.name
        
        # 분할 출력 폴더 (메타데이터의 folder 정보 우선 사용)
        folder_path = meta.get("course_folder")
        if folder_path:
            split_out = DRIVE_ROOT / folder_path / "전사문" / canonical_stem
        else:
            split_out = UNMATCHED_DIR / canonical_stem

        # Step 0: 전사 원본 저장
        raw_saved_path = save_original_transcript(
            t_path,
            split_out,
            target_name=canonical_name,
            dry_run=args.dry_run,
        )

        # Step 1: 분할
        split_ok = True
        if not args.skip_split:
            split_source = raw_saved_path if raw_saved_path else t_path
            split_ok = split_transcript(split_source, split_out, parts=args.parts, dry_run=args.dry_run)
        
        # Step 2: 벡터DB 인덱싱
        index_ok = True
        if not args.skip_index:
            index_ok = index_to_vectordb(split_out, dry_run=args.dry_run)
        
        # Step 3: 진도 업데이트
        progress_ok = True
        if not args.skip_progress:
            progress_ok = update_progress(stem, dry_run=args.dry_run)

        if not args.dry_run:
            archived_path = None
            if split_ok and index_ok and progress_ok:
                archived_path = archive_processed_transcript(
                    t_path,
                    target_name=canonical_name,
                    dry_run=False,
                )
            else:
                print("  ⚠️ 일부 단계 실패로 output 전사본 이동을 건너뜀")

            update_transcription_log(
                archived_path or t_path,
                split_out,
                raw_saved_path,
                source_path=t_path if archived_path else None,
            )
    
    # 완료 요약
    print(f"\n{'=' * 60}")
    print("🎉 후처리 완료!")
    print(f"{'=' * 60}")
    print(f"  전사문: {len(transcripts)}개 처리")
    if not args.skip_split:
        print(f"  분할: 과목별 전사문 폴더 (미매칭: {UNMATCHED_DIR})")
    if not args.skip_index:
        print(f"  벡터DB: qmd law-notes 재인덱싱 완료")
    if not args.skip_progress:
        print(f"  진도: progress.json 업데이트")
    
    print(f"\n💡 다음 단계:")
    print(f"   - 전사문 교정: '전사문 교정해줘' 또는 transcript-correction Skill")
    print(f"   - 수업노트 정리: Antigravity에게 '수업노트 정리해줘'")


if __name__ == "__main__":
    main()
