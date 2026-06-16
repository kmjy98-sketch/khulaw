#!/usr/bin/env python3
"""
phase25_prejoin.py - Phase 2.5: LLM 전 사전 구조화

Phase 1+2 이후, Phase 3(LLM) 전에 실행. LLM 작업량을 줄이기 위한 규칙 기반 전처리.

기능:
  1. 끊긴 문장 재접합 (줄 끝 한글 + 다음 줄 시작 한글 → 이어붙이기)
  2. 각주 N) → [^N] 마크다운 각주 변환
  3. 헤딩에서 각주 분리 (### 제목[^N] → ### 제목 + 다음줄 [^N])
  4. 추가 OCR 잔여물 제거 (저|→제, 저I→제, 回=1 등)
  5. [논거] → **논거:** 변환
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

# ─── 1. 끊긴 문장 재접합 ───
# 줄 끝이 한글(조사/어미 아닌 것)이고 다음 줄 시작이 한글이면 이어붙이기
# 단, 다음 줄이 리스트/헤딩/콜아웃/빈줄이면 스킵
def rejoin_lines(body):
    lines = body.split('\n')
    joined = []
    changes = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        # 현재 줄이 비어있거나 특수 줄이면 그대로
        if not line.strip() or line.strip().startswith(('#', '>', '-', '|', '```', '---', '- ')):
            joined.append(line)
            i += 1
            continue
        # 다음 줄이 있고, 현재 줄 끝이 한글이고, 다음 줄 시작이 한글이면 접합
        while (i + 1 < len(lines)
               and line.rstrip()
               and re.search(r'[가-힣]$', line.rstrip())
               and lines[i+1].strip()
               and re.match(r'^[가-힣]', lines[i+1].strip())
               and not lines[i+1].strip().startswith(('#', '>', '-', '|', '```', '---'))
               and not re.match(r'^\s*$', lines[i+1])):
            line = line.rstrip() + lines[i+1].strip()
            changes += 1
            i += 1
        joined.append(line)
        i += 1
    return '\n'.join(joined), changes

# ─── 2. 각주 N) → [^N] 변환 ───
# 본문 내 참조: 텍스트N) → 텍스트[^N]
# 정의부: 줄 시작 N) 텍스트 → [^N]: 텍스트
FOOTNOTE_REF = re.compile(r'(?<=[가-힣A-Za-z)\]」])(\d{1,3})\)')
FOOTNOTE_DEF = re.compile(r'^(\d{1,3})\)\s*(.+)$', re.MULTILINE)

def convert_footnotes(body):
    changes = 0
    # 정의부 먼저 (줄 시작 N) → [^N]:)
    def repl_def(m):
        nonlocal changes
        changes += 1
        return f'[^{m.group(1)}]: {m.group(2)}'
    body = FOOTNOTE_DEF.sub(repl_def, body)

    # 참조부 (인라인 N) → [^N])
    def repl_ref(m):
        nonlocal changes
        changes += 1
        return f'[^{m.group(1)}]'
    body = FOOTNOTE_REF.sub(repl_ref, body)
    return body, changes

# ─── 3. 헤딩에서 각주 분리 ───
HEADING_FN = re.compile(r'^(#{1,6} .+?)(\[\^\d+\])$', re.MULTILINE)

def separate_heading_footnotes(body):
    changes = 0
    def repl(m):
        nonlocal changes
        changes += 1
        return f'{m.group(1)}\n\n{m.group(2)}'
    body = HEADING_FN.sub(repl, body)
    return body, changes

# ─── 4. 추가 OCR 잔여물 ───
EXTRA_OCR = [
    (re.compile(r'저\|(\d)'), r'제\g<1>'),      # 저|3 → 제3
    (re.compile(r'저I(\d)'), r'제\g<1>'),       # 저I3 → 제3
    (re.compile(r'저P(\d)'), r'제\g<1>'),       # 저P3 → 제3
    (re.compile(r'回=\d'), ''),                  # 回=1 제거
    (re.compile(r't각=\d'), ''),                 # t각=1 제거
    (re.compile(r'f괔=\d'), ''),                 # f괔=1 제거
    (re.compile(r'\[논거\]'), '**논거:**'),       # [논거] → **논거:**
    (re.compile(r'^\s*\[?돈절\]?\s*$', re.MULTILINE), ''),  # [돈절], 돈절
    (re.compile(r'^\s*\[?돈접\]?\s*$', re.MULTILINE), ''),  # 돈접
    (re.compile(r'^\s*LawS\w*\s+Civil\s+Act\s*$', re.MULTILINE), ''),
]

def extra_ocr_cleanup(body):
    changes = 0
    for p, r in EXTRA_OCR:
        body, n = p.subn(r, body)
        changes += n
    return body, changes


# ═══════════════════════════════════════
def extract_frontmatter(text):
    if text.startswith('---'):
        end = text.find('---', 3)
        if end != -1:
            fm_end = end + 3
            if fm_end < len(text) and text[fm_end] == '\n': fm_end += 1
            return text[:fm_end], text[fm_end:]
    return '', text

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
    total = 0

    body, c = extra_ocr_cleanup(body); total += c
    body, c = convert_footnotes(body); total += c
    body, c = separate_heading_footnotes(body); total += c
    body, c = rejoin_lines(body); total += c
    # 빈 줄 정리
    body = re.sub(r'\n{3,}', '\n\n', body)

    new_text = fm + body
    if new_text == text:
        return {'file': filepath, 'status': 'unchanged', 'changes': 0}

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_text)
    return {'file': filepath, 'status': 'applied', 'changes': total}


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

    print(f'Phase 2.5 대상: {len(files)}파일')
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

if __name__ == '__main__':
    main()
