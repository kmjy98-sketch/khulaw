#!/usr/bin/env python3
"""교재원문 마크다운 파일의 결정론적 가독성 정리 (단계 A).

처리 내용 (lossless):
- 본문의 `--- Page N ---` 마커 수집 → frontmatter `포함_페이지: [N1, N2, ...]` 필드로 이동
- 본문에서 페이지 마커 줄 삭제
- 단독 줄 인라인 페이지 번호 (`- N -` 혼자 있는 줄) 삭제
- 연속 공백 정리 (`  +` → ` `, 코드 블록 제외)
- 연속 빈 줄 정리 (3개 이상 → 2개)
- 전각 괄호 `（）`·`［］` → 반각 `()`·`[]` (본문만)
- 데코 노이즈 단독 줄 제거 (`• r`, `■QB` 같은 패턴)

백업: 5.기타/_trash/2026-04-11/_교재원문_pre_cleanA/ 하위로 원본 복사 (--backup 플래그)
idempotent: 재실행 시 이미 처리된 파일은 frontmatter에 `포함_페이지` 존재 → 본문 스캔만
"""
import sys
import re
import shutil
import argparse
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브')
TEXTBOOK_ROOT = ROOT / 'sync' / '_교재원문'
BACKUP_ROOT = ROOT / '5.기타' / '_trash' / '2026-04-11' / '_교재원문_pre_cleanA'

FRONTMATTER_PAT = re.compile(r'^(---\n.*?\n---\n)(.*)$', re.DOTALL)
PAGE_MARKER_PAT = re.compile(r'^--- Page (\d+) ---$', re.MULTILINE)
INLINE_PAGE_PAT = re.compile(r'^\s*[-─]\s*(\d+)\s*[-─]\s*$', re.MULTILINE)
PAGE_RANGE_IN_FM_PAT = re.compile(r'(?:pp?\.)?\s*(\d+)\s*[-~–—]\s*(\d+)')
MULTI_SPACE_PAT = re.compile(r'  +')
MULTI_BLANK_PAT = re.compile(r'\n{3,}')
FULLWIDTH_PAREN_OPEN = '（'
FULLWIDTH_PAREN_CLOSE = '）'
FULLWIDTH_BRACKET_OPEN = '［'
FULLWIDTH_BRACKET_CLOSE = '］'
DECO_NOISE_PAT = re.compile(r'^[•■▪▫◆◇▲△▼▽○●◎□■]\s*[a-zA-Z]?\s*$', re.MULTILINE)


def split_frontmatter(text: str) -> tuple[str, str]:
    """frontmatter와 body 분리. frontmatter 없으면 ('', text)."""
    m = FRONTMATTER_PAT.match(text)
    if m:
        return m.group(1), m.group(2)
    return '', text


def parse_frontmatter_page_range(frontmatter: str) -> tuple[int, int] | None:
    """frontmatter `페이지: 91-120` 또는 `페이지: pp.68-84`에서 (min, max) 추출."""
    m = re.search(r'^페이지:\s*(.+)$', frontmatter, re.MULTILINE)
    if not m:
        return None
    val = m.group(1).strip()
    rm = PAGE_RANGE_IN_FM_PAT.search(val)
    if rm:
        try:
            return int(rm.group(1)), int(rm.group(2))
        except ValueError:
            return None
    return None


def extract_page_numbers(body: str, frontmatter: str = '') -> list[int]:
    """본문에서 페이지 번호 수집. 2가지 형식 모두 확인 후 실제 PDF 페이지인 것 선택.

    형식:
    1. `--- Page N ---` (위치: 줄 독립)
    2. `- N -` (단독 줄, 실제 PDF 페이지일 수 있음)

    선택 로직:
    - 양쪽 다 수집
    - frontmatter `페이지:` 범위와 비교해서 교집합이 많은 쪽을 선택
    - 둘 다 교집합 없으면 `--- Page N ---` 우선
    """
    marker_pages = sorted({int(m.group(1)) for m in PAGE_MARKER_PAT.finditer(body)})
    inline_pages = sorted({int(m.group(1)) for m in INLINE_PAGE_PAT.finditer(body)})

    fm_range = parse_frontmatter_page_range(frontmatter)
    if fm_range:
        fm_min, fm_max = fm_range
        fm_set = set(range(fm_min, fm_max + 1))

        marker_overlap = len(set(marker_pages) & fm_set)
        inline_overlap = len(set(inline_pages) & fm_set)

        # 겹침이 더 많은 쪽 선택
        if inline_overlap > marker_overlap:
            return inline_pages
        elif marker_overlap > 0:
            return marker_pages
        # 둘 다 겹침 없으면 아래 로직으로

    # frontmatter 정보 없거나 겹침 없음: marker 우선, 없으면 inline
    if marker_pages:
        return marker_pages
    return inline_pages


def add_pages_to_frontmatter(frontmatter: str, pages: list[int]) -> str:
    """frontmatter에 포함_페이지 필드 추가/갱신.

    - 이미 `포함_페이지:` 있으면 갱신
    - 없으면 `페이지:` 줄 바로 다음에 삽입. `페이지:` 없으면 frontmatter 맨 끝(--- 직전)에 삽입.
    """
    if not pages:
        return frontmatter

    pages_line = f'포함_페이지: {pages}\n'

    # 이미 있으면 갱신
    existing_pat = re.compile(r'^포함_페이지:\s*\[.*?\]\s*\n', re.MULTILINE)
    if existing_pat.search(frontmatter):
        return existing_pat.sub(pages_line, frontmatter)

    # 페이지: 필드 다음에 삽입
    page_field_pat = re.compile(r'^(페이지:\s*.*\n)', re.MULTILINE)
    m = page_field_pat.search(frontmatter)
    if m:
        insert_pos = m.end()
        return frontmatter[:insert_pos] + pages_line + frontmatter[insert_pos:]

    # 페이지: 없으면 frontmatter 맨 끝 --- 직전에 삽입
    close_pat = re.compile(r'^---\n', re.MULTILINE)
    matches = list(close_pat.finditer(frontmatter))
    if len(matches) >= 2:
        # frontmatter는 ---\n ... \n---\n 형태
        insert_pos = matches[-1].start()
        return frontmatter[:insert_pos] + pages_line + frontmatter[insert_pos:]

    return frontmatter


