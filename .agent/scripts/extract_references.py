#!/usr/bin/env python3
"""
extract_references.py - 교재원문에서 조문/판례 참조 추출

기능:
  1. 조문 추출: 제N조, §N 패턴
  2. 판례 추출: 대판 YYYY.M.D. NN다NNNN 패턴
  3. 빈도 집계 및 JSON 출력

사용법:
  python extract_references.py --target <file_or_dir> --output <output.json>
"""

import os
import re
import sys
import json
import argparse
from collections import Counter

if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# ─── 조문 패턴 ───
STATUTE_PATTERNS = [
    # 제366조, 제100조 제2항
    re.compile(r'제(\d{1,4})조(?:\s*(?:제(\d{1,2})항))?'),
    # §366, §287
    re.compile(r'§(\d{1,4})'),
]

# ─── 판례 패턴 ───
# 사건번호 "꼬리" 부분: 다/다카/도/두/누/마/허/재/그 + 숫자, 또는 헌가/헌바/헌마/헌라/헌나/헌사 + 숫자
CASE_NUM_RE = r'(\d{2,4}(?:다카|다|도|두|누|마|허|재|그|초|초기|초재|모)\d{2,6}|\d{2,4}헌(?:가|바|마|라|나|사|아)\d{2,6})'
CASE_PATTERNS = [
    # 대판/대결/헌재(전합) 2013.9.12. 2013다43345
    re.compile(r'(?:대판|대결|대법원|헌재|현재)(?:\(전합\))?\s*(\d{4}\.\d{1,2}\.\d{1,2})[.,]?\s*' + CASE_NUM_RE),
    # (대판 1996.4.26. 95다52864)
    re.compile(r'\((?:대판|대결|대법원|헌재|현재)(?:\(전합\))?\s*(\d{4}\.\d{1,2}\.\d{1,2})[.,]?\s*' + CASE_NUM_RE + r'\)'),
    # 단독 판례번호: 95다52864 / 2010도3023 / 2018헌마1100
    re.compile(CASE_NUM_RE),
]

# 법률명 매핑 (조문 → 법률)
STATUTE_TO_LAW = {
    range(1, 1119): '민법',
    range(1, 373): '형법',  # 형법 조문은 민법과 겹치므로 맥락 필요
}


def extract_statutes(text: str) -> list[dict]:
    """조문 참조 추출."""
    statutes = []
    for pat in STATUTE_PATTERNS:
        for m in pat.finditer(text):
            article = m.group(1)
            paragraph = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            ref = f'제{article}조'
            if paragraph:
                ref += f' 제{paragraph}항'
            statutes.append({
                'article': int(article),
                'paragraph': int(paragraph) if paragraph else None,
                'ref': ref,
                'position': m.start(),
            })
    return statutes


def extract_cases(text: str) -> list[dict]:
    """판례 참조 추출."""
    cases = []
    seen = set()
    # 먼저 상세 패턴(날짜+번호)으로 추출
    for pat in CASE_PATTERNS[:2]:
        for m in pat.finditer(text):
            date = m.group(1)
            number = m.group(2)
            key = number
            if key not in seen:
                seen.add(key)
                cases.append({
                    'date': date,
                    'number': number,
                    'full': f'대판 {date} {number}',
                    'position': m.start(),
                })
    # 단독 번호 패턴 (이미 추출된 것 제외)
    for m in CASE_PATTERNS[2].finditer(text):
        number = m.group(1)
        if number not in seen:
            seen.add(number)
            cases.append({
                'number': number,
                'date': None,
                'full': number,
                'position': m.start(),
            })
    return cases


def process_file(filepath: str) -> dict:
    """파일에서 조문/판례 추출."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='cp949') as f:
            text = f.read()

    statutes = extract_statutes(text)
    cases = extract_cases(text)

    # 빈도 집계
    statute_freq = Counter(s['ref'] for s in statutes)
    case_freq = Counter(c['number'] for c in cases)

    return {
        'file': filepath,
        'statutes': {
            'total': len(statutes),
            'unique': len(statute_freq),
            'frequency': dict(statute_freq.most_common()),
            'details': statutes[:10],  # 처음 10건만
        },
        'cases': {
            'total': len(cases),
            'unique': len(case_freq),
            'frequency': dict(case_freq.most_common()),
            'details': cases,
        },
    }


def main():
    parser = argparse.ArgumentParser(description='조문/판례 참조 추출')
    parser.add_argument('--target', required=True)
    parser.add_argument('--output', default=None)
    args = parser.parse_args()

    target = os.path.abspath(args.target)

    if os.path.isfile(target):
        files = [target]
    else:
        files = []
        for root, dirs, fnames in os.walk(target):
            dirs[:] = [d for d in dirs if not d.startswith('_')]
            for fn in fnames:
                if fn.endswith('.md') and not fn.startswith('_'):
                    files.append(os.path.join(root, fn))

    all_statutes = Counter()
    all_cases = Counter()
    all_case_details = {}
    results = []

    for fp in sorted(files):
        result = process_file(fp)
        results.append(result)
        all_statutes.update(result['statutes']['frequency'])
        all_cases.update(result['cases']['frequency'])
        for c in result['cases']['details']:
            if c['number'] not in all_case_details:
                all_case_details[c['number']] = c

    # 요약 출력
    print(f'파일 수: {len(files)}')
    print(f'\n=== 조문 참조 ===')
    print(f'고유 조문: {len(all_statutes)}')
    print(f'상위 20:')
    for ref, cnt in all_statutes.most_common(20):
        print(f'  {ref}: {cnt}회')

    print(f'\n=== 판례 참조 ===')
    print(f'고유 판례: {len(all_cases)}')
    print(f'상위 20:')
    for num, cnt in all_cases.most_common(20):
        detail = all_case_details.get(num, {})
        date = detail.get('date', '?')
        print(f'  {num} ({date}): {cnt}회')

    if args.output:
        report = {
            'total_files': len(files),
            'statute_summary': {
                'unique': len(all_statutes),
                'top50': dict(all_statutes.most_common(50)),
            },
            'case_summary': {
                'unique': len(all_cases),
                'top50': dict(all_cases.most_common(50)),
                'details': {k: v for k, v in list(all_case_details.items())[:50]},
            },
            'per_file': results,
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f'\n리포트 저장: {args.output}')


if __name__ == '__main__':
    main()
