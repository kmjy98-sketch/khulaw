#!/usr/bin/env python3
"""교재 위키링크 전용 감사 — 정리노트에서 sync/_교재원문/ 하위를 가리키는 링크 검증."""
import sys
import re
from pathlib import Path
from collections import defaultdict


def build_indexes() -> tuple[dict[str, list[str]], set[str]]:
    stem_index: dict[str, list[str]] = defaultdict(list)
    path_index: set[str] = set()
    for pat in ['sync/민법/**/*.md', 'sync/형법/**/*.md', 'sync/헌법/**/*.md', 'sync/_교재원문/**/*.md']:
        for f in Path('.').glob(pat):
            rel = f.relative_to(Path('sync')).as_posix()
            rel_noext = rel[:-3] if rel.endswith('.md') else rel
            stem_index[f.stem].append(rel_noext)
            path_index.add(rel_noext)
    return stem_index, path_index


def resolve(link: str, stem_index: dict[str, list[str]], path_index: set[str]) -> bool:
    """Obsidian wikilink resolution.

    - 경로 포함 링크(`/` 있음) → path_index 일치 확인
    - stem 링크 → stem_index 존재 확인
    """
    if '/' in link:
        return link in path_index
    return link in stem_index


def main() -> int:
    sys.stdout.reconfigure(encoding='utf-8')

    stem_index, path_index = build_indexes()
    total_notes = sum(len(v) for v in stem_index.values())
    print(f'전체 노트(교재원문 포함): {total_notes}개')

    link_pat = re.compile(r'\[\[([^\]|#]+)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]')
    broken: defaultdict[str, list[str]] = defaultdict(list)
    valid = 0

    roots = ['sync/민법', 'sync/형법', 'sync/헌법']
    for root in roots:
        for f in Path(root).rglob('*.md'):
            if f.stem.startswith('_'):
                continue
            text = f.read_text(encoding='utf-8')
            for link in link_pat.findall(text):
                link = link.strip()
                if not (re.search(r'_ch\d+', link) or '교재목차' in link):
                    continue
                if resolve(link, stem_index, path_index):
                    valid += 1
                else:
                    broken[f.stem].append(link)

    total_broken = sum(len(v) for v in broken.values())
    print(f'교재 위키링크: valid={valid}, broken={total_broken}')

    if broken:
        print()
        print('=== 깨진 교재 링크 상위 15개 ===')
        for note, links in sorted(broken.items(), key=lambda x: -len(x[1]))[:15]:
            print(f'  {note}: {len(links)}개 — {links[:3]}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