def clean_body(body: str) -> str:
    """본문 결정론적 정리."""
    # 1. Page 마커 줄 제거 (줄 전체)
    body = re.sub(r'^--- Page \d+ ---\s*\n?', '', body, flags=re.MULTILINE)

    # 2. 단독 줄 인라인 페이지 번호 제거 (e.g., "- 68 -" 단독 줄)
    body = re.sub(r'^\s*[-─]\s*\d+\s*[-─]\s*\n?', '', body, flags=re.MULTILINE)

    # 3. 전각 괄호 → 반각 (본문만, 코드블록/인라인코드 내부는 보존)
    # 간단 처리: 전체 치환 (법률 본문에 코드블록 거의 없음)
    body = body.replace(FULLWIDTH_PAREN_OPEN, '(')
    body = body.replace(FULLWIDTH_PAREN_CLOSE, ')')
    body = body.replace(FULLWIDTH_BRACKET_OPEN, '[')
    body = body.replace(FULLWIDTH_BRACKET_CLOSE, ']')

    # 4. 데코 노이즈 단독 줄 제거
    body = DECO_NOISE_PAT.sub('', body)

    # 5. 연속 공백 → 단일 공백 (라인 내)
    # 라인별로 처리해서 줄바꿈 보존
    lines = body.split('\n')
    new_lines = [MULTI_SPACE_PAT.sub(' ', line).rstrip() for line in lines]
    body = '\n'.join(new_lines)

    # 6. 연속 빈 줄 → 최대 1개 빈 줄
    body = MULTI_BLANK_PAT.sub('\n\n', body)

    return body


def backup_file(src: Path, backup_root: Path) -> Path:
    """원본 파일을 _trash 하위로 복사."""
    rel = src.relative_to(TEXTBOOK_ROOT)
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def process_file(path: Path, dry_run: bool = False, do_backup: bool = True) -> dict:
    """단일 파일 처리. 반환: 변경 통계 dict."""
    orig = path.read_text(encoding='utf-8')
    orig_size = len(orig)

    frontmatter, body = split_frontmatter(orig)

    # Page 수집 (frontmatter 범위 참조해서 실제 PDF 페이지 선택)
    pages = extract_page_numbers(body, frontmatter)

    # Body 정리
    new_body = clean_body(body)

    # Frontmatter에 포함_페이지 추가
    new_frontmatter = add_pages_to_frontmatter(frontmatter, pages) if frontmatter else frontmatter

    new_text = new_frontmatter + new_body
    new_size = len(new_text)

    changed = (new_text != orig)

    stats = {
        'path': str(path),
        'orig_size': orig_size,
        'new_size': new_size,
        'delta': orig_size - new_size,
        'pages_found': len(pages),
        'pages_list': pages,
        'changed': changed,
    }

    if changed and not dry_run:
        if do_backup:
            backup_file(path, BACKUP_ROOT)
        path.write_text(new_text, encoding='utf-8')

    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='변경 없이 통계만 출력')
    parser.add_argument('--no-backup', action='store_true', help='백업 건너뛰기')
    parser.add_argument('--sample', type=int, default=0, help='상위 N개만 처리 (테스트용)')
    parser.add_argument('paths', nargs='*', help='특정 파일 경로 (없으면 전체 _교재원문)')
    args = parser.parse_args()

    # 대상 파일 수집
    if args.paths:
        targets = [Path(p).resolve() for p in args.paths]
    else:
        targets = []
        for f in TEXTBOOK_ROOT.rglob('*.md'):
            if '_trash' in f.parts:
                continue
            if f.name == '_교재목차.md':
                continue
            targets.append(f)

    if args.sample > 0:
        targets = targets[:args.sample]

    print(f'대상: {len(targets)}개 파일')
    print(f'모드: {"DRY-RUN" if args.dry_run else "EXECUTE"}')
    print(f'백업: {"NO" if args.no_backup else str(BACKUP_ROOT)}')
    print()

    total_orig = 0
    total_new = 0
    changed_count = 0
    errors = []

    for f in targets:
        try:
            stats = process_file(f, dry_run=args.dry_run, do_backup=not args.no_backup)
            total_orig += stats['orig_size']
            total_new += stats['new_size']
            if stats['changed']:
                changed_count += 1
        except Exception as e:
            errors.append((f, str(e)))

    pct = (total_orig - total_new) / total_orig * 100 if total_orig > 0 else 0
    print(f'=== 요약 ===')
    print(f'  처리: {len(targets)}')
    print(f'  변경: {changed_count}')
    print(f'  원본 총 크기: {total_orig:,} chars ({total_orig/1024:.0f} KB)')
    print(f'  정리 총 크기: {total_new:,} chars ({total_new/1024:.0f} KB)')
    print(f'  감소: {total_orig - total_new:,} chars ({pct:.2f}%)')
    print(f'  에러: {len(errors)}')
    for f, e in errors[:5]:
        print(f'    {f}: {e}')


if __name__ == '__main__':
    main()
