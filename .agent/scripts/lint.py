#!/usr/bin/env python3
"""
lint.py — 메모리 시스템 건강 체크 7종.

Karpathy LLM Wiki 패턴의 "lint" 단계.
모순, 오래된 정보, 고아 문서, 깨진 링크 등 자동 탐지.
#17-A 삭제 금지 원칙 준수 — 문제 파일은 _trash로 이동만.

사용법:
  python lint.py                 # 전체 건강 체크
  python lint.py --fix           # 자동 수정 가능한 항목만 수정
  python lint.py --report-only   # 보고서만 출력
"""

import os
import re
import sys
import glob
import json
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE = os.environ.get("MEMORY_BASE", r"H:\내 드라이브\.auto-memory")
WIKI_DIR = os.environ.get("WIKI_DIR", r"H:\내 드라이브\sync\wiki")
DAILY_DIR = os.path.join(BASE, "daily")
MEMORY_DIR = BASE
TRASH_BASE = r"H:\내 드라이브\_trash"


def check_broken_links(wiki_dir: str) -> list:
    """1. 깨진 [[백링크]] 탐지"""
    issues = []
    wiki_files = {os.path.basename(f).replace(".md", "")
                  for f in glob.glob(os.path.join(wiki_dir, "*.md"))}

    for wf in glob.glob(os.path.join(wiki_dir, "*.md")):
        with open(wf, "r", encoding="utf-8") as f:
            content = f.read()
        for m in re.finditer(r"\[\[([^\]]+)\]\]", content):
            target = m.group(1)
            if target not in wiki_files and not target.startswith("§"):
                issues.append({
                    "type": "broken_link",
                    "file": os.path.basename(wf),
                    "target": target,
                    "severity": "medium",
                })
    return issues


def check_orphans(wiki_dir: str) -> list:
    """2. 고아 문서 (어디서도 참조되지 않는 아티클)"""
    issues = []
    wiki_files = glob.glob(os.path.join(wiki_dir, "*.md"))
    all_names = {os.path.basename(f).replace(".md", "") for f in wiki_files}
    referenced = set()

    for wf in wiki_files:
        with open(wf, "r", encoding="utf-8") as f:
            content = f.read()
        for m in re.finditer(r"\[\[([^\]]+)\]\]", content):
            referenced.add(m.group(1))

    orphans = all_names - referenced - {"_index"}
    for o in orphans:
        issues.append({
            "type": "orphan",
            "file": f"{o}.md",
            "detail": "어디서도 참조되지 않는 아티클",
            "severity": "low",
        })
    return issues


def check_stale(wiki_dir: str, days: int = 30) -> list:
    """3. 오래된 아티클 (30일 이상 미갱신)"""
    issues = []
    cutoff = datetime.now() - timedelta(days=days)

    for wf in glob.glob(os.path.join(wiki_dir, "*.md")):
        mtime = datetime.fromtimestamp(os.path.getmtime(wf))
        if mtime < cutoff:
            issues.append({
                "type": "stale",
                "file": os.path.basename(wf),
                "last_modified": mtime.strftime("%Y-%m-%d"),
                "days_old": (datetime.now() - mtime).days,
                "severity": "low",
            })
    return issues


def check_contradictions(wiki_dir: str) -> list:
    """4. 모순 탐지 (같은 판례/학설이 다른 아티클에서 다르게 기술)"""
    issues = []
    case_claims = defaultdict(list)  # 판례번호 → [(파일, 주장)]

    for wf in glob.glob(os.path.join(wiki_dir, "*.md")):
        fname = os.path.basename(wf)
        with open(wf, "r", encoding="utf-8") as f:
            content = f.read()

        # 판례번호 + 주변 문맥 추출
        for m in re.finditer(r"(\d{2,4}다\w*\d+)", content):
            case_no = m.group(1)
            start = max(0, m.start() - 50)
            end = min(len(content), m.end() + 100)
            context = content[start:end].replace("\n", " ").strip()
            case_claims[case_no].append((fname, context))

    # 같은 판례가 2곳 이상에서 언급되면 잠재적 모순 후보
    for case_no, claims in case_claims.items():
        if len(claims) >= 2:
            files = list(set(c[0] for c in claims))
            if len(files) >= 2:
                issues.append({
                    "type": "potential_contradiction",
                    "case": case_no,
                    "files": files,
                    "detail": "동일 판례가 여러 아티클에서 언급 — 수동 확인 필요",
                    "severity": "high",
                })
    return issues


