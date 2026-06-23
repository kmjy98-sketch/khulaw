"""
신규 추출 38청크 정규화 (2026-04-30)
- yaml frontmatter 표준화 (tags 공백 제거, 따옴표)
- 카테고리별 페이지 푸터/헤더 제거
- 사건번호 백링크 보강
- 본문 0% 변경 (CLAUDE.md #1·#34)
"""
import os
import re
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

ROOT = Path(VAULT_ROOT)

# ----- 카테고리 정의 -----
CATEGORIES = [
    {
        'name': '헌법사례형',
        'dir': 'sync/_교재원문/헌법/해커스변호사_헌법사례형',
        'tags_clean': '교재원문, 헌법, 해커스변호사_헌법사례형, 사례형, 기출, 변호사시험',
        'footer_patterns': [
            re.compile(r'^\s*\d{1,3}\s*해커스변호[^\n]*law\.Hackers\.com.*$', re.MULTILINE),
            re.compile(r'^\s*해커스변호사[^\n]*law\.Hackers\.com.*$', re.MULTILINE),
            re.compile(r'^\s*law\.Hackers\.com\s*$', re.MULTILINE),
        ],
    },
    {
        'name': '김기용_책임론',
        'dir': 'sync/_교재원문/형법/김기용_compactOX/책임론',
        'tags_clean': '교재원문, 형법, 김기용_compactOX_책임론, OX, 형법총론, 책임론',
        'footer_patterns': [],
    },
    {
        'name': '김기용_미수범',
        'dir': 'sync/_교재원문/형법/김기용_compactOX/미수범',
        'tags_clean': '교재원문, 형법, 김기용_compactOX_미수범, OX, 형법총론, 미수범',
        'footer_patterns': [],
    },
    {
        'name': '김기용_공범론',
        'dir': 'sync/_교재원문/형법/김기용_compactOX/공범론',
        'tags_clean': '교재원문, 형법, 김기용_compactOX_공범론, OX, 형법총론, 공범론',
        'footer_patterns': [],
    },
    {
        'name': '송영곤_채권',
        'dir': 'sync/_교재원문/민법/송영곤_사례_채권',
        'tags_clean': '교재원문, 민법, 송영곤_사례연습_채권, 사례연습, 채권, 민사법',
        'footer_patterns': [
            # "저|4장 계약금| 181" / "제 1 장 계약 ｜ 23"
            re.compile(r'^\s*저\|\s*\d+장\s+[^\n|]+\|\s*\d+\s*$', re.MULTILINE),
            re.compile(r'^\s*제\s*\d+\s*장\s+[^\n|｜]+[\|｜]\s*\d+\s*$', re.MULTILINE),
        ],
    },
    {
        'name': '전경운_정규화',
        'dir': 'sync/_교재원문/민법/전경운_민법3',
        'tags_clean': '교재원문, 민법, 전경운_민법3, 민법기초이론, 물권법',
        'footer_patterns': [],
        'file_filter': lambda f: '교재_p001-050' in f or '교재_p051-100' in f or '교재_p101-150' in f,
    },
]

# 추가 사건번호 패턴 (헌법용)
HEONJAE_PATTERNS = [
    # 2009헌마, 2018헌바 등 - 이미 추출 스크립트에서 처리됨
    re.compile(r'(?<![\[0-9])(\d{4}헌(?:마|바|가|나|라|아|타|인|어)\d+(?:[·,\s]\d+)*)(?![\]0-9])'),
]
# 대법원 사건번호 추가 패턴
DAEPAN_PATTERNS = [
    re.compile(r'(?<![\[0-9])(\d{2,4}(?:다카|다|도|누|후|므|허|두|마|바|초|아|재)\d+(?:[·,\s]\d+)*)(?![\]0-9])'),
]


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith('---'):
        return '', text
    parts = text.split('---', 2)
    if len(parts) < 3:
        return '', text
    return parts[1], parts[2].lstrip('\n')


def parse_fm(fm_text: str) -> dict:
    fm = {}
    for ln in fm_text.strip().split('\n'):
        if ':' in ln:
            k, v = ln.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm


def remove_footer_patterns(body: str, patterns: list) -> int:
    """푸터/헤더 패턴 제거. (cleaned, removed_count) 반환."""
    count = 0
    for pat in patterns:
        new_body, n = pat.subn('', body)
        body = new_body
        count += n
    # 연속 빈 줄 정리
    body = re.sub(r'\n{3,}', '\n\n', body)
    return body, count


