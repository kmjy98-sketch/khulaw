"""
전경운 민법기초이론3 raw OCR(50p 단위) → sync/_교재원문/민법/전경운_민법3/ 정규화
- raw .md 본문 그대로 보존 (본문 0% 변경)
- frontmatter 정렬
- 사건번호 백링크
- placeholder 5개는 _trash/2026-04-30/ 로 이동 (삭제 금지)
"""
import os
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from code_pdf_extract_2026_04_30 import add_case_backlinks  # 동일 폴더 import

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

ROOT = Path(VAULT_ROOT)
RAW_DIR = ROOT / 'sync/_ocr_extracted/1민사__20전경운_민법3__교재__민법의_기초이론_3_전경운_교재'
TGT_DIR = ROOT / 'sync/_교재원문/민법/전경운_민법3'
TRASH = ROOT / '_trash/2026-04-30/전경운_placeholder_치환'

PLACEHOLDERS = [
    '민법의_기초이론_3_전경운_교재_p001-030.md',
    '민법의_기초이론_3_전경운_교재_p031-060.md',
    '민법의_기초이론_3_전경운_교재_p061-090.md',
    '민법의_기초이론_3_전경운_교재_p091-120.md',
    '민법의_기초이론_3_전경운_교재_p121-150.md',
]

NEW_FILES = [
    ('민법의_기초이론_3_전경운_교재_p001-050.md', '1민사__20전경운_민법3__교재__민법의_기초이론_3_전경운_교재_p0001-0050.md', '1-50'),
    ('민법의_기초이론_3_전경운_교재_p051-100.md', '1민사__20전경운_민법3__교재__민법의_기초이론_3_전경운_교재_p0051-0100.md', '51-100'),
    ('민법의_기초이론_3_전경운_교재_p101-150.md', '1민사__20전경운_민법3__교재__민법의_기초이론_3_전경운_교재_p0101-0150.md', '101-150'),
]


def parse_raw(raw_path: Path) -> tuple[str, dict]:
    text = raw_path.read_text(encoding='utf-8')
    # frontmatter 분리
    if not text.startswith('---'):
        return text, {}
    parts = text.split('---', 2)
    fm_text = parts[1]
    body = parts[2].lstrip('\n')
    fm = {}
    for ln in fm_text.strip().split('\n'):
        if ':' in ln:
            k, v = ln.split(':', 1)
            fm[k.strip()] = v.strip().strip('"')
    return body, fm


def make_normalized(body: str, pages: str, raw_meta: dict) -> str:
    fm = ['---']
    fm.append('tags: [교재원문, 민법, 전경운_민법3, 민법기초이론, 물권법]')
    fm.append('교재: 《민법의 기초이론 3》 (전경운)')
    fm.append('과목: 민법')
    fm.append(f'주제: 민법기초이론·물권법 (페이지 {pages})')
    fm.append(f'포함_페이지: {pages}')
    fm.append('저자: 전경운')
    fm.append('출처: 민법의_기초이론_3_전경운_교재.pdf')
    fm.append('추출엔진: marker-pdf (sync/_ocr_extracted/ raw)')
    fm.append(f'정규화일: {datetime.now().strftime("%Y-%m-%d")}')
    fm.append('---')

    title = f'# 민법의 기초이론 3 (전경운) — p.{pages}'
    intro = (f'\n## 0. 소스 범위\n\n'
             f'- **포함 페이지**: p.{pages}\n'
             f'- **추출**: marker-pdf (raw OCR), Code 환경 정규화\n'
             f'- **본문 변경**: 0% (raw OCR 보존, frontmatter만 정렬)\n'
             f'- **참조**: 동일 과목 《전경운 민법 물권총칙 26판》 파일군 (`전경운_민법_물총_26_*.md`)\n')

    body = add_case_backlinks(body)

    return '\n'.join(fm) + '\n\n' + title + '\n' + intro + '\n---\n\n' + body


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    TRASH.mkdir(parents=True, exist_ok=True)

    # 1) placeholder 5개 _trash로 이동
    for ph in PLACEHOLDERS:
        src = TGT_DIR / ph
        dst = TRASH / ph
        if src.exists():
            shutil.move(str(src), str(dst))
            print(f'  moved: {ph} → _trash/2026-04-30/전경운_placeholder_치환/')
        else:
            print(f'  skip (not found): {ph}')

    # 2) raw → 정규화 .md 생성
    for new_name, raw_name, pages in NEW_FILES:
        raw_path = RAW_DIR / raw_name
        if not raw_path.exists():
            print(f'  RAW MISSING: {raw_name}')
            continue
        body, raw_meta = parse_raw(raw_path)
        normalized = make_normalized(body, pages, raw_meta)
        dst = TGT_DIR / new_name
        dst.write_text(normalized, encoding='utf-8')
        print(f'  written: {new_name} ({len(normalized)} chars)')

    print('\n전경운 정규화 완료.')


if __name__ == '__main__':
    main()
