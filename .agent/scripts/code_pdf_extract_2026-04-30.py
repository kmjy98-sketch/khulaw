"""
PDF OCR 추출 (Code 환경, 2026-04-30)
- PyMuPDF (fitz) 기반 텍스트 추출
- 텍스트 레이어 있는 PDF만 처리 (없으면 skip + 보고)
- 30p 단위 청크 분할
- yaml frontmatter 자동 부여
- 사건번호/조문 백링크 (CLAUDE.md #34·#35 준수)
- 본문 0% 변경, 의역 X
"""
import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF


# 사건번호 패턴 (대법원·헌재 통합)
# 대판: YY다XXXXX, YY도XXXXX, YY누XXXXX, YY후XXXXX, YY므XXXXX, YY가합XXXXX 등
# 헌재: YYYY헌마XXXX, YYYY헌바XXXX, YYYY헌가XXXX, YYYY헌나XXXX, YYYY헌라XXXX, YYYY헌마XXXX
CASE_PATTERNS = [
    # 헌재 (4자리 연도)
    re.compile(r'(?<![0-9가-힣])(\d{4}헌(?:마|바|가|나|라|아|타|인)\d+(?:[·,\s]\d+)*)'),
    # 대법원 (2자리 연도)
    re.compile(r'(?<![0-9가-힣])(\d{2,4}(?:다|도|누|후|므|허|두|마|바|초|아|재)(?:합|부|영|상)?\d+(?:[·,\s]\d+)*)'),
]


def add_case_backlinks(text: str) -> str:
    """사건번호를 [[..]] 백링크로 변환. 표/코드/판례블록 안에서는 적용 X (간단판: 라인별 검사)."""
    out_lines = []
    in_code = False
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code = not in_code
            out_lines.append(line)
            continue
        if in_code:
            out_lines.append(line)
            continue
        # 표 행이면 스킵 (|로 시작하거나 |가 다수)
        if stripped.startswith('|') and stripped.count('|') >= 2:
            out_lines.append(line)
            continue
        # 이미 [[..]] 로 감싸진 부분은 보존
        # 가장 긴 매치부터 처리하기 위해 모든 매치를 모은 뒤 정렬
        new_line = line
        # 헌재 먼저(긴 패턴)
        for pat in CASE_PATTERNS:
            def repl(m):
                tok = m.group(1)
                # 이미 백링크에 포함됐는지 확인
                start = m.start()
                # 좌측 [[ 검사
                left = new_line[max(0, start-2):start]
                if left == '[[':
                    return tok
                return f'[[{tok}]]'
            new_line = pat.sub(repl, new_line)
        out_lines.append(new_line)
    return '\n'.join(out_lines)


def clean_page_text(text: str) -> str:
    """OCR 노이즈 정리 — 본문 0% 변경 원칙 (페이지 헤더/번호만 제거)."""
    # 페이지 단독 숫자 라인 제거 (선택적, 보수적)
    lines = text.split('\n')
    cleaned = []
    for ln in lines:
        s = ln.strip()
        # 페이지 단독 숫자 (1~3자리)
        if re.fullmatch(r'-?\s*\d{1,3}\s*-?', s):
            continue
        cleaned.append(ln)
    out = '\n'.join(cleaned)
    # 연속 빈 줄 3개 이상 → 2개
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out.strip()


def extract_chunk(doc: fitz.Document, start_page: int, end_page: int) -> tuple[str, int]:
    """0-indexed [start_page, end_page) 범위 텍스트 추출. (text, char_count) 반환."""
    parts = []
    for i in range(start_page, min(end_page, doc.page_count)):
        page = doc[i]
        text = page.get_text()
        text = clean_page_text(text)
        if text.strip():
            parts.append(f'<!-- p.{i+1} -->\n\n{text}')
    body = '\n\n'.join(parts)
    return body, len(body)


def make_frontmatter(meta: dict) -> str:
    tags = meta.get('tags', [])
    fm = ['---']
    fm.append(f"tags: [{', '.join(tags)}]")
    for k, v in meta.items():
        if k == 'tags':
            continue
        fm.append(f"{k}: {v}")
    fm.append('---')
    return '\n'.join(fm)


def _detect_scanned(doc: "fitz.Document", sample: int = 5) -> tuple:
    """스캔 이미지 PDF 감지: (풀페이지 대형 이미지 페이지 수, O/0 글머리 비율).
    텍스트 레이어가 있어도 스캔본의 저품질 OCR 레이어면 ①②③ 등이 O/0으로 깨져 있음.
    PyMuPDF get_text()는 이 손상된 레이어를 그대로 가져오므로 카드화 부적합 → 차단."""
    big_img_pages = 0
    o0_lines = 0
    total_lines = 0
    for i in range(min(sample, doc.page_count)):
        page = doc[i]
        for img in page.get_images(full=True):
            w, h = img[2], img[3]
            if w >= 1000 and h >= 1400:  # 고해상도 풀페이지 스캔
                big_img_pages += 1
                break
        for ln in page.get_text().splitlines():
            s = ln.strip()
            if not s:
                continue
            total_lines += 1
            if s[:1] in "O0":
                o0_lines += 1
    o0_ratio = (o0_lines / total_lines) if total_lines else 0.0
    return big_img_pages, o0_ratio


