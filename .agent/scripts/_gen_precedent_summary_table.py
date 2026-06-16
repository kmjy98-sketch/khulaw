#!/usr/bin/env python3
"""과목별 판례 종합 관리 표 생성.

소스: sync/_백업/교재원문_문서_백업_2026-05-22/_판례색인/{민법,형법,헌법}/
출력: .auto-memory/wiki/판례종합표_{민사|형사|헌법}.md

칼럼: 순위 | 사건번호 (위키링크) | 선고일 | 총 빈도 | 관련 조문 | 상태 | 주요 출현 교재

총 빈도: references_all_2026-04-18_v2.json case_summary.top50 우선,
         없으면 스텁 출현 교재 표의 출현 합계.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BACKUP_IDX_ROOT = Path('H:/내 드라이브/sync/_백업/교재원문_문서_백업_2026-05-22/_판례색인')
REFS_JSON = Path('H:/내 드라이브/.agent/state/references_all_2026-04-18_v2.json')
OUT_DIR = Path('H:/내 드라이브/.auto-memory/wiki')

SUBJECTS = [
    ('민법', '민사'),
    ('형법', '형사'),
    ('헌법', '헌법'),
]

ARTICLE_TRUNCATE = 70


def load_freq_map() -> dict:
    """references JSON → {사건번호: 총 빈도} 맵."""
    if not REFS_JSON.exists():
        return {}
    with REFS_JSON.open(encoding='utf-8') as f:
        data = json.load(f)
    top50 = data.get('case_summary', {}).get('top50', {})
    return {k: v for k, v in top50.items() if isinstance(v, int)}


def read_md(p: Path) -> tuple:
    """마크다운 파일 → (frontmatter dict, body str)."""
    text = p.read_text(encoding='utf-8')
    if not text.startswith('---'):
        return {}, text
    end = text.find('\n---', 3)
    if end < 0:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4:].lstrip('\n')
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm, body


def parse_articles(body: str) -> str:
    """## 참조조문 섹션 → 조문 텍스트 (최대 ARTICLE_TRUNCATE자)."""
    in_sec = False
    parts = []
    for line in body.split('\n'):
        s = line.strip()
        if re.match(r'^##\s+참조조문', s):
            in_sec = True
            continue
        if in_sec:
            if s.startswith('## '):
                break
            if s:
                parts.append(s)
    text = ' '.join(parts)
    # [1] [2] 등 항 접두사 제거
    text = re.sub(r'\[\d+\]\s*', '', text).strip()
    if len(text) > ARTICLE_TRUNCATE:
        text = text[:ARTICLE_TRUNCATE - 1] + '…'
    return text or '-'


def parse_sources_table(body: str) -> list:
    """## 출현 교재 표 파싱 → [(book_name, context_path, count), ...]."""
    in_sec = False
    rows = []
    for line in body.split('\n'):
        s = line.strip()
        if re.match(r'^##\s+출현 교재', s):
            in_sec = True
            continue
        if in_sec:
            if s.startswith('## '):
                break
            if not s.startswith('|'):
                continue
            if '교재 파일' in s or re.match(r'^\|[-| ]+\|$', s):
                continue
            parts = [p.strip() for p in s.split('|')]
            parts = [p for p in parts if p]
            if len(parts) < 2:
                continue
            book = re.sub(r'\[\[([^\]]+)\]\]', r'\1', parts[0])
            ctx = parts[1].strip('`').strip()
            try:
                cnt = int(parts[2]) if len(parts) >= 3 else 1
            except ValueError:
                cnt = 1
            rows.append((book, ctx, cnt))
    return rows


def top_books_str(rows: list, n: int = 3) -> str:
    """상위 n개 교재 문자열 (book(count) 형식)."""
    top = sorted(rows, key=lambda x: -x[2])[:n]
    return ', '.join(f'{b}({c})' for b, _, c in top) if top else '-'


def build_records(sub_dir: Path, freq_map: dict) -> list:
    """과목 폴더 → 레코드 리스트 (빈도 내림차순)."""
    records = []
    for f in sorted(sub_dir.iterdir()):
        if f.suffix != '.md' or f.name.startswith('_'):
            continue
        fm, body = read_md(f)
        case_num = fm.get('사건번호', f.stem)
        date = fm.get('선고일', '-')
        status_raw = fm.get('상태', 'stub')
        status = 'Filled' if status_raw == 'filled' else 'Stub'
        articles = parse_articles(body)
        rows = parse_sources_table(body)
        freq = freq_map.get(case_num)
        if freq is None:
            freq = sum(r[2] for r in rows)
        books = top_books_str(rows)
        records.append({
            'case': case_num,
            'date': date,
            'freq': freq,
            'articles': articles,
            'status': status,
            'books': books,
        })
    records.sort(key=lambda r: -r['freq'])
    return records


def write_table_md(records: list, subject_label: str, out_path: Path) -> None:
    lines = [
        f'# 판례 종합 관리 표 — {subject_label}',
        '',
        '> 자동 생성: `_gen_precedent_summary_table.py`  ',
        '> 소스: `sync/_백업/교재원문_문서_백업_2026-05-22/_판례색인/`',
        '',
        '| 순위 | 사건번호 | 선고일 | 총 빈도 | 관련 조문 | 상태 | 주요 출현 교재 |',
        '|------|----------|--------|---------|-----------|------|---------------|',
    ]
    for i, rec in enumerate(records, 1):
        link = f'[[{rec["case"]}]]'
        lines.append(
            f'| {i} | {link} | {rec["date"]} | {rec["freq"]} '
            f'| {rec["articles"]} | {rec["status"]} | {rec["books"]} |'
        )
    lines.append('')
    out_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'  → {out_path.name}  ({len(records)}건)')


def main():
    freq_map = load_freq_map()
    if freq_map:
        print(f'빈도 데이터: {len(freq_map)}건 로드')
    else:
        print('빈도 데이터 없음 — 스텁 합계 사용')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sub_name, label in SUBJECTS:
        sub_dir = BACKUP_IDX_ROOT / sub_name
        if not sub_dir.exists():
            print(f'[SKIP] {sub_dir} 없음')
            continue
        records = build_records(sub_dir, freq_map)
        out_path = OUT_DIR / f'판례종합표_{label}.md'
        write_table_md(records, label, out_path)
    print('완료')


if __name__ == '__main__':
    main()
