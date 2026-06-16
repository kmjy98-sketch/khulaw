#!/usr/bin/env python3
"""민법 전체 목차(MOC) 자동 생성."""
import sys
import re
from pathlib import Path
from collections import defaultdict

import yaml

FOLDERS = [
    ('총칙', 'sync/민법/총칙'),
    ('물권', 'sync/민법/물권'),
    ('담보물권', 'sync/민법/담보물권'),
    ('채권총론', 'sync/민법/채권총론'),
    ('채권각론', 'sync/민법/채권각론'),
]

FM_PAT = re.compile(r'^---\n(.*?)\n---', re.DOTALL)


def parse_note(f: Path) -> dict:
    text = f.read_text(encoding='utf-8')
    m = FM_PAT.search(text)
    fm = {}
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            fm = {}
    h_match = re.search(r'^# (.+)$', text, re.MULTILINE)
    title = h_match.group(1).strip() if h_match else f.stem
    return {
        'stem': f.stem,
        'title': title,
        'freq': fm.get('쟁점빈도', ''),
        'articles': fm.get('관련조문', []),
        'aliases': fm.get('aliases', []),
    }


def freq_rank(freq) -> int:
    if isinstance(freq, str):
        return freq.count('★')
    return 0


def load_all_notes() -> dict[str, list[dict]]:
    all_notes: dict[str, list[dict]] = {}
    for name, path in FOLDERS:
        notes = []
        for f in sorted(Path(path).glob('*.md')):
            if f.stem.startswith('_'):
                continue
            notes.append(parse_note(f))
        all_notes[name] = notes
    return all_notes


def render(all_notes: dict[str, list[dict]]) -> str:
    top: list[tuple[str, dict]] = []
    for folder, notes in all_notes.items():
        for n in notes:
            top.append((folder, n))
    top.sort(key=lambda x: (-freq_rank(x[1]['freq']), x[1]['stem']))

    lines: list[str] = []
    lines.append('---')
    lines.append('tags: [민법, MOC, 통합목차]')
    lines.append('aliases: [민법전체목차, 민법MOC, 민법_목차]')
    lines.append('---')
    lines.append('')
    lines.append('# 민법 전체 Map of Content')
    lines.append('')
    lines.append(f'> **총 노트 수**: {sum(len(v) for v in all_notes.values())}개 (5폴더)')
    lines.append('> **소스**: 송영곤 《민사법쟁점노트》8판 + 《논점민법강의》12판')
    lines.append('> **재작성일**: 2026-04-10')
    lines.append('')
    lines.append('## 폴더별 노트 수')
    lines.append('')
    lines.append('| 폴더 | 노트 수 | 폴더 목차 |')
    lines.append('|------|:---:|------|')
    for name in all_notes:
        cnt = len(all_notes[name])
        lines.append(f'| {name} | {cnt} | [[_민법{name}_목차]] |')
    lines.append('')
    lines.append('---')
    lines.append('')

    lines.append('## 빈출 쟁점 Top 30 (★★★)')
    lines.append('')
    lines.append('| 순위 | 쟁점 | 폴더 | 빈도 | 관련조문 |')
    lines.append('|:---:|------|------|:---:|------|')
    top3 = [(f, n) for f, n in top if freq_rank(n['freq']) >= 3]
    for i, (folder, n) in enumerate(top3[:30], 1):
        arts = ', '.join(n['articles']) if n['articles'] else ''
        lines.append(f'| {i} | [[{n["stem"]}]] | {folder} | {n["freq"]} | {arts} |')
    lines.append('')
    lines.append('---')
    lines.append('')

    for folder, notes in all_notes.items():
        lines.append(f'## {folder} ({len(notes)}개)')
        lines.append('')
        notes_sorted = sorted(notes, key=lambda n: (-freq_rank(n['freq']), n['stem']))
        for n in notes_sorted:
            arts = ', '.join(n['articles']) if n['articles'] else ''
            freq = n['freq'] if n['freq'] else ''
            if arts:
                lines.append(f'- [[{n["stem"]}]] {freq} — {arts}')
            else:
                lines.append(f'- [[{n["stem"]}]] {freq}')
        lines.append('')

    lines.append('---')
    lines.append('')
    lines.append('## 인접 폴더 관계 (교차 링크 권장)')
    lines.append('')
    lines.append('- **총칙 ↔ 물권**: 의사표시·법률행위 → 부동산 물권변동 (등기원인)')
    lines.append('- **총칙 ↔ 채권총론**: 무효·취소 → 부당이득 반환')
    lines.append('- **물권 ↔ 담보물권**: 점유·소유권 → 저당권·유치권')
    lines.append('- **담보물권 ↔ 채권총론**: 보증·연대 → 구상권·변제자대위')
    lines.append('- **채권총론 ↔ 채권각론**: 채무불이행·해제 → 매매·임대차')
    lines.append('- **물권 ↔ 채권각론**: 점유 → 부당이득(점유자 과실수취권)')

    return '\n'.join(lines)


def main() -> int:
    sys.stdout.reconfigure(encoding='utf-8')
    all_notes = load_all_notes()
    content = render(all_notes)
    out = Path('sync/민법/_민법전체목차.md')
    out.write_text(content, encoding='utf-8')

    top3_count = sum(
        1 for notes in all_notes.values() for n in notes if freq_rank(n['freq']) >= 3
    )
    print(f'Generated: {out}')
    print(f'  {sum(len(v) for v in all_notes.values())} notes, {top3_count} ★★★ rank')
    return 0


if __name__ == '__main__':
    sys.exit(main())
