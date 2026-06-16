"""Audit Phase 3 LLM reflow output for problematic files.

Heuristics:
- Compare current vs _backup_phase1 size ratio
- Detect raw OCR garbage characters that should have been cleaned
- Detect missing markdown structure (no callouts, no h3 headings)
"""
import sys, os, re

sys.stdout.reconfigure(encoding='utf-8')

ROOT = 'sync/_교재원문'

# OCR garbage markers - presence in reflowed output indicates Phase 3 incomplete
GARBAGE_CHARS = ['材', '功', 'fcW', '左同', '＝', '＞', '｛', '｝', '乂', '水']

# Patterns that suggest raw/incomplete OCR
BAD_PATTERNS = [
    re.compile(r'\d{2,4}다\[\^?\d+'),     # broken precedent: "65다[^877"
    re.compile(r'기\s+(이|을|에게|는|과)'), # "기" mistakes (should be 갑/을)
    re.compile(r'tw풰|fcW뇌|기다카|다®'),    # specific OCR scrambles
    re.compile(r'[가-힣][\.\s]+[가-힣]\s*[•·]\s*[가-힣]'),  # broken bullet sep
]

results = []

for root, dirs, files in os.walk(ROOT):
    if not root.endswith('_backup_phase1'):
        continue
    for f in files:
        if not f.endswith('.md'):
            continue
        backup_path = os.path.join(root, f)
        parent = os.path.dirname(root)
        current_path = os.path.join(parent, f)
        if not os.path.exists(current_path):
            continue
        bsize = os.path.getsize(backup_path)
        csize = os.path.getsize(current_path)

        with open(current_path, encoding='utf-8') as fh:
            cur = fh.read()

        ratio = csize / bsize if bsize > 0 else 0
        garbage = sum(cur.count(c) for c in GARBAGE_CHARS)
        bad_score = sum(len(p.findall(cur)) for p in BAD_PATTERNS)
        has_callout = '> [!' in cur
        has_h3 = re.search(r'^### ', cur, re.MULTILINE) is not None

        rel = os.path.relpath(current_path, ROOT).replace(os.sep, '/')

        results.append({
            'path': rel,
            'csize': csize,
            'bsize': bsize,
            'ratio': ratio,
            'bad_score': bad_score,
            'garbage': garbage,
            'total_bad': bad_score + garbage,
            'has_callout': has_callout,
            'has_h3': has_h3,
        })

results.sort(key=lambda x: -x['total_bad'])

print(f'Total backup pairs: {len(results)}')
print()

# Critical: high garbage and missing structure
critical = [r for r in results if r['garbage'] >= 5 or r['bad_score'] >= 5 or not r['has_callout']]
print(f'Critical (garbage>=5 OR bad>=5 OR no callouts): {len(critical)}')
print()
print(f'{"BAD":<5}{"GAR":<5}{"RATIO":<7}{"CAL":<4}{"H3":<4} PATH')
print('-' * 100)
for r in critical[:80]:
    cal = 'Y' if r['has_callout'] else 'N'
    h3 = 'Y' if r['has_h3'] else 'N'
    print(f'{r["bad_score"]:<5}{r["garbage"]:<5}{r["ratio"]:<7.2f}{cal:<4}{h3:<4} {r["path"]}')

print()
print('=== Stats ===')
print(f'No callouts: {sum(1 for r in results if not r["has_callout"])}')
print(f'No H3 headings: {sum(1 for r in results if not r["has_h3"])}')
print(f'High garbage (>5): {sum(1 for r in results if r["garbage"] > 5)}')
print(f'Bad pattern (>5): {sum(1 for r in results if r["bad_score"] > 5)}')
print(f'Ratio < 0.95 (likely truncated): {sum(1 for r in results if r["ratio"] < 0.95)}')