def remove_lone_digits(body: str) -> tuple[str, int]:
    """페이지 단독 숫자 라인 제거 (코드/표 내부 제외)."""
    lines = body.split('\n')
    out = []
    in_code = False
    removed = 0
    for ln in lines:
        s = ln.strip()
        if s.startswith('```'):
            in_code = not in_code
            out.append(ln)
            continue
        if in_code:
            out.append(ln)
            continue
        # 표 행이면 보존
        if s.startswith('|') and s.count('|') >= 2:
            out.append(ln)
            continue
        # 페이지 단독 숫자 (1~4자리, 선택적 dash)
        if re.fullmatch(r'-?\s*\d{1,4}\s*-?', s) and not (out and out[-1].strip().startswith('<!-- p.')):
            removed += 1
            continue
        out.append(ln)
    return '\n'.join(out), removed


def add_case_backlinks_safe(text: str) -> tuple[str, int]:
    """이미 [[..]] 안 감싸진 사건번호 백링크 추가."""
    out_lines = []
    in_code = False
    added = 0
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code = not in_code
            out_lines.append(line)
            continue
        if in_code or (stripped.startswith('|') and stripped.count('|') >= 2):
            out_lines.append(line)
            continue
        new_line = line
        for pat in HEONJAE_PATTERNS + DAEPAN_PATTERNS:
            def repl(m):
                nonlocal added
                tok = m.group(1)
                start = m.start()
                left = new_line[max(0, start-2):start]
                if left == '[[':
                    return tok
                added += 1
                return f'[[{tok}]]'
            new_line = pat.sub(repl, new_line)
        out_lines.append(new_line)
    return '\n'.join(out_lines), added


def normalize_yaml(fm_dict: dict, tags_clean: str, file_path: str) -> str:
    """yaml frontmatter 정규화."""
    out = ['---']
    out.append(f'tags: [{tags_clean}]')
    # 보존할 필드 (순서 유지)
    keys_order = ['교재', '판', '과목', '주제', '서브책자', '포함_페이지', '저자', '출처', '추출엔진', '추출일', '정규화일']
    for k in keys_order:
        if k in fm_dict:
            v = fm_dict[k]
            # 출처: 따옴표 감싸기 ([+/괄호] 포함된 경우)
            if k == '출처' and not (v.startswith('"') or v.startswith("'")):
                # PDF 이름에 [ 또는 + 포함된 경우만 quote
                if any(c in v for c in '[]+()'):
                    v = f'"{v}"'
            out.append(f'{k}: {v}')
    # 추가 표준 필드
    if '정규화일' not in fm_dict:
        out.append(f'정규화일: {datetime.now().strftime("%Y-%m-%d")}')
    out.append('---')
    return '\n'.join(out)


def normalize_file(file_path: Path, category: dict) -> dict:
    text = file_path.read_text(encoding='utf-8')
    fm_text, body = split_frontmatter(text)
    fm = parse_fm(fm_text)

    # 1. yaml 표준화
    new_fm = normalize_yaml(fm, category['tags_clean'], str(file_path))

    # 2. 푸터/헤더 제거
    body, footer_removed = remove_footer_patterns(body, category['footer_patterns'])

    # 3. 페이지 단독 숫자 라인 제거 (보강)
    body, digit_removed = remove_lone_digits(body)

    # 4. 사건번호 백링크 보강
    body, links_added = add_case_backlinks_safe(body)

    new_text = new_fm + '\n\n' + body

    file_path.write_text(new_text, encoding='utf-8')

    return {
        'file': file_path.name,
        'footer_removed': footer_removed,
        'lone_digits_removed': digit_removed,
        'backlinks_added': links_added,
        'final_size': len(new_text),
    }


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    summary = {}

    for cat in CATEGORIES:
        d = ROOT / cat['dir']
        if not d.exists():
            print(f'  SKIP (not found): {cat["name"]} -> {cat["dir"]}')
            continue
        files = sorted(d.glob('*.md'))
        flt = cat.get('file_filter')
        if flt:
            files = [f for f in files if flt(f.name)]
        results = []
        for f in files:
            r = normalize_file(f, cat)
            results.append(r)
        total_footer = sum(r['footer_removed'] for r in results)
        total_digits = sum(r['lone_digits_removed'] for r in results)
        total_links = sum(r['backlinks_added'] for r in results)
        summary[cat['name']] = {
            'files': len(results),
            'footer_removed': total_footer,
            'lone_digits_removed': total_digits,
            'backlinks_added': total_links,
        }
        print(f'  {cat["name"]:>18s} | files={len(results):>2d} footer={total_footer:>3d} digits={total_digits:>3d} links={total_links:>4d}')

    print('\n=== summary ===')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
