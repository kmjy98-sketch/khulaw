#!/usr/bin/env python3
"""2.형사/94.교재 핵심 교재 선별 ingest.

범위:
- 새로쓴형법총론_ocr_x.pdf (32MB)
- 반반형법_25.pdf (216MB, _24 제외)
- 작은변사기형법_25.pdf (260MB)
- 이인규 분할본 3종 (총 789MB, 통합본 중복 회피)
"""
import sys
import re
import json
from pathlib import Path
from datetime import datetime

ROOT = Path('H:/내 드라이브')
sys.path.insert(0, str(ROOT / '.agent/skills/pdf-ingest/scripts'))
sys.path.insert(0, str(ROOT / '.agent/lib'))

from pypdf import PdfReader

SRC = ROOT / '2.형사/94.교재'
OUT_BASE = ROOT / 'sync/_교재원문/형법'

# (pdf 파일명, 출력 폴더명, 접두사)
TARGETS = [
    ('새로쓴형법총론_ocr_x.pdf', '새로쓴_형법총론', '새로쓴_형법총론'),
    ('반반형법_25.pdf', '반반형법', '반반형법'),
    ('작은변사기형법_25.pdf', '작은변사기_형법', '작은변사기_형법'),
    ('이인규_진도별변시사시기출형법사례연습_총론_25.pdf', '이인규_사례연습', '이인규_사례연습_총론'),
    ('이인규_진도별변시사시기출형법사례연습_개인적법익_25.pdf', '이인규_사례연습', '이인규_사례연습_개인적법익'),
    ('이인규_진도별변시사시기출형법사례연습_사회적법익_국가기능_특별형법_25.pdf', '이인규_사례연습', '이인규_사례연습_사회적_국가_특별'),
]

CHUNK = 30


def extract_pages(reader, start, end):
    parts = []
    for i in range(start - 1, min(end, len(reader.pages))):
        try:
            t = reader.pages[i].extract_text()
        except Exception as e:
            t = f'[추출실패: {e}]'
        if t:
            parts.append(f'--- Page {i+1} ---\n{t}')
    return '\n\n'.join(parts)


def extract_legal_keywords(text):
    kw = set()
    kw.update(re.findall(r'제\d+조(?:의\d+)?', text))
    kw.update(re.findall(r'\d{2,4}다\d+', text))
    kw.update(re.findall(r'\d{2,4}도\d+', text))
    return list(kw)[:20]


def process_pdf(pdf_path, out_dir, base_prefix):
    if not pdf_path.exists():
        print(f'[SKIP 없음] {pdf_path}')
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / 'chunks_index.json'
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding='utf-8'))
    else:
        index = {'created': datetime.now().isoformat(), 'chunk_size': CHUNK, 'sources': [], 'chunks': []}
    processed = {s['file'] for s in index['sources']}
    if pdf_path.name in processed:
        print(f'[건너뜀] {pdf_path.name}')
        return 0

    size_mb = pdf_path.stat().st_size / 1024 / 1024
    print(f'\n[추출] {pdf_path.name} ({size_mb:.1f}MB)')
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    print(f'  페이지: {total}')

    src_info = {'file': pdf_path.name, 'pages': total, 'chunks': [], 'source_title': base_prefix}
    chunk_count = 0
    for start in range(0, total, CHUNK):
        end = min(start + CHUNK, total)
        text = extract_pages(reader, start + 1, end)
        chunk_name = f'{base_prefix}_p{start+1:04d}-{end:04d}.md'
        (out_dir / chunk_name).write_text(text, encoding='utf-8')
        index['chunks'].append({
            'id': f'{base_prefix}_p{start+1}-{end}',
            'source': pdf_path.name,
            'source_title': base_prefix,
            'pages': f'{start+1}-{end}',
            'file': chunk_name,
            'size': len(text),
            'keywords': extract_legal_keywords(text),
        })
        src_info['chunks'].append(chunk_name)
        chunk_count += 1
        if chunk_count % 10 == 0:
            print(f'  ... {chunk_count}개 청크 ({end}/{total}p)')
    index['sources'].append(src_info)
    index['last_updated'] = datetime.now().isoformat()
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  완료: {chunk_count}청크 → {out_dir.name}/')
    return chunk_count


def main():
    total_chunks = 0
    for fname, dirname, prefix in TARGETS:
        pdf = SRC / fname
        out = OUT_BASE / dirname
        total_chunks += process_pdf(pdf, out, prefix)
    print(f'\n전체 청크 수: {total_chunks}')


if __name__ == '__main__':
    main()
