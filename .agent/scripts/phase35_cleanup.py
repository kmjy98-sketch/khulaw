"""Phase 3.5 OCR garbage cleanup.

Targets specific OCR artifacts that survived Phase 1-3:
- Broken precedent numbers with footnote markers: "78다[^719]" → "78다719"
- Trailing block char: "...단어■" → "...단어"
- Block char at start of callout line: "> ■ 내용" → "> 내용"
- Fullwidth ASCII: ＝＞＜［］→ =><[]
- Sample/warning markers: "사례 功" → "사례 ①", "주의 材" → "주의 ②"
- 좌同/左同 → 좌동

Usage:
  python phase35_cleanup.py --target <path> [--dry-run] [--verbose]
"""
import os
import re
import sys
import argparse
import difflib
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Rules: (pattern, replacement, description)
RULES = [
    # 1. Broken precedent: "78다[^719]" or "78다[^719])" → "78다719)"
    # Always restore closing paren since these are nearly always inside (대판 ...)
    (re.compile(r'(\d{2,4})다\[\^(\d+)\]\)?'), r'\1다\2)', 'precedent_footnote'),

    # 2. Block char at end of Korean word: "단어■" → "단어"
    (re.compile(r'([가-힣])■(?!\s*[\(\)\[\]\d])'), r'\1', 'trailing_block'),

    # 4. Block char at start of callout line: "> ■ " or "> ■' " → "> "
    (re.compile(r'(^>\s*)■[\'\']?\s+', re.MULTILINE), r'\1', 'leading_block_callout'),

    # 5. Bare ■ at line start (no callout): "■ 내용" → "- 내용"
    (re.compile(r'(?m)^■[\'\']?\s+'), '- ', 'leading_block_line'),

    # 6. Fullwidth ASCII
    (re.compile(r'＝'), '=', 'fw_eq'),
    (re.compile(r'＞'), '>', 'fw_gt'),
    (re.compile(r'＜'), '<', 'fw_lt'),
    (re.compile(r'［'), '[', 'fw_bracket_open'),
    (re.compile(r'］'), ']', 'fw_bracket_close'),
    (re.compile(r'｛'), '(', 'fw_brace_open'),
    (re.compile(r'｝'), ')', 'fw_brace_close'),
    (re.compile(r'（'), '(', 'fw_paren_open'),
    (re.compile(r'）'), ')', 'fw_paren_close'),
    (re.compile(r'，'), ',', 'fw_comma'),
    (re.compile(r'；'), ';', 'fw_semicolon'),
    (re.compile(r'：'), ':', 'fw_colon'),
    (re.compile(r'！'), '!', 'fw_exclaim'),
    (re.compile(r'？'), '?', 'fw_question'),
    (re.compile(r'．'), '.', 'fw_period'),
    (re.compile(r'・'), '·', 'fw_middot'),

    # 7. 좌同/左同 → 좌동
    (re.compile(r'좌同|左同'), '좌동', 'jwa_dong'),

    # 8. Sample/warning markers with garbage circled-digit chars
    # 功 in "사례 功", "주의 功", "문제점 功", "해설 功", "취 지 功" → ①
    # 材 in "주의 材", "사례 材" → ②
    (re.compile(r'(사례|주의|문제점|해설|취\s*지|판례|예제|쟁점)(\s*)功'), r'\1\2①', 'marker_func_to_1'),
    (re.compile(r'(사례|주의|문제점|해설|취\s*지|판례|예제|쟁점)(\s*)材'), r'\1\2②', 'marker_zai_to_2'),

    # 9. Specific OCR scrambles seen in audit
    (re.compile(r'fcW뇌[!！]?'), '주의！', 'fcW_garbage'),
    (re.compile(r'tw풰'), '참고', 'tw_garbage'),
    (re.compile(r'기다카(?!\d)'), '다카', 'gida-ka_garbage'),

    # 10. WRE1 81 / WRE / similar OCR labels (unrecognizable abbreviations)
    (re.compile(r'(?m)^WRE\d*\s+\d*\s*'), '', 'wre_garbage'),

    # 11. Placeholder name 한자 → 한글 (legal case examples use 甲乙丙丁戊)
    (re.compile(r'(?<![가-힣A-Za-z])甲(?![가-힣A-Za-z])'), '갑', 'kanji_gap'),
    (re.compile(r'(?<![가-힣A-Za-z])乙(?![가-힣A-Za-z])'), '을', 'kanji_eul'),
    (re.compile(r'(?<![가-힣A-Za-z])丙(?![가-힣A-Za-z])'), '병', 'kanji_byeong'),
    (re.compile(r'(?<![가-힣A-Za-z])丁(?![가-힣A-Za-z])'), '정', 'kanji_jeong'),
    (re.compile(r'(?<![가-힣A-Za-z])戊(?![가-힣A-Za-z])'), '무', 'kanji_mu'),
    # OCR misreads of placeholder kanji
    (re.compile(r'江'), '을', 'ocr_river_to_eul'),    # 江 ← 乙 (OCR error)
    (re.compile(r'內'), '병', 'ocr_inside_to_byeong'),  # 內 ← 丙 (OCR error)
]


