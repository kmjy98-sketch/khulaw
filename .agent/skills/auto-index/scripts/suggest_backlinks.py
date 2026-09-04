#!/usr/bin/env python3
"""
suggest_backlinks.py — 과목 내 노트 간 백링크 제안 생성

기능:
  1. 양 볼트의 .md 파일에서 ## 헤딩, 조문(§, 제X조), 판례번호 추출
  2. 과목 내 교차참조 맵 생성 (민법끼리, 형법끼리, 헌법끼리)
  3. 중간↔기말 연결 우선
  4. 기존 백링크 [[]] 의 깨진 링크 탐지
  5. 출력: .agent/state/backlink_suggestions.json
"""

import os
import sys
import json
import re
from pathlib import Path
from collections import defaultdict

_p = os.path.abspath(__file__)
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, 'scripts'))
from _vault import VAULT_ROOT, vp  # noqa: E402

BASE = Path(VAULT_ROOT)
VAULTS = [
    BASE / "_4과목_도표추가본_통합본_모음",
    BASE / "_기말_도표추가본_통합본_모음",
]
OUTPUT = BASE / ".agent/state/backlink_suggestions.json"

# 과목 분류 패턴
SUBJECT_PATTERNS = {
    "민법": re.compile(r"민법|민\d|강혜림|전경운|송영곤"),
    "형법": re.compile(r"형법|형\d|서보학|홍형철|김성돈"),
    "헌법": re.compile(r"헌법|헌\d|이진"),
    "국제법": re.compile(r"국제법|백범석"),
}

# 추출 패턴
RE_HEADING2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)
RE_ARTICLE_FULL = re.compile(r"제(\d+)조(?:의\d+)?")  # 제126조
RE_ARTICLE_SYMBOL = re.compile(r"§(\d+)")  # §126
RE_CASE_NUM = re.compile(r"(\d{2,4}다\d+)")  # 2018다40231
RE_CASE_COURT = re.compile(r"대판\s*(\d{4}\.\d{1,2}\.\d{1,2})")
RE_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
RE_BOLD_TERM = re.compile(r"\*\*([가-힣]{2,8})\*\*")


def classify_subject(filename: str) -> str | None:
    for subj, pat in SUBJECT_PATTERNS.items():
        if pat.search(filename):
            return subj
    return None


