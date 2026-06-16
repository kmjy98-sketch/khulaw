#!/usr/bin/env python3
"""교재원문 마크다운 파일의 10천간 한자 → 한글 변환 (단계 B).

매핑 (10천간만):
  甲→갑, 乙→을, 丙→병, 丁→정, 戊→무,
  己→기, 庚→경, 辛→신, 壬→임, 癸→계

범위: 본문 + frontmatter 전체 (사용자 결정)
위험 낮음: Hanja 문자와 한글은 별개 유니코드 → 한글 "갑오경장"은 영향 없음
"""
import sys
import re
import shutil
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브')
TEXTBOOK_ROOT = ROOT / 'sync' / '_교재원문'
BACKUP_ROOT = ROOT / '5.기타' / '_trash' / '2026-04-11' / '_교재원문_pre_cleanB'

CHEONGAN_MAP = {
    '甲': '갑',
    '乙': '을',
    '丙': '병',
    '丁': '정',
    '戊': '무',
    '己': '기',
    '庚': '경',
    '辛': '신',
    '壬': '임',
    '癸': '계',
}


def convert_hanja(text: str) -> tuple[str, dict[str, int]]:
    """텍스트의 10천간 한자를 한글로 변환. (new_text, count_per_char) 반환."""
    counts = {}
    for hanja, hangul in CHEONGAN_MAP.items():
        count = text.count(hanja)
        if count:
            counts[hanja] = count
            text = text.replace(hanja, hangul)
    return text, counts


def backup_file(src: Path, backup_root: Path):
    """원본 파일을 _trash 하위로 복사."""
    rel = src.relative_to(TEXTBOOK_ROOT)
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def process_file(path: Path, dry_run: bool = False, do_backup: bool = True) -> dict:
    """단일 파일 처리."""
    orig = path.read_text(encoding='utf-8')
    new_text, counts = convert_hanja(orig)

    total_replaced = sum(counts.values())
    changed = total_replaced > 0

    if changed and not dry_run:
        if do_backup:
            backup_file(path, BACKUP_ROOT)
        path.write_text(new_text, encoding='utf-8')

    return {
        'path': str(path),
        'counts': counts,
        'total_replaced': total_replaced,
        'changed': changed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--no-backup', action='store_true')
    parser.add_argument('--sample', type=int, default=0)
    parser.add_argument('paths', nargs='*')
    args = parser.parse_args()

    if args.paths:
        targets = [Path(p).resolve() for p in args.paths]
    else:
        targets = []
        for f in TEXTBOOK_ROOT.rglob('*.md'):
            if '_trash' in f.parts:
                continue
            if f.name == '_교재목차.md':
                continue
            targets.append(f)

    if args.sample > 0:
        targets = targets[:args.sample]

    print(f'대상: {len(targets)}개 파일')
    print(f'모드: {"DRY-RUN" if args.dry_run else "EXECUTE"}')
    print(f'백업: {"NO" if args.no_backup else str(BACKUP_ROOT)}')
    print()

    changed_count = 0
    total_replaced = 0
    per_char_total = {k: 0 for k in CHEONGAN_MAP}
    errors = []

    for f in targets:
        try:
            stats = process_file(f, dry_run=args.dry_run, do_backup=not args.no_backup)
            if stats['changed']:
                changed_count += 1
                total_replaced += stats['total_replaced']
                for k, v in stats['counts'].items():
                    per_char_total[k] += v
        except Exception as e:
            errors.append((f, str(e)))

    print(f'=== 요약 ===')
    print(f'  처리: {len(targets)}')
    print(f'  변경: {changed_count}')
    print(f'  총 치환: {total_replaced}')
    print(f'  에러: {len(errors)}')
    print()
    print(f'=== 한자별 치환 횟수 ===')
    for hanja, hangul in CHEONGAN_MAP.items():
        count = per_char_total[hanja]
        if count:
            print(f'  {hanja} → {hangul}: {count:,}')
    if errors:
        print()
        print('=== 에러 ===')
        for f, e in errors[:5]:
            print(f'  {f}: {e}')


if __name__ == '__main__':
    main()