def check_empty_articles(wiki_dir: str) -> list:
    """5. 빈 아티클 (100자 미만)"""
    issues = []
    for wf in glob.glob(os.path.join(wiki_dir, "*.md")):
        size = os.path.getsize(wf)
        if size < 100:
            issues.append({
                "type": "empty",
                "file": os.path.basename(wf),
                "size": size,
                "severity": "medium",
            })
    return issues


def check_duplicate_topics(wiki_dir: str) -> list:
    """6. 중복 주제 (유사 이름의 아티클)"""
    issues = []
    names = [os.path.basename(f).replace(".md", "")
             for f in glob.glob(os.path.join(wiki_dir, "*.md"))
             if not f.endswith("_index.md")]

    for i, n1 in enumerate(names):
        for n2 in names[i+1:]:
            # 간단한 유사도: 한쪽이 다른 쪽에 포함
            if n1 in n2 or n2 in n1:
                issues.append({
                    "type": "duplicate_topic",
                    "files": [f"{n1}.md", f"{n2}.md"],
                    "detail": "주제명이 유사 — 병합 검토 필요",
                    "severity": "medium",
                })
    return issues


def check_index_sync(wiki_dir: str) -> list:
    """7. 인덱스와 실제 파일 불일치"""
    issues = []
    index_file = os.path.join(wiki_dir, "_index.md")
    if not os.path.exists(index_file):
        issues.append({
            "type": "missing_index",
            "detail": "_index.md 파일 없음 — compile.py 실행 필요",
            "severity": "high",
        })
        return issues

    with open(index_file, "r", encoding="utf-8") as f:
        index_content = f.read()

    # 인덱스에 있는 아티클
    indexed = set(re.findall(r"\[\[([^\]]+)\]\]", index_content))
    # 실제 파일
    actual = {os.path.basename(f).replace(".md", "")
              for f in glob.glob(os.path.join(wiki_dir, "*.md"))
              if not f.endswith("_index.md")}

    missing_from_index = actual - indexed
    missing_from_disk = indexed - actual

    for m in missing_from_index:
        issues.append({
            "type": "not_in_index",
            "file": f"{m}.md",
            "detail": "파일 존재하나 인덱스에 없음",
            "severity": "medium",
        })

    for m in missing_from_disk:
        issues.append({
            "type": "not_on_disk",
            "target": m,
            "detail": "인덱스에 있으나 파일 없음",
            "severity": "high",
        })

    return issues


def check_invalid_backlinks(wiki_dir: str) -> list:
    """8. 올바르지 않은 백링크 형식 검사"""
    issues = []
    for wf in glob.glob(os.path.join(wiki_dir, "*.md")):
        with open(wf, "r", encoding="utf-8") as f:
            content = f.read()
        for m in re.finditer(r"\[\[([^\]]+)\]\]", content):
            link = m.group(1).strip()
            # 판례 패턴 검증
            if any(prefix in link for prefix in ["대판", "대결", "헌재"]):
                pattern = r"^(대판|대결|헌재)\s+\d{4}\.\d{1,2}\.\d{1,2},\s+\w+"
                if not re.match(pattern, link):
                    issues.append({
                        "type": "invalid_backlink_format",
                        "file": os.path.basename(wf),
                        "target": link,
                        "detail": f"판례 백링크 형식이 표준을 따르지 않음: [[{link}]]",
                        "severity": "medium",
                    })
            # 조문 패턴 검증
            elif link.startswith("§"):
                if not re.match(r"^§\d+$", link):
                    issues.append({
                        "type": "invalid_backlink_format",
                        "file": os.path.basename(wf),
                        "target": link,
                        "detail": f"조문 백링크 형식은 [[§숫자]]여야 함: [[{link}]]",
                        "severity": "medium",
                    })
                else:
                    try:
                        val = int(link[1:])
                        if val < 10:
                            issues.append({
                                "type": "invalid_backlink_format",
                                "file": os.path.basename(wf),
                                "target": link,
                                "detail": f"조문 백링크는 §10 이상만 허용됨: [[{link}]]",
                                "severity": "low",
                            })
                    except ValueError:
                        pass
    return issues