def extract_features(filepath: Path) -> dict:
    """파일에서 헤딩, 조문, 판례, 볼드 키워드, 기존 위키링크 추출."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    headings = []
    for m in RE_HEADING2.finditer(text):
        headings.append(m.group(1).strip())

    articles = set()
    for m in RE_ARTICLE_FULL.finditer(text):
        articles.add(f"제{m.group(1)}조")
    for m in RE_ARTICLE_SYMBOL.finditer(text):
        articles.add(f"제{m.group(1)}조")

    cases = set()
    for m in RE_CASE_NUM.finditer(text):
        cases.add(m.group(1))
    for m in RE_CASE_COURT.finditer(text):
        cases.add(m.group(1))

    bold_terms = set()
    for m in RE_BOLD_TERM.finditer(text):
        bold_terms.add(m.group(1))

    wikilinks = []
    for i, line in enumerate(lines):
        for m in RE_WIKILINK.finditer(line):
            wikilinks.append({"line": i + 1, "link": m.group(1)})

    return {
        "headings": headings,
        "articles": articles,
        "cases": cases,
        "bold_terms": bold_terms,
        "wikilinks": wikilinks,
    }


def check_broken_links(features_map: dict) -> list:
    """기존 위키링크가 실제 헤딩에 대응하는지 확인."""
    broken = []
    all_headings = {}  # {filename_without_ext: set_of_headings}
    for fname, feat in features_map.items():
        stem = Path(fname).stem
        all_headings[stem] = set(feat["headings"])

    for fname, feat in features_map.items():
        for wl in feat["wikilinks"]:
            link = wl["link"]
            # [[파일명#섹션]] 또는 [[파일명]]
            if "#" in link:
                parts = link.split("#", 1)
                target_file = parts[0].strip()
                target_section = parts[1].strip().split("|")[0].strip()
            else:
                target_file = link.split("|")[0].strip()
                target_section = None

            if target_file and target_file not in all_headings:
                broken.append({
                    "file": fname,
                    "line": wl["line"],
                    "link": f"[[{link}]]",
                    "issue": "target file not found",
                })
            elif target_section and target_file in all_headings:
                if target_section not in all_headings[target_file]:
                    broken.append({
                        "file": fname,
                        "line": wl["line"],
                        "link": f"[[{link}]]",
                        "issue": f"target heading '{target_section}' not found",
                    })

    return broken


def generate_suggestions(features_map: dict, subject_map: dict) -> list:
    """과목 내 공유 조문/판례/키워드 기반 백링크 제안 생성."""
    suggestions = []

    # 과목별 파일 그룹
    subject_files = defaultdict(list)
    for fname, subj in subject_map.items():
        if subj:
            subject_files[subj].append(fname)

    for subj, files in subject_files.items():
        if len(files) < 2:
            continue

        # 파일 쌍별 공유 요소 탐색
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                f1, f2 = files[i], files[j]
                feat1 = features_map[f1]
                feat2 = features_map[f2]

                # 공유 조문
                shared_articles = feat1["articles"] & feat2["articles"]
                for art in sorted(shared_articles):
                    # f1 → f2 제안
                    # 해당 조문이 등장하는 f2의 첫 번째 헤딩 찾기
                    target_heading = _find_heading_for_article(feat2, art)
                    source_heading = _find_heading_for_article(feat1, art)
                    is_midterm_final = _is_midterm_final_pair(f1, f2)
                    suggestions.append({
                        "source_file": f1,
                        "source_section": source_heading or "(전체)",
                        "target_file": f2,
                        "target_section": target_heading or "(전체)",
                        "reason": f"{art} 공유",
                        "priority": "high" if is_midterm_final else "medium",
                    })

                # 공유 판례
                shared_cases = feat1["cases"] & feat2["cases"]
                for case in sorted(shared_cases)[:5]:  # 상위 5개
                    target_heading = feat2["headings"][0] if feat2["headings"] else "(전체)"
                    suggestions.append({
                        "source_file": f1,
                        "source_section": "(판례)",
                        "target_file": f2,
                        "target_section": target_heading,
                        "reason": f"판례 {case} 공유",
                        "priority": "medium",
                    })

                # 중간↔기말 연결 (같은 과목+강사)
                if is_midterm_final := _is_midterm_final_pair(f1, f2):
                    suggestions.append({
                        "source_file": f1,
                        "source_section": "(범위 계속)",
                        "target_file": f2,
                        "target_section": feat2["headings"][0] if feat2["headings"] else "(전체)",
                        "reason": "중간↔기말 범위 연결",
                        "priority": "high",
                    })

    # 중복 제거
    seen = set()
    deduped = []
    for s in suggestions:
        key = (s["source_file"], s["target_file"], s["reason"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    return sorted(deduped, key=lambda x: (0 if x["priority"] == "high" else 1, x["source_file"]))


def _find_heading_for_article(features: dict, article: str) -> str | None:
    """조문 번호가 포함된 헤딩을 찾는다."""
    art_num = re.search(r"\d+", article)
    if not art_num:
        return None
    num = art_num.group()
    for h in features["headings"]:
        if num in h and ("조" in h or "§" in h or article in h):
            return h
    return None


def _is_midterm_final_pair(f1: str, f2: str) -> bool:
    """두 파일이 같은 과목의 중간↔기말 쌍인지."""
    mid_final = {"중간", "기말"}
    f1_has = {"중간"} if "중간" in f1 else ({"기말"} if "기말" in f1 else set())
    f2_has = {"중간"} if "중간" in f2 else ({"기말"} if "기말" in f2 else set())
    return f1_has | f2_has == mid_final


def main():
    features_map = {}
    subject_map = {}

    for vault in VAULTS:
        if not vault.exists():
            continue
        for md_file in sorted(vault.glob("**/*.md")):
            fname = md_file.name
            features_map[fname] = extract_features(md_file)
            # set → list for JSON
            features_map[fname]["articles"] = set(features_map[fname]["articles"])
            features_map[fname]["cases"] = set(features_map[fname]["cases"])
            features_map[fname]["bold_terms"] = set(features_map[fname]["bold_terms"])
            subject_map[fname] = classify_subject(fname)

    suggestions = generate_suggestions(features_map, subject_map)
    broken_links = check_broken_links(features_map)

    result = {
        "suggestions": suggestions,
        "broken_links": broken_links,
        "summary": {
            "files_scanned": len(features_map),
            "total_suggestions": len(suggestions),
            "broken_links": len(broken_links),
            "by_subject": {},
        },
    }

    # 과목별 통계
    for subj in set(subject_map.values()):
        if subj:
            count = sum(1 for s in suggestions if classify_subject(s["source_file"]) == subj)
            result["summary"]["by_subject"][subj] = count

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"백링크 제안 완료: {len(features_map)}개 파일 스캔, "
          f"{len(suggestions)}개 제안, {len(broken_links)}개 깨진 링크")
    print(f"결과: {OUTPUT}")


if __name__ == "__main__":
    main()
