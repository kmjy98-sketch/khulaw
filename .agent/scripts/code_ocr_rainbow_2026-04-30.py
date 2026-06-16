"""
2026 레인보우 형법 OX 805p OCR 추출
- EasyOCR (ko+en)
- 50p 청크 단위로 점진 저장 (중단 시 재개 가능)
- 본문 0% 변경 (raw OCR 보존)
- 진행 상태: .agent/data/rainbow_ocr_progress.json
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

import fitz
import easyocr

ROOT = Path('H:/내 드라이브')
PDF_PATH = ROOT / '2.형사/96.기타/2026_레인보우_형법_OX_26.pdf'
OUT_DIR = ROOT / 'sync/_교재원문/형법/김기용_레인보우OX'
PROGRESS_FILE = ROOT / '.agent/data/rainbow_ocr_progress.json'
RAW_DIR = ROOT / 'sync/_ocr_extracted/2형사__96기타__2026_레인보우_형법_OX_26'

CHUNK_SIZE = 50
SCALE = 2.0


def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding='utf-8'))
    return {'completed_chunks': [], 'started_at': datetime.now().isoformat()}


def save_progress(progress):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding='utf-8')


def make_frontmatter(start, end, total_pages):
    return f'''---
tags: [교재원문, 형법, 김기용_레인보우OX, OX, 형법총론, 보조자료]
교재: 《2026 레인보우 형법 OX》 (보조자료)
과목: 형법
주제: 형법총론·각론 OX 보조 (페이지 {start}-{end})
포함_페이지: {start}-{end}
저자: 레인보우 (보조자료, 김기용 compact OX와 별개)
출처: 2026_레인보우_형법_OX_26.pdf
추출엔진: EasyOCR (ko+en, CPU, scale={SCALE})
추출일: {datetime.now().strftime("%Y-%m-%d")}
---'''


def extract_chunk(reader, doc, start, end, mat):
    """페이지 [start, end] (1-indexed inclusive)."""
    parts = []
    times = []
    for p in range(start, end + 1):
        if p > doc.page_count:
            break
        page = doc[p - 1]
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes('png')
        t0 = time.time()
        result = reader.readtext(img_bytes, detail=0, paragraph=True)
        t1 = time.time()
        times.append(t1 - t0)
        text = '\n'.join(result) if result else ''
        if text.strip():
            parts.append(f'<!-- p.{p} -->\n\n{text}')
    body = '\n\n'.join(parts)
    avg_time = sum(times)/len(times) if times else 0
    return body, avg_time


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f'Loading EasyOCR...')
    reader = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
    print(f'EasyOCR ready.')

    doc = fitz.open(PDF_PATH)
    total = doc.page_count
    print(f'PDF: {PDF_PATH.name}, {total} pages')

    progress = load_progress()
    completed = set(progress['completed_chunks'])

    mat = fitz.Matrix(SCALE, SCALE)
    chunks = []
    for start in range(1, total + 1, CHUNK_SIZE):
        end = min(start + CHUNK_SIZE - 1, total)
        chunks.append((start, end))

    overall_start = time.time()
    for i, (start, end) in enumerate(chunks):
        chunk_id = f'p{start:04d}-{end:04d}'
        if chunk_id in completed:
            print(f'  [{i+1}/{len(chunks)}] {chunk_id} already done, skip')
            continue

        print(f'  [{i+1}/{len(chunks)}] {chunk_id} start...', flush=True)
        t0 = time.time()
        body, avg = extract_chunk(reader, doc, start, end, mat)
        t1 = time.time()
        chunk_time = t1 - t0

        # raw 저장
        raw_path = RAW_DIR / f'2026_레인보우_형법_OX_26_{chunk_id}.md'
        raw_path.write_text(body, encoding='utf-8')

        # 정규화본 저장
        fm = make_frontmatter(start, end, total)
        title = f'# 2026 레인보우 형법 OX — p.{start}-{end}'
        intro = f'\n## 0. 소스 범위\n\n- **포함 페이지**: p.{start}-{end}\n- **추출**: EasyOCR (ko+en, CPU, scale {SCALE}x)\n- **본문 변경**: 0% (raw OCR 보존)\n'
        full = f'{fm}\n\n{title}\n{intro}\n---\n\n{body}\n'

        out_path = OUT_DIR / f'김기용_레인보우OX_26_{chunk_id}.md'
        out_path.write_text(full, encoding='utf-8')

        completed.add(chunk_id)
        progress['completed_chunks'] = sorted(completed)
        progress['last_completed'] = chunk_id
        progress['last_completed_at'] = datetime.now().isoformat()
        save_progress(progress)

        elapsed_total = time.time() - overall_start
        remaining = len(chunks) - (i + 1)
        eta = remaining * chunk_time / 60 if chunk_time > 0 else 0
        print(f'  [{i+1}/{len(chunks)}] {chunk_id} done in {chunk_time:.0f}s (avg {avg:.1f}s/p, body {len(body)}c) | elapsed {elapsed_total/60:.1f}min, ETA {eta:.0f}min')

    print(f'\nALL DONE. {len(chunks)} chunks total.')


if __name__ == '__main__':
    main()
