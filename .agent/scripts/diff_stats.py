#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

with open('.agent/state/batch2_g1.json', encoding='utf-8') as f:
    records = json.load(f)

base_in = '.agent/data/ocr_chunks/'
base_out = '.agent/data/ocr_chunks_reviewed/'

total_changed_lines = 0
modified_files = 0
copied_files = 0

for r in records:
    cp = r['chunk_path']
    norm = cp.replace('\\', '/')
    marker = 'ocr_chunks/'
    idx = norm.find(marker)
    rel = norm[idx + len(marker):]

    src = os.path.join(base_in, *rel.split('/'))
    dst = os.path.join(base_out, *rel.split('/'))

    if not os.path.exists(src) or not os.path.exists(dst):
        continue

    with open(src, encoding='utf-8') as f:
        orig = f.readlines()
    with open(dst, encoding='utf-8') as f:
        rev = f.readlines()

    diff = sum(1 for o, r2 in zip(orig, rev) if o != r2)
    total_changed_lines += diff
    if diff > 0:
        modified_files += 1
    else:
        copied_files += 1

print(f'수정된 파일: {modified_files}개')
print(f'변경 없는 파일: {copied_files}개')
print(f'총 교정된 줄: {total_changed_lines}줄')
