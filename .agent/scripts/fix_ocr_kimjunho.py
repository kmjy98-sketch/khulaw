#!/usr/bin/env python3
"""김준호_민법강의 파일 OCR 오류 수정.

수정 대상:
1. 법령 한자 약어 OCR 오류 제거 (봏, 뽀, 봏법 계열 괄호 패턴)
2. 오탈자 수정: '민법종칙' → '민법총칙'
"""
import sys
import os
import re
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(vp('sync', '_교재원문', '민법', '강혜림_민법1'))

# 법령 약어 OCR 패턴 목록 — 앞에 한국어 법령명이 있고, 괄호 안 한자 약어가 OCR 손상된 패턴
# 공통 특성: 끝이 "법)" 또는 "법j" 이며, 중간에 비한글 OCR 잡음 포함
_ABBR_CORE = r'(?:봏|뽀|봏법|Z봏|쯔봏|쯔봏|찌봏|씨봏|X봏|繼봏|體봏|殺:봏|끊:봏|;쩌봏|Z&|Z：|C：뽀|Q：흐볗|殺삖|G뿨:I|끊器)'
SIMPLE_ABBR_RE = re.compile(
    r'\s?[(（][^)）\n]{0,15}' + _ABBR_CORE + r'[^)）\n]{0,10}법?[jj]?[^)）\n]{0,5}[)）]'
)

# 괄호 안 비한글 OCR 잡음이 포함된 법 약어 패턴 (더 넓은 범위)
# 조건: "(xxx 법)" 형태이며, xxx에 器, ：, &, 뀌: 등이 포함
BROAD_ABBR_RE = re.compile(
    r'[(（][^)）\n]{0,5}(?:器|뀌：껺|省업갈|끊器)[^)）\n]{0,5}법[^)）\n]{0,3}[)）]'
)

# 인라인 OCR 잡음 패턴 (괄호 밖)
# "유실물법省업갈[^N]" 에서 省업갈 제거 (뒤에 각주 마커가 오는 경우)
INLINE_NOISE_RE = re.compile(r'省업갈(?=\[\^)')

TYPO_FIXES = [
    ('민법종칙', '민법총칙'),
]


def fix_file(path: Path, dry_run: bool = False) -> dict:
    original = path.read_text(encoding='utf-8')
    text = original
    changes = []

    new_text, n1 = SIMPLE_ABBR_RE.subn('', text)
    if n1 > 0:
        changes.append(f'  법령약어(봏계열): {n1}개')
        text = new_text

    new_text, n2 = BROAD_ABBR_RE.subn('', text)
    if n2 > 0:
        changes.append(f'  법령약어(器/뀌계열): {n2}개')
        text = new_text

    new_text, n3 = INLINE_NOISE_RE.subn('', text)
    if n3 > 0:
        changes.append(f'  인라인잡음(省업갈): {n3}개')
        text = new_text

    for wrong, correct in TYPO_FIXES:
        count = text.count(wrong)
        if count > 0:
            text = text.replace(wrong, correct)
            changes.append(f'  오탈자: {repr(wrong)} → {repr(correct)} ({count}개)')

    if text != original:
        if not dry_run:
            path.write_text(text, encoding='utf-8')
        return {'file': path.name, 'changed': True, 'changes': changes}
    return {'file': path.name, 'changed': False, 'changes': []}


def main():
    dry_run = '--dry-run' in sys.argv
    mode_label = '[DRY-RUN]' if dry_run else '[수정]'

    files = sorted(BASE.glob('*_김준호_민법강의.md'))
    print(f'{mode_label} 대상 파일: {len(files)}개')

    changed_count = 0
    for f in files:
        result = fix_file(f, dry_run=dry_run)
        if result['changed']:
            changed_count += 1
            print(f'{mode_label} {result["file"]}')
            for change in result['changes']:
                print(change)

    print(f'\n완료: {changed_count}/{len(files)}개 파일 수정됨')


if __name__ == '__main__':
    main()