def check_hanja_remnants(wiki_dir: str) -> list:
    """9. 한자 잔재 검사"""
    issues = []
    hanja_pattern = re.compile(r"[\u4e00-\u9fff]+")
    
    for wf in glob.glob(os.path.join(wiki_dir, "*.md")):
        with open(wf, "r", encoding="utf-8") as f:
            content = f.read()
        
        # HTML 주석 내 한자는 검사 제외
        cleaned_content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        
        matches = hanja_pattern.findall(cleaned_content)
        if matches:
            unique_hanjas = list(set(matches))
            issues.append({
                "type": "hanja_remnant",
                "file": os.path.basename(wf),
                "detail": f"한자 잔재 감지됨: {', '.join(unique_hanjas[:5])}...",
                "severity": "low",
            })
    return issues


def check_table_rendering(wiki_dir: str) -> list:
    """10. 마크다운 표 구조 검사"""
    issues = []
    for wf in glob.glob(os.path.join(wiki_dir, "*.md")):
        with open(wf, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        in_table = False
        table_cols = 0
        table_start_line = 0
        
        for idx, line in enumerate(lines):
            line_str = line.strip()
            if line_str.startswith("|") and line_str.endswith("|"):
                if re.match(r"^\|[\s\-:|]+$", line_str):
                    continue
                
                cols = len([c for c in line_str.split("|") if c])
                if not in_table:
                    in_table = True
                    table_cols = cols
                    table_start_line = idx + 1
                else:
                    if cols != table_cols:
                        issues.append({
                            "type": "broken_table_structure",
                            "file": os.path.basename(wf),
                            "detail": f"표 열 개수 불일치 (시작 {table_start_line}, 현재 {idx + 1}): 기대 {table_cols}, 실제 {cols}",
                            "severity": "medium",
                        })
            else:
                in_table = False
    return issues


def main():
    parser = argparse.ArgumentParser(description="메모리 시스템 건강 체크")
    parser.add_argument("--fix", action="store_true",
                        help="자동 수정 가능한 항목 수정")
    parser.add_argument("--report-only", action="store_true",
                        help="보고서만 출력")
    args = parser.parse_args()

    print("=" * 50)
    print("메모리 시스템 건강 체크 (lint)")
    print(f"대상: {WIKI_DIR}")
    print("=" * 50)

    all_issues = []

    checks = [
        ("1. 깨진 링크", check_broken_links),
        ("2. 고아 문서", check_orphans),
        ("3. 오래된 아티클", check_stale),
        ("4. 모순 탐지", check_contradictions),
        ("5. 빈 아티클", check_empty_articles),
        ("6. 중복 주제", check_duplicate_topics),
        ("7. 인덱스 동기화", check_index_sync),
        ("8. 올바르지 않은 백링크 형식", check_invalid_backlinks),
        ("9. 한자 잔재 검사", check_hanja_remnants),
        ("10. 마크다운 표 구조 검사", check_table_rendering),
    ]

    for name, check_fn in checks:
        issues = check_fn(WIKI_DIR)
        all_issues.extend(issues)
        status = "[OK] 정상" if not issues else f"[WARN] {len(issues)}건"
        print(f"\n{name}: {status}")
        for issue in issues:
            sev = {"high": "[HIGH]", "medium": "[MED ]", "low": "[LOW ]"}.get(
                issue.get("severity", "low"), "[LOW ]")
            detail = issue.get("detail", issue.get("target", issue.get("file", "")))
            print(f"  {sev} {detail}")

    # 요약
    high = sum(1 for i in all_issues if i.get("severity") == "high")
    medium = sum(1 for i in all_issues if i.get("severity") == "medium")
    low = sum(1 for i in all_issues if i.get("severity") == "low")

    print(f"\n{'=' * 50}")
    print(f"총 {len(all_issues)}건: HIGH {high} | MED {medium} | LOW {low}")

    if args.report_only:
        return

    # 보고서 저장
    report_file = os.path.join(BASE, "lint_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(all_issues),
            "high": high,
            "medium": medium,
            "low": low,
            "issues": all_issues,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n보고서 저장: {report_file}")


if __name__ == "__main__":
    main()
