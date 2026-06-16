#!/usr/bin/env python3
"""정리노트 frontmatter의 cross-domain alias·tag에 과목 prefix 추가.

문제:
- §13, §117 등 § 조문 alias가 민법·형법·헌법에 동일하게 등장하여 Obsidian이 자동 연결
- "총론" tag가 형법·헌법 양쪽에 등장
- "착오" tag가 민법·형법 양쪽에 등장
- "§117" tag가 민법·헌법 양쪽에 등장

해결:
- 폴더 기준으로 과목 prefix 추가:
  - 민법 노트의 § alias → 민§N
  - 형법 노트의 § alias → 형§N
  - 헌법 노트의 § alias → 헌§N
  - "총론" tag (형법) → 형총론
  - "총론" tag (헌법) → 헌총론
  - "착오" tag (민법) → 민착오
  - "착오" tag (형법) → 형착오

idempotent: 이미 prefix가 있으면 건너뜀
"""
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync')
SUBJ_PREFIX = {'민법': '민', '형법': '형', '헌법': '헌'}

# Cross-domain로 식별된 alias·tag (수동 식별 결과)
CROSS_ALIASES = {
    '§1', '§10', '§103', '§111', '§112', '§113', '§114', '§117', '§118',
    '§13', '§17', '§22', '§25', '§27', '§31', '§32', '§34',
    '명확성원칙', '죄형법정주의',
}
CROSS_TAGS = {'§117', '착오', '총론'}

# alias 형식 변환: §13 → 민§13
def transform_alias(alias: str, subj: str) -> str:
    prefix = SUBJ_PREFIX[subj]
    if alias in CROSS_ALIASES:
        # 이미 prefix 있는지 확인
        if alias.startswith(prefix):
            return alias
        return prefix + alias
    return alias


def transform_tag(tag: str, subj: str) -> str:
    prefix = SUBJ_PREFIX[subj]
    if tag in CROSS_TAGS:
        if tag.startswith(prefix):
            return tag
        return prefix + tag
    return tag


def process_note(f: Path, subj: str, dry_run: bool = False) -> tuple[bool, list[str]]:
    """노트의 frontmatter aliases·tags 변환. (changed, log)"""
    text = f.read_text(encoding='utf-8')
    fm_pat = re.compile(r'^(---\n)(.*?)(\n---)', re.DOTALL)
    m = fm_pat.match(text)
    if not m:
        return False, []
    head, fm, tail = m.group(1), m.group(2), m.group(3)
    log = []
    new_fm = fm

    # tags 변환
    tag_pat = re.compile(r'(tags:\s*\[)([^\]]+)(\])')
    tag_m = tag_pat.search(new_fm)
    if tag_m:
        old_tags = [t.strip() for t in tag_m.group(2).split(',')]
        new_tags = [transform_tag(t, subj) for t in old_tags]
        if old_tags != new_tags:
            new_inner = ', '.join(new_tags)
            new_fm = new_fm[:tag_m.start()] + tag_m.group(1) + new_inner + tag_m.group(3) + new_fm[tag_m.end():]
            log.append(f'tags: {old_tags} → {new_tags}')

    # aliases 변환
    alias_pat = re.compile(r'(aliases:\s*\[)([^\]]+)(\])')
    alias_m = alias_pat.search(new_fm)
    if alias_m:
        old_aliases = [a.strip() for a in alias_m.group(2).split(',')]
        new_aliases = [transform_alias(a, subj) for a in old_aliases]
        if old_aliases != new_aliases:
            new_inner = ', '.join(new_aliases)
            new_fm = new_fm[:alias_m.start()] + alias_m.group(1) + new_inner + alias_m.group(3) + new_fm[alias_m.end():]
            log.append(f'aliases: {old_aliases} → {new_aliases}')

    if new_fm != fm:
        new_text = head + new_fm + tail + text[m.end():]
        if not dry_run:
            f.write_text(new_text, encoding='utf-8')
        return True, log
    return False, []


def main():
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print('=== DRY RUN ===\n')

    total_files = 0
    changed_files = 0
    for subj in ['민법', '형법', '헌법']:
        for f in (ROOT / subj).rglob('*.md'):
            if f.stem.startswith('_'):
                continue
            total_files += 1
            changed, log = process_note(f, subj, dry_run=dry_run)
            if changed:
                changed_files += 1
                rel = f.relative_to(ROOT)
                print(f'[{subj}] {rel}')
                for line in log:
                    print(f'  {line}')

    print()
    print(f'=== 요약 ===')
    print(f'  처리 대상: {total_files}파일')
    print(f'  변경된 파일: {changed_files}')


if __name__ == '__main__':
    main()
