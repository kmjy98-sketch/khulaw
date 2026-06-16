#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, re, json
sys.stdout.reconfigure(encoding='utf-8')

with open('.agent/state/batch2_g1.json', encoding='utf-8') as f:
    records = json.load(f)

base_out = '.agent/data/ocr_chunks_reviewed/'
error_patterns = {'判例': 0, '邙': 0, '저し': 0, '何판': 0, '仰판': 0}
file_count = 0

for r in records:
    cp = r['chunk_path']
    norm = cp.replace('\\', '/')
    marker = 'ocr_chunks/'
    idx = norm.find(marker)
    rel = norm[idx + len(marker):]
    dst = os.path.join(base_out, *rel.split('/'))
    if os.path.exists(dst):
        with open(dst, encoding='utf-8') as f:
            text = f.read()
        for pat in error_patterns:
            error_patterns[pat] += text.count(pat)
        file_count += 1

print(f'확인한 파일 수: {file_count}')
print('batch2_g1 교정 파일 남은 오류:')
for pat, count in error_patterns.items():
    print(f'  {pat}: {count}개')
