#!/usr/bin/env python3
"""홍형철 고유 PDF 4개만 선별 ingest (중복 복사본 제외)."""
import sys
from pathlib import Path

ROOT = Path('H:/내 드라이브')
sys.path.insert(0, str(ROOT / '.agent/skills/pdf-ingest/scripts'))
sys.path.insert(0, str(ROOT / '.agent/lib'))

from ingest import batch_extract, ensure_pypdf
from pypdf import PdfReader

SRC = ROOT / '2.형사/30.홍형철_기본형법'
OUT = ROOT / 'sync/_교재원문/형법/홍형철_기본형법'

# 고유 파일만 (크기별로 중복 식별 후 선별)
TARGETS = [
    SRC / '기타/홍형철_쟁점정리_형법_25.pdf',                      # 124MB 메인
    SRC / '정리/기본형법_총론_15회_2.7_보충자료1.pdf',             # 33KB
    SRC / '정리/기본형법_총론_15회_2.7_보충자료2.pdf',             # 61KB
    SRC / '정리/기본형법_각론_12회_판례추가.pdf',                   # 106KB
]

OUT.mkdir(parents=True, exist_ok=True)

# ingest.py의 batch_extract를 재사용하되 단일 파일 글롭은 어려워 직접 수동 실행
import json, re
from datetime import datetime


def extract_pages(reader, start, end):
    parts = []
    for i in range(start - 1, min(end, len(reader.pages))):
        t = reader.pages[i].extract_text()
        if t:
            parts.append(f'--- Page {i+1} ---\n{t}')
    return '\n\n'.join(parts)


def extract_legal_keywords(text):
    kw = set()
    kw.update(re.findall(r'제\d+조(?:의\d+)?', text))
    kw.update(re.findall(r'\d{2,4}다\d+', text))
    kw.update(re.findall(r'\d{2,4}도\d+', text))
    return list(kw)[:20]


CHUNK = 30
index_path = OUT / 'chunks_index.json'
if index_path.exists():
    index = json.loads(index_path.read_text(encoding='utf-8'))
else:
    index = {'created': datetime.now().isoformat(), 'chunk_size': CHUNK, 'sources': [], 'chunks': []}
processed = {s['file'] for s in index['sources']}

for pdf in TARGETS:
    if not pdf.exists():
        print(f'[SKIP 없음] {pdf}')
        continue
    if pdf.name in processed:
        print(f'[건너뜀] {pdf.name}')
        continue
    print(f'\n[추출] {pdf.name} ({pdf.stat().st_size/1024:.1f}KB)')
    reader = PdfReader(str(pdf))
    total = len(reader.pages)
    print(f'  페이지: {total}')
    # 홍형철 접두사 부여 (파일명 식별용)
    base = pdf.stem.replace('기본형법_', '홍형철_기본형법_') if 'pdf' not in pdf.stem else pdf.stem
    if not base.startswith('홍형철'):
        base = '홍형철_' + base
    src_info = {'file': pdf.name, 'pages': total, 'chunks': [], 'source_title': base}
    for start in range(0, total, CHUNK):
        end = min(start + CHUNK, total)
        text = extract_pages(reader, start + 1, end)
        chunk_name = f'{base}_p{start+1:03d}-{end:03d}.md'
        (OUT / chunk_name).write_text(text, encoding='utf-8')
        index['chunks'].append({
            'id': f'{pdf.stem}_p{start+1}-{end}',
            'source': pdf.name,
            'source_title': base,
            'pages': f'{start+1}-{end}',
            'file': chunk_name,
            'size': len(text),
            'keywords': extract_legal_keywords(text),
        })
        src_info['chunks'].append(chunk_name)
        print(f'  → {chunk_name} ({len(text):,}자)')
    index['sources'].append(src_info)

index['last_updated'] = datetime.now().isoformat()
index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n완료. 출력: {OUT}')
print(f'chunks: {len(index["chunks"])}')
