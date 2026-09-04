#!/usr/bin/env python3
"""
compile.py — daily log들을 주제별 wiki 아티클로 컴파일.

[FROZEN 2026-04-24] 동결 — 1회 가동 후 미사용. 위키 정본은 wiki_원문분할.py→sync/위키/원문
계통으로 대체됨. 부활은 CLAUDE.md #41 결정 후. 진입점은 memory-maintenance 스킬.

Karpathy LLM Wiki 패턴의 "compile" 단계.
여러 세션에 걸쳐 축적된 지식을 주제별로 통합.

사용법:
  python compile.py                  # 미컴파일 daily log 전부 처리
  python compile.py --rebuild        # wiki 전체 재구축
  python compile.py --dry-run        # 변경 없이 미리보기
"""

import os
import re
import sys
import glob
import json
import argparse
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE = os.environ.get("MEMORY_BASE", vp(".auto-memory"))
DAILY_DIR = os.path.join(BASE, "daily")
SESSION_LOGS_DIR = os.path.join(BASE, "session_logs")
WIKI_DIR = os.environ.get("WIKI_DIR", vp("sync", "wiki"))
INDEX_FILE = os.path.join(WIKI_DIR, "_index.md")
COMPILE_STATE = os.path.join(BASE, ".compile_state.json")

# === 법학 주제 분류 키워드 ===
TOPIC_KEYWORDS = {
    # 민법
    "점유취득시효": ["취득시효", "§245", "점유취득", "자주점유", "타주점유", "시효완성"],
    "물권적청구권": ["물권적 청구권", "§213", "§214", "반환청구", "방해배제", "방해예방"],
    "명의신탁": ["명의신탁", "실명법", "계약명의신탁", "2자간", "중간생략"],
    "법정지상권": ["법정지상권", "§366", "관습법상", "분묘기지권"],
    "전세권": ["전세권", "전세금반환", "전세권저당권"],
    "소멸시효": ["소멸시효", "§162", "§168", "§170", "시효중단", "시효이익"],
    "사정변경원칙": ["사정변경", "2004다31302", "계약준수"],
    "선의취득": ["선의취득", "§249", "점유개정", "도품"],
    "등기청구권": ["등기청구권", "이전등기", "진정명의회복", "가등기"],
    "과실수취권": ["과실수취", "§201", "§203", "과실취득"],
    "청구항변구조": ["청구-항변", "원고", "피고", "재항변", "공방 구조"],
    "하자담보책임": ["하자담보", "§570", "§580", "담보책임"],
    # 형법
    "인과관계": ["인과관계", "상당인과관계", "객관적 귀속", "합법칙적"],
    "고의과실": ["고의", "과실", "미필적 고의", "인식있는 과실"],
    "위법성조각": ["정당방위", "긴급피난", "정당행위", "위법성조각"],
    "오상방위": ["오상방위", "위전착", "엄격책임설", "법효과제한"],
    "공범론": ["공동정범", "공모관계이탈", "간접정범", "교사범", "종범", "§33"],
    "미수범": ["미수", "중지미수", "불능미수", "실행착수", "장애미수"],
    # 헌법
    "헌법재판": ["헌법소원", "위헌심사", "헌법재판소", "권한쟁의"],
    "기본권": ["기본권", "자유권", "평등권", "생명권"],
    "통치구조": ["국회", "대통령", "사법부", "권력분립"],
}


def classify_topic(text: str) -> list:
    """텍스트에서 관련 주제 분류"""
    topics = []
    text_lower = text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score >= 1:
            topics.append((topic, score))
    topics.sort(key=lambda x: -x[1])
    return [t[0] for t in topics[:3]]  # 상위 3개 주제


