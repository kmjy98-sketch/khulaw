#!/usr/bin/env python3
"""
Progress Tracker: 학습 진도 관리
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

PROGRESS_PATH = Path(__file__).parent.parent.parent.parent / "state" / "progress.json"


def load_progress() -> dict:
    """진도 파일 로드"""
    if PROGRESS_PATH.exists():
        # Some Windows editors write JSON with a UTF-8 BOM.
        with open(PROGRESS_PATH, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {
        "current_scope": {},
        "transcript_parts": {},
        "lecture_notes": {},
        "last_session": str(date.today()),
    }


def save_progress(data: dict) -> None:
    """진도 파일 저장"""
    data["last_session"] = str(date.today())
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def find_next_part(parts: dict, start_part: str) -> str:
    """이미 완료된 파트를 건너뛰고 다음 진행 파트를 찾는다."""
    part_num = int(start_part.replace("part", ""))
    candidate = part_num + 1

    while True:
        next_part = f"part{str(candidate).zfill(2)}"
        if parts.get(next_part) != "완료":
            return next_part
        candidate += 1


def show_status(data: dict) -> None:
    """현재 진도 출력"""
    scope = data.get("current_scope", {})
    parts = data.get("transcript_parts", {})
    notes = data.get("lecture_notes", {})
    
    print("[학습 진도]")
    print(f"  📖 교재: {scope.get('textbook', '미설정')}")
    print(f"  📄 페이지: {scope.get('page_range', '미설정')}")
    print(f"  📝 전사문: {scope.get('transcript', '미설정')}")
    print(f"  📅 마지막 세션: {data.get('last_session', 'N/A')}")
    
    # 파트 진행 상황
    if parts:
        completed = [k for k, v in parts.items() if v == "완료"]
        in_progress = [k for k, v in parts.items() if v == "진행중"]
        print(f"\n[전사문 진도]")
        print(f"  ✅ 완료: {', '.join(completed) if completed else '없음'}")
        print(f"  🔄 진행중: {', '.join(in_progress) if in_progress else '없음'}")
    
    # 수업노트 진행 상황
    if notes:
        print(f"\n[수업노트 정리]")
        for name, info in notes.items():
            print(f"  📓 {name}: {info.get('range', '')} ({info.get('last_updated', '')})")


def complete_part(data: dict, part: str, part_type: str) -> None:
    """파트 완료 마킹"""
    if part_type == "transcript":
        data.setdefault("transcript_parts", {})
        data["transcript_parts"][part] = "완료"
        print(f"✅ 전사문 {part} 완료 마킹됨")
        
        # 다음 파트 진행중으로 설정
        try:
            next_part = find_next_part(data["transcript_parts"], part)
            data["transcript_parts"][next_part] = "진행중"
            print(f"🔄 다음 파트 {next_part} 진행중으로 설정")
        except ValueError:
            pass
        
        
    elif part_type == "notes":
        # 수업노트 정리 완료 - lecture_notes에 기록
        lecture_name = data.get("current_scope", {}).get("textbook", "Unknown")
        lecture_name = Path(lecture_name).stem if lecture_name else "Unknown"
        
        data.setdefault("lecture_notes", {})
        if lecture_name not in data["lecture_notes"]:
            data["lecture_notes"][lecture_name] = {"range": part, "last_updated": str(date.today())}
        else:
            existing_range = data["lecture_notes"][lecture_name].get("range", "")
            if part not in existing_range:
                data["lecture_notes"][lecture_name]["range"] = f"{existing_range}-{part}" if existing_range else part
            data["lecture_notes"][lecture_name]["last_updated"] = str(date.today())
        
        print(f"✅ 수업노트 {part} 정리 완료 마킹됨")


def set_scope(data: dict, textbook: str, page_range: str, transcript: str = None) -> None:
    """현재 범위 설정"""
    data["current_scope"] = {
        "textbook": textbook,
        "page_range": page_range,
    }
    if transcript:
        data["current_scope"]["transcript"] = transcript
    
    print(f"✅ 범위 설정됨:")
    print(f"  📖 교재: {textbook}")
    print(f"  📄 페이지: {page_range}")
    if transcript:
        print(f"  📝 전사문: {transcript}")


def next_part(data: dict) -> None:
    """다음 파트로 이동"""
    parts = data.get("transcript_parts", {})
    in_progress = [k for k, v in parts.items() if v == "진행중"]
    
    if in_progress:
        current = sorted(in_progress)[0]
        parts[current] = "완료"
        
        next_p = find_next_part(parts, current)
        parts[next_p] = "진행중"
        
        # 전사문 경로 업데이트
        if "current_scope" in data and "transcript" in data["current_scope"]:
            old_transcript = data["current_scope"]["transcript"]
            new_transcript = old_transcript.replace(current, next_p)
            data["current_scope"]["transcript"] = new_transcript
        
        print(f"✅ {current} → {next_p} 이동 완료")
    else:
        print("⚠️ 진행중인 파트가 없습니다")


def main():
    parser = argparse.ArgumentParser(description="Progress Tracker: 학습 진도 관리")
    parser.add_argument("--status", "-s", action="store_true", help="현재 진도 조회")
    parser.add_argument("--complete", "-c", help="파트 완료 마킹 (예: part01)")
    parser.add_argument("--type", "-t", choices=["transcript", "notes"], default="transcript", help="완료 유형")
    parser.add_argument("--set-scope", nargs=2, metavar=("TEXTBOOK", "PAGES"), help="범위 설정")
    parser.add_argument("--transcript", help="전사문 경로 (set-scope와 함께 사용)")
    parser.add_argument("--next", "-n", action="store_true", help="다음 파트로 이동")
    
    args = parser.parse_args()
    
    if not any([args.status, args.complete, args.set_scope, args.next]):
        parser.print_help()
        sys.exit(1)
    
    data = load_progress()
    
    if args.status:
        show_status(data)
    elif args.complete:
        complete_part(data, args.complete, args.type)
        save_progress(data)
    elif args.set_scope:
        set_scope(data, args.set_scope[0], args.set_scope[1], args.transcript)
        save_progress(data)
    elif args.next:
        next_part(data)
        save_progress(data)


if __name__ == "__main__":
    main()
