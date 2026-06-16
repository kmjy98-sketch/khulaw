# -*- coding: utf-8 -*-
import os, json, sys

base = 'H:/내 드라이브'
with open(base + '/.agent/state/batch3_g4.json', encoding='utf-8') as f:
    chunks = json.load(f)

already = []
todo = []
for c in chunks:
    cp = c['chunk_path']
    cp_fwd = cp.replace('\\', '/')
    prefix = '.agent/data/ocr_chunks/'
    if cp_fwd.startswith(prefix):
        suffix = cp_fwd[len(prefix):]
    else:
        suffix = cp_fwd
    reviewed_path = base + '/.agent/data/ocr_chunks_reviewed/' + suffix
    if os.path.exists(reviewed_path):
        already.append(suffix)
    else:
        todo.append((cp, suffix))

print(f'Already done: {len(already)}', flush=True)
print(f'Todo: {len(todo)}', flush=True)
for t in todo[:15]:
    print(' TODO:', t[1], flush=True)