def load_compile_state() -> dict:
    """컴파일 상태 로드"""
    if os.path.exists(COMPILE_STATE):
        with open(COMPILE_STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_compiled": None, "compiled_files": []}


def save_compile_state(state: dict):
    """컴파일 상태 저장"""
    with open(COMPILE_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _load_with_raw(daily_file: str, include_raw: bool) -> str:
    """daily 로그 내용 로드. include_raw=True이면 같은 날짜 session_logs 병합."""
    with open(daily_file, "r", encoding="utf-8") as f:
        content = f.read()

    if not include_raw:
        return content

    date_str = os.path.basename(daily_file).replace(".md", "")
    session_pattern = os.path.join(SESSION_LOGS_DIR, f"session_{date_str}*")
    for sl in sorted(glob.glob(session_pattern)):
        try:
            with open(sl, "r", encoding="utf-8") as f:
                content += "\n\n<!-- raw:" + os.path.basename(sl) + " -->\n" + f.read()
        except OSError:
            continue
    return content


def compile_to_wiki(daily_files: list, dry_run: bool = False, include_raw: bool = False):
    """daily log들을 wiki 아티클로 컴파일.
       include_raw=True이면 session_logs 원문도 분류에 포함 (daily가 빈약한 경우 대비)."""
    os.makedirs(WIKI_DIR, exist_ok=True)

    # 주제별 내용 수집
    topic_entries = defaultdict(list)

    for df in daily_files:
        content = _load_with_raw(df, include_raw)

        date_str = os.path.basename(df).replace(".md", "")
        topics = classify_topic(content)

        # 섹션별 분리 (daily: `### 세션:`, raw: `## 제목`)
        sep_pattern = r"^#{2,3} " if include_raw else r"^### "
        sections = re.split(sep_pattern, content, flags=re.MULTILINE)
        for section in sections[1:]:  # 첫 번째는 헤더
            sec_topics = classify_topic(section)
            for topic in (sec_topics or topics):
                topic_entries[topic].append({
                    "date": date_str,
                    "content": section.strip()[:500],
                    "source": os.path.basename(df),
                })

    if not topic_entries:
        print("No topics extracted from daily logs")
        return {}

    # wiki 아티클 생성/갱신
    results = {}
    for topic, entries in topic_entries.items():
        wiki_file = os.path.join(WIKI_DIR, f"{topic}.md")

        # 기존 아티클 로드
        existing = ""
        if os.path.exists(wiki_file):
            with open(wiki_file, "r", encoding="utf-8") as f:
                existing = f.read()

        # 새 내용 구성
        new_content = f"# {topic}\n\n"
        new_content += f"_마지막 컴파일: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n"

        if existing:
            # 기존 본문 유지 (헤더와 메타 제거 후)
            body = re.sub(r"^#.*\n+_마지막 컴파일.*\n+", "", existing).strip()
            if body:
                new_content += body + "\n\n"

        # 새 엔트리 추가
        new_content += "---\n## 최근 세션 기록\n\n"
        for entry in entries:
            new_content += f"### [{entry['date']}] ({entry['source']})\n"
            new_content += entry["content"] + "\n\n"

        if dry_run:
            print(f"[DRY-RUN] {topic}: {len(entries)} entries → {wiki_file}")
        else:
            with open(wiki_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  {topic}: {len(entries)} entries → {wiki_file}")

        results[topic] = len(entries)

    return results


def build_index(dry_run: bool = False):
    """wiki 인덱스 생성"""
    wiki_files = sorted(glob.glob(os.path.join(WIKI_DIR, "*.md")))
    wiki_files = [f for f in wiki_files if not f.endswith("_index.md")]

    index = "# Wiki 인덱스\n\n"
    index += f"_생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
    index += f"아티클: {len(wiki_files)}개_\n\n"

    # 분류별 정리
    categories = {
        "민법": [], "형법": [], "헌법": [], "기타": []
    }

    civil_topics = ["점유취득시효", "물권적청구권", "명의신탁", "법정지상권",
                     "전세권", "소멸시효", "사정변경원칙", "선의취득",
                     "등기청구권", "과실수취권", "청구항변구조", "하자담보책임"]
    criminal_topics = ["인과관계", "고의과실", "위법성조각", "오상방위",
                        "공범론", "미수범"]
    constitutional_topics = ["헌법재판", "기본권", "통치구조"]

    for wf in wiki_files:
        name = os.path.basename(wf).replace(".md", "")
        # 파일 크기로 내용량 추정
        size = os.path.getsize(wf)
        size_label = "●" if size > 5000 else "○" if size > 1000 else "·"

        entry = f"- {size_label} [[{name}]]"

        if name in civil_topics:
            categories["민법"].append(entry)
        elif name in criminal_topics:
            categories["형법"].append(entry)
        elif name in constitutional_topics:
            categories["헌법"].append(entry)
        else:
            categories["기타"].append(entry)

    for cat, items in categories.items():
        if items:
            index += f"\n## {cat}\n\n"
            index += "\n".join(items) + "\n"

    index += "\n---\n_● 5KB+ | ○ 1KB+ | · 소규모_\n"

    if dry_run:
        print(f"[DRY-RUN] Would write index with {len(wiki_files)} articles")
    else:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write(index)
        print(f"Index updated: {len(wiki_files)} articles")


def main():
    parser = argparse.ArgumentParser(description="daily log → wiki 아티클 컴파일")
    parser.add_argument("--rebuild", action="store_true",
                        help="wiki 전체 재구축")
    parser.add_argument("--dry-run", action="store_true",
                        help="변경 없이 미리보기")
    parser.add_argument("--include-raw", action="store_true",
                        help="session_logs 원문도 주제 분류에 포함 (daily가 빈약할 때)")
    args = parser.parse_args()

    state = load_compile_state()

    # 처리 대상 daily log 수집
    all_daily = sorted(glob.glob(os.path.join(DAILY_DIR, "*.md")))

    if args.rebuild:
        target_files = all_daily
    else:
        compiled = set(state.get("compiled_files", []))
        target_files = [f for f in all_daily if os.path.basename(f) not in compiled]

    if not target_files:
        print("No new daily logs to compile")
        build_index(args.dry_run)
        return

    print(f"Compiling {len(target_files)} daily log(s)"
          + (" [include-raw]" if args.include_raw else "")
          + "...")
    results = compile_to_wiki(target_files, args.dry_run, include_raw=args.include_raw)

    # 인덱스 갱신
    build_index(args.dry_run)

    # 상태 업데이트
    if not args.dry_run:
        state["last_compiled"] = datetime.now().isoformat()
        state["compiled_files"] = [os.path.basename(f) for f in all_daily]
        save_compile_state(state)

    print(f"\nDone: {len(results)} topics updated")


if __name__ == "__main__":
    main()