def chunk_pdf(pdf_path: str, out_dir: str, *, prefix: str, subject: str,
              author: str, book: str, chunk_size: int = 30,
              extra_tags: list = None, topic: str = '',
              start_page: int = 1, max_pages: int = None) -> dict:
    """
    PDF를 chunk_size 페이지 단위로 분할 추출.
    출력: {out_dir}/{prefix}_p{NNN}-{NNN}.md
    """
    extra_tags = extra_tags or []
    os.makedirs(out_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    total = doc.page_count

    # 텍스트 레이어 검사 (앞 5p 샘플)
    sample_chars = 0
    for i in range(min(5, total)):
        sample_chars += len(doc[i].get_text().strip())
    if sample_chars < 50:
        return {
            'pdf': pdf_path,
            'pages': total,
            'status': 'NO_TEXT_LAYER',
            'sample_chars': sample_chars,
            'chunks': 0,
        }

    # [가드 2026-06-01] 스캔 이미지 PDF의 저품질 OCR 텍스트레이어 덤프 차단.
    # PyMuPDF는 이미지를 못 읽고 박혀있는 OCR 레이어만 추출 → ①②③→O/0 손상.
    big_img_pages, o0_ratio = _detect_scanned(doc)
    if big_img_pages >= 3 or o0_ratio > 0.15:
        doc.close()
        return {
            'pdf': pdf_path,
            'pages': total,
            'status': 'SCANNED_NEEDS_IMAGE_OCR',
            'big_img_pages': big_img_pages,
            'o0_ratio': round(o0_ratio, 2),
            'note': '스캔 이미지 PDF — 텍스트레이어 손상(①②③→O/0). marker-pdf(Colab) 또는 Gemini Mode B 이미지 OCR 사용 (CLAUDE.md #13).',
            'chunks': 0,
        }

    end = total if max_pages is None else min(start_page + max_pages, total + 1)

    chunks_written = []
    page = start_page
    while page <= end - 1:  # page is 1-indexed inclusive
        chunk_end = min(page + chunk_size - 1, end - 1, total)
        # 0-indexed for fitz
        body, n = extract_chunk(doc, page - 1, chunk_end)
        if n < 30:
            page = chunk_end + 1
            continue

        body = add_case_backlinks(body)

        chunk_label = f'p{page:03d}-{chunk_end:03d}'
        out_path = os.path.join(out_dir, f'{prefix}_{chunk_label}.md')

        meta = {
            'tags': ['교재원문', subject, f'{author}_{book}'] + extra_tags,
            '교재': f'《{book}》 ({author})',
            '과목': subject,
            '주제': topic or f'페이지 {page}-{chunk_end}',
            '포함_페이지': f'{page}-{chunk_end}',
            '저자': author,
            '출처': os.path.basename(pdf_path),
            '추출일': datetime.now().strftime('%Y-%m-%d'),
            '추출엔진': 'PyMuPDF-1.26.7',
        }
        fm = make_frontmatter(meta)
        title = f'# {book} ({author}) — p.{page}-{chunk_end}'

        full = f'{fm}\n\n{title}\n\n## 0. 소스 범위\n\n- **포함 페이지**: p.{page}-{chunk_end}\n- **추출**: PyMuPDF native text layer extraction\n- **본문 변경**: 0% (raw text 보존)\n\n---\n\n{body}\n'

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(full)
        chunks_written.append({'file': out_path, 'pages': f'{page}-{chunk_end}', 'chars': n})

        page = chunk_end + 1

    doc.close()
    return {
        'pdf': pdf_path,
        'pages': total,
        'status': 'OK',
        'sample_chars': sample_chars,
        'chunks': len(chunks_written),
        'chunks_written': chunks_written,
    }


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--author', required=True)
    parser.add_argument('--book', required=True)
    parser.add_argument('--chunk-size', type=int, default=30)
    parser.add_argument('--topic', default='')
    parser.add_argument('--extra-tags', default='', help='comma-separated')
    args = parser.parse_args()

    extra_tags = [t.strip() for t in args.extra_tags.split(',') if t.strip()]
    result = chunk_pdf(
        args.pdf, args.out,
        prefix=args.prefix,
        subject=args.subject,
        author=args.author,
        book=args.book,
        chunk_size=args.chunk_size,
        extra_tags=extra_tags,
        topic=args.topic,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
