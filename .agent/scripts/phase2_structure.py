#!/usr/bin/env python3
"""
phase2_structure.py - Phase 2: 규칙 기반 구조화

기능:
  1. 결론 키워드 볼드 (성립O, 취득X 등)
  2. 조문번호 볼드 (제NNN조 → **제NNN조**)
  3. 번호 항목 리스트화 (①②③ → - ① ...)

Phase 1 (reflow_batch.py) 적용 후 실행.
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime
from collections import Counter

if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# 결론 키워드 볼드
CONCLUSION_PATTERNS = [
    (re.compile(r'(?<!\*)성립O(?!\*)'), '**성립O**'),
    (re.compile(r'(?<!\*)성립X(?!\*)'), '**성립X**'),
    (re.compile(r'(?<!\*)성립0(?!\*)'), '**성립O**'),  # 0→O
    (re.compile(r'(?<!\*)취득O(?!\*)'), '**취득O**'),
    (re.compile(r'(?<!\*)취득X(?!\*)'), '**취득X**'),
    (re.compile(r'(?<!\*)인정O(?!\*)'), '**인정O**'),
    (re.compile(r'(?<!\*)인정X(?!\*)'), '**인정X**'),
    (re.compile(r'(?<!\*)가능O(?!\*)'), '**가능O**'),
    (re.compile(r'(?<!\*)가능X(?!\*)'), '**가능X**'),
    (re.compile(r'(?<!\*)포기O(?!\*)'), '**포기O**'),
    (re.compile(r'(?<!\*)포기0(?!\*)'), '**포기O**'),
]

# 조문번호 볼드
STATUTE_BOLD = re.compile(r'(?<!\*)(제\d{1,4}조(?:\s*제\d{1,2}항)?)(?!\*)')

def extract_frontmatter(text):
    if text.startswith('---'):
        end = text.find('---', 3)
        if end != -1:
            fm_end = end + 3
            if fm_end < len(text) and text[fm_end] == '\n': fm_end += 1
            return text[:fm_end], text[fm_end:]
    return '', text

def phase2(body):
    changes = 0

    # 1. 결론 키워드
    for p, r in CONCLUSION_PATTERNS:
        body, n = p.subn(r, body); changes += n

    # 2. 조문번호 볼드 (콜아웃/헤딩 내부 제외)
    lines = body.split('\n')
    new_lines = []
    in_callout = False
    for line in lines:
        if line.strip().startswith('> [!'):
            in_callout = True
        elif not line.strip().startswith('>'):
            in_callout = False
        if not in_callout and not line.strip().startswith('#'):
            new_line = STATUTE_BOLD.sub(r'**\g<1>**', line)
            if new_line != line: changes += 1
            line = new_line
        new_lines.append(line)
    body = '\n'.join(new_lines)

    # 3. 번호 항목 리스트화
    lines = body.split('\n')
    new_lines = []
    for line in lines:
        s = line.strip()
        if s.startswith('>') or s.startswith('-') or s.startswith('#'):
            new_lines.append(line); continue
        if s and s[0] in '①②③④⑤⑥⑦⑧⑨⑩':
            new_lines.append(f'- {s}'); changes += 1
        else:
            new_lines.append(line)
    body = '\n'.join(new_lines)

    return body, changes

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='cp949') as f:
                text = f.read()
        except:
            return {'file': filepath, 'status': 'error', 'changes': 0}

    fm, body = extract_frontmatter(text)
    body, changes = phase2(body)
    new_text = fm + body

    if new_text == text:
        return {'file': filepath, 'status': 'unchanged', 'changes': 0}

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_text)
    return {'file': filepath, 'status': 'applied', 'changes': changes}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--report', default=None)
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
        files.sort()

    print(f'Phase 2 대상: {len(files)}파일')
    stats = Counter()
    total = 0
    for i, fp in enumerate(files):
        r = process_file(fp)
        stats[r['status']] += 1
        total += r['changes']
        if (i+1) % 100 == 0:
            print(f'  [{i+1}/{len(files)}] {total} changes')

    print(f'\n완료: {dict(stats)}')
    print(f'총 변경: {total}')

    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': datetime.now().isoformat(), 'stats': dict(stats), 'total': total}, f, ensure_ascii=False, indent=2)
        print(f'리포트: {args.report}')

if __name__ == '__main__':
    main()
