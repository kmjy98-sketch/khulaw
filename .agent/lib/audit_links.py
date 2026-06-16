#!/usr/bin/env python3
"""민법 노트 폴더 내부·교차 링크 감사 (교재원문 제외).

교재 위키링크까지 포함한 감사는 audit_textbook_links.py 를 사용한다.
"""
import sys
import re
from pathlib import Path
from collections import defaultdict


def main() -> int:
    sys.stdout.reconfigure(encoding='utf-8')

    roots = [
        'sync/민법/총칙',
        'sync/민법/물권',
        'sync/민법/담보물권',
        'sync/민법/채권총론',
        'sync/민법/채권각론',
    ]
    all_notes: dict[str, str] = {}
    # 목차 파일(sync/민법/ 직속) 포함
    for f in Path('sync/민법').glob('*.md'):
        all_notes[f.stem] = str(f).replace('\\', '/')
    for r in roots:
        for f in Path(r).glob('*.md'):
            all_notes[f.stem] = str(f).replace('\\', '/')

    print(f'전체 민법 노트: {len(all_notes)}개')

    link_pat = re.compile(r'\[\[([^\]|#]+)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]')
    broken: defaultdict[str, list[str]] = defaultdict(list)
    total_links = 0
    intra_folder = 0
    inter_folder = 0
    out_links: defaultdict[str, int] = defaultdict(int)
    in_links: defaultdict[str, int] = defaultdict(int)

    for r in roots:
        folder = Path(r).name
        for f in Path(r).glob('*.md'):
            text = f.read_text(encoding='utf-8')
            links = link_pat.findall(text)
            for link in links:
                link = link.strip()
                total_links += 1
                out_links[f.stem] += 1
                if link in all_notes:
                    in_links[link] += 1
                    target_folder = Path(all_notes[link]).parent.name
                    if target_folder == folder:
                        intra_folder += 1
                    else:
                        inter_folder += 1
                else:
                    broken[f.stem].append(link)

    print(f'전체 위키링크: {total_links}')
    print(f'  폴더 내부: {intra_folder}, 폴더 교차: {inter_folder}')
    print(f'  깨진 링크: {sum(len(v) for v in broken.values())}')
    print()

    isolated = [n for n in all_notes if in_links.get(n, 0) == 0]
    print(f'고립 노트(받는 링크 0개): {len(isolated)}')
    for n in sorted(isolated):
        folder = Path(all_notes[n]).parent.name
        print(f'  - [{folder}] {n}')
    print()

    print('=== 깨진 링크 상위 30개 ===')
    for note, links in sorted(broken.items(), key=lambda x: -len(x[1]))[:30]:
        print(f'  {note}: {len(links)}개 - 예: {links[:3]}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
