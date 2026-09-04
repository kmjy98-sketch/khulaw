import os, json, re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

manifest = vp(".agent", "state", "batch2_g2.json")
out_base = vp(".agent", "data", "ocr_chunks_reviewed")

with open(manifest, 'r', encoding='utf-8') as f:
    records = json.load(f)

sample_indices = [0, 5, 20, 50, 100, 131]

for i in sample_indices:
    rec = records[i]
    cp = rec['chunk_path']
    cp_fwd = cp.replace('\\', '/')
    rel = cp_fwd.replace('.agent/data/ocr_chunks/', '')
    out_path = out_base + '/' + rel
    if os.path.exists(out_path):
        with open(out_path, 'r', encoding='utf-8') as f:
            content = f.read()
        issues = []
        if re.search(r'[\uB2E4][\uC785\.\,\s]', content) and '댜' in content:
            issues.append('댜 잔존')
        if re.search(r'\u5244f\w+[Jj]', content):
            issues.append('判例 오인식 잔존')
        if '\uCC9C\uAD8C\uC790' in content:
            issues.append('천권자 잔존')
        if '\uB300\uB9AC\uC548\uC774' in content or '\uB300\uB9AC\uC548\uC758' in content:
            issues.append('대리안 잔존')
        fname = os.path.basename(out_path)
        status = 'OK' if not issues else ', '.join(issues)
        print(f'[{i:3d}] {fname}: {status}')
    else:
        print(f'[{i:3d}] MISSING: {out_path}')

print('\n=== 전체 잔존 패턴 통계 ===')
counts = {'처리완료': 0, '천권자잔존': 0, '대리안잔존': 0, '의마잔존': 0}
for rec in records:
    cp = rec['chunk_path'].replace('\\', '/')
    rel = cp.replace('.agent/data/ocr_chunks/', '')
    out_path = out_base + '/' + rel
    if os.path.exists(out_path):
        counts['처리완료'] += 1
        with open(out_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if '천권자' in content:
            counts['천권자잔존'] += 1
        if '대리안이' in content or '대리안의' in content:
            counts['대리안잔존'] += 1
        if '의마를' in content or '의마가' in content:
            counts['의마잔존'] += 1

for k, v in counts.items():
    print(f'  {k}: {v}')
