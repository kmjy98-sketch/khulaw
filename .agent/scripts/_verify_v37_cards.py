# -*- coding: utf-8 -*-
"""
_verify_v37_cards.py (일회성) — outputs/02_cards_v37/*.md 전수 빈칸 경계·무결성 기계검증.
09_NLP_빈칸경계_v1 위반 후보를 플래그(LLM 검증 전 1차 스크리닝).
"""
import os
import re
import sys
from collections import Counter

DIR = "H:/내 드라이브/outputs/02_cards_v37"
CLOZE = re.compile(r"\{\{c\d+::(.*?)\}\}", re.S)
# 고정밀: 목적격조사 을/를 종결만(명사 오탐 적음) / 연결어미 / 관형형 종결
BARE_JOSA = ("을", "를")
ENDIANGS = ("므로", "하여", "하면서", "한바", "으며", "이며", "거나", "고서", "면서", "는데", "는바", "어서", "지만")
GWANHYEONG = ("관한", "대한", "위한", "따른", "인한", "관하여", "대하여", "있어서")
PROPER = re.compile(r"(?<![가-힣])([갑병정무])(?![가-힣])|[XYZ]\s?토지|[XYZ]\s?건물|\d{1,4}만\s?원")


def blank_issues(b: str):
    b = re.sub(r"<[^>]+>", "", b).strip()
    issues = []
    ws = b.split()
    if not ws:
        return ["빈"]
    last = ws[-1]
    if len(last) >= 2 and last[-1] in BARE_JOSA and last not in ("경우",):
        # '범위를' 같은 격조사 종결 (단 '~의' 명사 'X의'는 허용폭 있어 길이체크)
        issues.append(f"조사종결:{last}")
    if any(last.endswith(e) for e in ENDIANGS):
        issues.append(f"연결어미:{last}")
    if last in GWANHYEONG:
        issues.append(f"관형종결:{last}")
    if PROPER.search(b):
        issues.append("고유명사의심")
    return issues


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = [f for f in os.listdir(DIR) if f.endswith(".md")]
    tot_blanks = tot_issue = 0
    no_blank_files = []
    issue_kinds = Counter()
    worst = []
    for f in sorted(files):
        txt = open(os.path.join(DIR, f), encoding="utf-8").read()
        blanks = CLOZE.findall(txt)
        if not blanks and "cloze" in txt.lower():
            no_blank_files.append(f)
        fi = 0
        for b in blanks:
            tot_blanks += 1
            iss = blank_issues(b)
            if iss:
                tot_issue += 1
                fi += 1
                for x in iss:
                    issue_kinds[x.split(":")[0]] += 1
        if fi:
            worst.append((fi, f))
    print(f"파일 {len(files)} / 총 빈칸 {tot_blanks} / 경계위반 후보 {tot_issue} ({tot_issue*100//max(tot_blanks,1)}%)")
    print("위반 유형:", dict(issue_kinds))
    print("위반 많은 파일 top10:")
    for n, f in sorted(worst, reverse=True)[:10]:
        print(f"  {n:>4}  {f}")
    if no_blank_files:
        print(f"cloze 표기 있으나 빈칸 0인 파일 {len(no_blank_files)}개:", no_blank_files[:5])


if __name__ == "__main__":
    main()