def clean_text(text: str, verbose: bool = False):
    """Apply all rules. Returns (cleaned, stats dict)."""
    stats = {}

    # Protect frontmatter
    fm = ''
    body = text
    if text.startswith('---\n'):
        end = text.find('\n---\n', 4)
        if end != -1:
            fm = text[:end + 5]
            body = text[end + 5:]

    for pattern, replacement, desc in RULES:
        before = body
        body = pattern.sub(replacement, body)
        if before != body:
            n = len(pattern.findall(before))
            stats[desc] = n
            if verbose:
                print(f'    [{desc}] {n} replacements')

    return fm + body, stats


def process_file(path: Path, dry_run: bool, verbose: bool):
    try:
        original = path.read_text(encoding='utf-8')
    except Exception as e:
        return None, f'READ_ERR: {e}'

    cleaned, stats = clean_text(original, verbose)

    if cleaned == original:
        return stats, 'unchanged'

    if dry_run:
        return stats, 'would_change'

    path.write_text(cleaned, encoding='utf-8')
    return stats, 'applied'


def show_diff(path: Path, max_lines: int = 30):
    """Show unified diff for a file."""
    original = path.read_text(encoding='utf-8')
    cleaned, _ = clean_text(original)
    diff = list(difflib.unified_diff(
        original.splitlines(),
        cleaned.splitlines(),
        fromfile=str(path),
        tofile=str(path) + ' (cleaned)',
        lineterm='',
        n=2,
    ))
    if not diff:
        return
    print(f'\n--- {path} ---')
    for line in diff[:max_lines]:
        print(line)
    if len(diff) > max_lines:
        print(f'... ({len(diff) - max_lines} more lines)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', required=True, help='File or directory')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--show-diffs', type=int, default=0, help='Show diff for first N changed files')
    ap.add_argument('--exclude-backup', action='store_true', default=True)
    args = ap.parse_args()

    target = Path(args.target)
    files = []
    if target.is_file():
        files = [target]
    elif target.is_dir():
        for p in target.rglob('*.md'):
            if args.exclude_backup and ('_backup' in str(p) or '_재추출' in str(p) or '_작업임시' in str(p)):
                continue
            files.append(p)

    print(f'[Phase 3.5] target={target} files={len(files)} dry_run={args.dry_run}')

    total_stats = {}
    changed = []
    unchanged = 0
    errors = []

    for f in files:
        result, status = process_file(f, args.dry_run, args.verbose)
        if status == 'unchanged':
            unchanged += 1
        elif status in ('applied', 'would_change'):
            changed.append((f, result))
            for k, v in result.items():
                total_stats[k] = total_stats.get(k, 0) + v
        else:
            errors.append((f, status))

    print()
    print('=== Summary ===')
    print(f'Files changed: {len(changed)}')
    print(f'Files unchanged: {unchanged}')
    print(f'Errors: {len(errors)}')
    print()
    print('=== Total replacements by rule ===')
    for k, v in sorted(total_stats.items(), key=lambda x: -x[1]):
        print(f'  {v:>6} {k}')

    if args.show_diffs and changed:
        print()
        print('=== Sample diffs ===')
        for f, _ in changed[:args.show_diffs]:
            show_diff(f)

    if errors:
        print()
        print('=== Errors ===')
        for f, e in errors[:10]:
            print(f'  {f}: {e}')


if __name__ == '__main__':
    main()
