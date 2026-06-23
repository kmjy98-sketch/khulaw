#!/usr/bin/env python3
"""
flush.py — 세션 로그에서 핵심 내용을 추출하여 일별 요약(daily log)으로 정리.

[FROZEN 2026-04-24] 동결 — 1회 가동 후 미사용. 위키 정본은 wiki_원문분할.py→sync/위키/원문
계통으로 대체됨. 부활은 CLAUDE.md #41 결정 후. 진입점은 memory-maintenance 스킬.

Karpathy LLM Wiki 패턴의 "ingest" 단계.
세션 종료 hook에서 호출되거나 수동 실행.

사용법:
  python flush.py                        # 오늘의 미처리 세션 로그 전부 flush
  python flush.py --date 2026-04-24      # 특정 날짜 로그만
  python flush.py --dry-run              # 변경 없이 미리보기
"""

import os
import re
import sys
import json
import glob
import argparse
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# === 경로 설정 ===
BASE = os.environ.get("MEMORY_BASE", vp(".auto-memory"))
SESSION_LOGS = os.path.join(BASE, "session_logs")
DAILY_DIR = os.path.join(BASE, "daily")

# === 추출 패턴 (법학 학습 특화, 2026-04-24 느슨화) ===
EXTRACT_PATTERNS = {
    "판례": r"대판\s*[\d.]+\s*선고\s*\d+다\w*\d+|대판\s*\d+다\w*\d+|\d{2,4}다\w*\d+|\d{4}헌\w+\d+",
    "조문": r"§\d+|제\d+조",
    "학설_변경": r"(판례|다수설|소수설|교수님|통설).*(변경|수정|오류|잘못|교정|보강|추가|삭제|확인)",
    "핵심_결정": r"(추가|삭제|수정|보강|변환|통일|완료|반영|적용|설치|생성|이동|교체|삽입|제거|변경)",
    "교훈": r"(주의|실수|오류|깨달|발견|확인|금지|사용해야|표시해야|적용해야|준수|위반|놓침|빠짐|누락)",
    "ocr_교정": r"(?i)(OCR|paddle|marker[-_]?pdf|haiku|sonnet).*(교정|적용|거부|완료|오류|보존|anchor|table_adopt|low_confidence)",
}

# === 섹션 헤더 매핑 (## 제목 → insights 카테고리) ===
SECTION_DECISION_KWS = ("수정", "보강", "변경", "시스템", "결정", "작업", "판례", "학설", "확인")
SECTION_LESSON_KWS = ("교훈", "주의", "발견")


def extract_insights(content: str) -> dict:
    """세션 로그에서 핵심 인사이트 추출 (정규식 + 섹션 헤더 2단계)"""
    insights = {
        "판례_언급": [],
        "조문_언급": [],
        "결정사항": [],
        "교훈": [],
        "파일_변경": [],
        "ocr_교정": [],
    }

    # 1단계: 줄 단위 정규식 매칭
    lines = content.split("\n")
    for line in lines:
        for m in re.finditer(EXTRACT_PATTERNS["판례"], line):
            case = m.group().strip()
            if case not in insights["판례_언급"]:
                insights["판례_언급"].append(case)

        for m in re.finditer(EXTRACT_PATTERNS["조문"], line):
            statute = m.group().strip()
            if statute not in insights["조문_언급"]:
                insights["조문_언급"].append(statute)

        if re.search(EXTRACT_PATTERNS["핵심_결정"], line):
            cleaned = line.strip()[:150]
            if cleaned and len(cleaned) > 5 and cleaned not in insights["결정사항"]:
                insights["결정사항"].append(cleaned)

        if re.search(EXTRACT_PATTERNS["교훈"], line):
            cleaned = line.strip()[:150]
            if cleaned and len(cleaned) > 5 and cleaned not in insights["교훈"]:
                insights["교훈"].append(cleaned)

        if re.search(EXTRACT_PATTERNS["ocr_교정"], line):
            cleaned = line.strip()[:150]
            if cleaned and len(cleaned) > 5 and cleaned not in insights["ocr_교정"]:
                insights["ocr_교정"].append(cleaned)

    # 2단계: `## 섹션` 헤더 기반 블록 추출
    sections = re.split(r"^## ", content, flags=re.MULTILINE)
    for section in sections[1:]:  # 첫 섹션은 헤더 이전의 머리말
        section_lines = section.split("\n")
        header = section_lines[0].strip().lower()
        body_lines = section_lines[1:]

        if any(kw in header for kw in SECTION_DECISION_KWS):
            for line in body_lines:
                cleaned = line.strip().lstrip("- ").lstrip("* ")[:150]
                if cleaned and len(cleaned) > 5 and cleaned not in insights["결정사항"]:
                    insights["결정사항"].append(cleaned)

        if any(kw in header for kw in SECTION_LESSON_KWS):
            for line in body_lines:
                cleaned = line.strip().lstrip("- ").lstrip("* ")[:150]
                if cleaned and len(cleaned) > 5 and cleaned not in insights["교훈"]:
                    insights["교훈"].append(cleaned)

    return insights


