#!/usr/bin/env python3
"""교재원문 마크다운의 OCR 깨진 한글 공백 결정론적 복구 (단계 C-deterministic).

OCR 과정에서 단어 내부에 공백이 들어간 케이스를 복구한다:
  "비 례 의 원 칙" → "비례의원칙"

알고리즘:
- 연속된 3개 이상의 단일 한글 음절이 단일 공백으로 구분된 run을 감지
- run 내부의 공백만 제거 (run 외부는 그대로)

주의:
- 결과는 단어 경계가 없어 다소 읽기 어려움 (`비례의원칙의의의`)
- 그러나 원본 그대로보다 훨씬 낫고 검색 품질도 향상됨
- 실제 의미 복원을 위한 word boundary 삽입은 LLM reflow (별도 단계)가 필요

백업: 5.기타/_trash/2026-04-11/_교재원문_pre_cleanC/
idempotent: 재실행해도 안전 (이미 joined된 run은 매치되지 않음)
"""
import sys
import re
import shutil
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브')
TEXTBOOK_ROOT = ROOT / 'sync' / '_교재원문'
BACKUP_ROOT = ROOT / '5.기타' / '_trash' / '2026-04-11' / '_교재원문_pre_cleanC'

FRONTMATTER_PAT = re.compile(r'^(---\n.*?\n---\n)(.*)$', re.DOTALL)

# 3+ consecutive single Korean syllables separated by single space each
# [가-힣] ([가-힣] ){2,} ← 3 이상
OCR_BROKEN_PAT = re.compile(r'[가-힣](?:\s[가-힣]){2,}')


def split_frontmatter(text: str) -> tuple[str, str]:
    m = FRONTMATTER_PAT.match(text)
    if m:
        return m.group(1), m.group(2)
    return '', text


def join_ocr_broken(text: str) -> tuple[str, int]:
    """OCR로 깨진 단일 음절 run을 조인. (new_text, run_count) 반환."""
    runs = [0]

    def replace(m):
        runs[0] += 1
        return m.group(0).replace(' ', '')

    return OCR_BROKEN_PAT.sub(replace, text), runs[0]


def backup_file(src: Path, backup_root: Path):
    rel = src.relative_to(TEXTBOOK_ROOT)
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def process_file(path: Path, dry_run: bool = False, do_backup: bool = True) -> dict:
    orig = path.read_text(encoding='utf-8')
    frontmatter, body = split_frontmatter(orig)

    # 본문만 처리 (frontmatter는 보존)
    new_body, run_count = join_ocr_broken(body)

    new_text = frontmatter + new_body
    changed = new_text != orig

    if changed and not dry_run:
        if do_backup:
            backup_file(path, BACKUP_ROOT)
        path.write_text(new_text, encoding='utf-8')

    return {
        'path': str(path),
        'orig_size': len(orig),
        'new_size': len(new_text),
        'run_count': run_count,
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
    print()

    total_orig = 0
    total_new = 0
    total_runs = 0
    changed_count = 0
    errors = []

    for f in targets:
        try:
            stats = process_file(f, dry_run=args.dry_run, do_backup=not args.no_backup)
            total_orig += stats['orig_size']
            total_new += stats['new_size']
            total_runs += stats['run_count']
            if stats['changed']:
                changed_count += 1
        except Exception as e:
            errors.append((f, str(e)))

    pct = (total_orig - total_new) / total_orig * 100 if total_orig > 0 else 0
    print(f'=== 요약 ===')
    print(f'  처리: {len(targets)}')
    print(f'  변경: {changed_count}')
    print(f'  총 복구된 run: {total_runs}')
    print(f'  원본: {total_orig:,} chars ({total_orig/1024:.0f} KB)')
    print(f'  정리: {total_new:,} chars ({total_new/1024:.0f} KB)')
    print(f'  감소: {total_orig - total_new:,} chars ({pct:.2f}%)')
    if errors:
        print(f'  에러: {len(errors)}')
        for f, e in errors[:5]:
            print(f'    {f}: {e}')


if __name__ == '__main__':
    main()
