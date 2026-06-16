"""Detect mid-reflow cutoff in Phase 3 output.

A "cutoff" file shows clean LLM-polished structure in the first half but
raw Phase 2 OCR in the second half. We score each line for "polish" markers
and look for a sharp transition.
"""
import sys, os, re, json
sys.stdout.reconfigure(encoding='utf-8')

ROOT = 'sync/_교재원문'

# Markers per line
POLISH_RE = re.compile(r'(\*\*[^*]+\*\*|> \[!|^#### [가나다라마]\.|\[\^\d+\])')
GARBAGE_RE = re.compile(r'(材|功|fcW|tw풰|기다카|\d{2,4}다\[\^|좌同|左同|＝|＞)')
PRECEDENT_BROKEN_RE = re.compile(r'\d{2,4}다\[\^?\d+|\d{2,4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*[Cc]?\d{2,4}|94[Ll-]+|HHHH')
RAW_OCR_RE = re.compile(r'[가-힣]\s*[•·]\s*[가-힣]\s*[•·]|[가-힣]{1,3}\s+[기을갑]\s+[가-힣]{1,3}\s+[기을갑]')

def score_segment(lines):
    polish = sum(1 for l in lines if POLISH_RE.search(l))
    garbage = sum(1 for l in lines if GARBAGE_RE.search(l))
    return polish, garbage

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

        with open(current_path, encoding='utf-8') as fh:
            cur = fh.read()

        lines = cur.split('\n')
        if len(lines) < 50:
            continue

        # Sliding window: 50-line chunks, compute polish/garbage ratio
        WINDOW = 50
        scores = []
        for i in range(0, len(lines) - WINDOW, WINDOW):
            seg = lines[i:i+WINDOW]
            p, g = score_segment(seg)
            scores.append({'start': i+1, 'polish': p, 'garbage': g})

        if not scores:
            continue

        # Find first segment after a "polished" segment that becomes "raw"
        cutoff = None
        max_polish = max(s['polish'] for s in scores)
        for i in range(1, len(scores)):
            prev = scores[i-1]
            cur_s = scores[i]
            # Sharp drop in polish + spike in garbage
            if prev['polish'] >= 5 and cur_s['polish'] <= 1 and cur_s['garbage'] >= 3:
                cutoff = cur_s['start']
                break
            # Or: polish drops to 0 and stays for rest
            if prev['polish'] >= 5 and cur_s['polish'] == 0:
                # Confirm subsequent segments stay polish==0
                rest = scores[i:]
                if all(s['polish'] <= 1 for s in rest) and any(s['garbage'] >= 2 for s in rest):
                    cutoff = cur_s['start']
                    break

        # Total counts
        total_polish = sum(s['polish'] for s in scores)
        total_garbage = sum(s['garbage'] for s in scores)
        rel = os.path.relpath(current_path, ROOT).replace(os.sep, '/')

        results.append({
            'path': rel,
            'lines': len(lines),
            'cutoff_line': cutoff,
            'total_polish': total_polish,
            'total_garbage': total_garbage,
        })

# Files with clear cutoff
cutoff_files = [r for r in results if r['cutoff_line']]
cutoff_files.sort(key=lambda x: -x['total_garbage'])

print(f'Total scanned: {len(results)}')
print(f'Files with detected cutoff: {len(cutoff_files)}')
print()
print(f'{"CUTOFF":<8}{"LINES":<7}{"POL":<6}{"GAR":<6} PATH')
print('-' * 100)
for r in cutoff_files[:60]:
    print(f'{r["cutoff_line"]:<8}{r["lines"]:<7}{r["total_polish"]:<6}{r["total_garbage"]:<6} {r["path"]}')

# Save full result
out = '.agent/state/reflow_cutoff_audit.json'
with open(out, 'w', encoding='utf-8') as fh:
    json.dump({
        'total': len(results),
        'cutoff_count': len(cutoff_files),
        'files': cutoff_files,
    }, fh, ensure_ascii=False, indent=2)
print(f'\nSaved: {out}')