def flush_session(session_file: str) -> dict:
    """단일 세션 로그를 처리"""
    with open(session_file, "r", encoding="utf-8") as f:
        content = f.read()

    insights = extract_insights(content)

    # 파일 메타데이터
    fname = os.path.basename(session_file)
    timestamp = fname.replace("session_", "").replace(".md", "").replace(".json", "")

    return {
        "session": fname,
        "timestamp": timestamp,
        "insights": insights,
    }


def write_daily_log(target_date: str, entries: list, dry_run: bool = False):
    """일별 요약 파일 생성/갱신"""
    os.makedirs(DAILY_DIR, exist_ok=True)
    daily_file = os.path.join(DAILY_DIR, f"{target_date}.md")

    # 기존 내용 보존
    existing = ""
    if os.path.exists(daily_file):
        with open(daily_file, "r", encoding="utf-8") as f:
            existing = f.read()

    # 새 내용 구성
    new_sections = []
    for entry in entries:
        ins = entry["insights"]
        section = f"\n### 세션: {entry['timestamp']}\n"

        if ins["결정사항"]:
            section += "\n**결정사항:**\n"
            for d in ins["결정사항"][:30]:
                section += f"- {d}\n"

        if ins["교훈"]:
            section += "\n**교훈:**\n"
            for l in ins["교훈"][:10]:
                section += f"- {l}\n"

        if ins["판례_언급"]:
            section += f"\n**판례:** {', '.join(ins['판례_언급'][:20])}\n"

        if ins["조문_언급"]:
            section += f"\n**조문:** {', '.join(ins['조문_언급'][:20])}\n"

        if ins["ocr_교정"]:
            section += "\n**OCR 교정:**\n"
            for o in ins["ocr_교정"][:10]:
                section += f"- {o}\n"

        new_sections.append(section)

    if not new_sections:
        return None

    output = f"# Daily Log: {target_date}\n\n"
    if existing and not existing.startswith(f"# Daily Log: {target_date}"):
        output += existing + "\n"
    output += "\n".join(new_sections)

    if dry_run:
        print(f"[DRY-RUN] Would write {daily_file}")
        print(f"  Entries: {len(entries)}")
        return daily_file

    with open(daily_file, "w", encoding="utf-8") as f:
        f.write(output)

    return daily_file


def main():
    parser = argparse.ArgumentParser(description="세션 로그 → 일별 요약 flush")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="처리할 날짜 (기본: 오늘)")
    parser.add_argument("--dry-run", action="store_true",
                        help="변경 없이 미리보기")
    parser.add_argument("--all", action="store_true",
                        help="모든 미처리 로그 flush")
    args = parser.parse_args()

    os.makedirs(SESSION_LOGS, exist_ok=True)

    # 세션 로그 수집
    if args.all:
        pattern = os.path.join(SESSION_LOGS, "session_*")
    else:
        pattern = os.path.join(SESSION_LOGS, f"session_{args.date}*")

    log_files = sorted(glob.glob(pattern))

    if not log_files:
        print(f"No session logs found for {args.date}")
        return

    print(f"Found {len(log_files)} session log(s)")

    # 날짜별 그룹
    by_date = {}
    for lf in log_files:
        fname = os.path.basename(lf)
        d = fname[8:18] if len(fname) > 18 else args.date  # session_YYYY-MM-DD
        by_date.setdefault(d, []).append(lf)

    # flush 실행
    for d, files in sorted(by_date.items()):
        entries = [flush_session(f) for f in files]
        entries = [e for e in entries if any(e["insights"].values())]

        if entries:
            result = write_daily_log(d, entries, args.dry_run)
            if result:
                print(f"  {d}: {len(entries)} entries → {result}")
        else:
            print(f"  {d}: no insights extracted")


if __name__ == "__main__":
    main()
