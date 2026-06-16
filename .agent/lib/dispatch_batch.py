#!/usr/bin/env python3
"""LLM reflow 배치 디스패치 헬퍼.

기능:
- 표준 프롬프트 템플릿 로드 + 파일별 치환
- progress JSON에서 미완료 파일 N개 선택
- 각 파일용 프롬프트 (표준 템플릿 + 파일 경로 + 문맥) 생성

사용:
    python .agent/lib/dispatch_batch.py --book 서보학_형법총론 --count 10

출력: 각 파일에 대한 프롬프트 + agent description 짝
"""
import sys
import json
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브')
TEXTBOOK_ROOT = ROOT / 'sync' / '_교재원문'
STATE_PATH = ROOT / '.agent' / 'state' / 'llm_reflow_progress.json'
TEMPLATE_PATH = ROOT / '.agent' / 'lib' / '_reflow_prompt_standard.md'

BOOKS = {
    '윤동환_민법의맥': {
        'path': '민법/윤동환_민법의맥',
        'full_name': '윤동환 《민법의 맥》 24판',
        'topic': '민법 (민법총칙·물권·채권·가족상속)',
    },
    '강혜림_민법1': {
        'path': '민법/강혜림_민법1',
        'full_name': '김준호 《민법강의》 32판 (강혜림 교수 사용)',
        'topic': '민법 전반',
    },
    '박승수_민법기본사례': {
        'path': '민법/박승수_민법기본사례',
        'full_name': '박승수 《민법기본사례》 23판',
        'topic': '민법 사례연습',
    },
    '서보학_형법총론': {
        'path': '형법/서보학_형법총론',
        'full_name': '서보학 《새로 쓴 형법총론》 18판',
        'topic': '형법 총론',
    },
}


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    return {}


def collect_files(book_key: str) -> list[Path]:
    rel = BOOKS[book_key]['path']
    root = TEXTBOOK_ROOT / rel
    files = [f for f in root.rglob('*.md') if f.name != '_교재목차.md']
    files.sort(key=lambda f: f.stat().st_size)
    return files


def load_template() -> str:
    return TEMPLATE_PATH.read_text(encoding='utf-8')


def guess_chapter_topic(file_path: Path) -> str:
    """파일 stem에서 쟁점 토큰 추출."""
    stem = file_path.stem
    # Remove author/book suffix
    tokens = []
    for t in stem.split('_'):
        if t in ('윤동환', '민법의맥', '강혜림', '민법1', '민법강의', '박승수',
                 '민법기본사례', '서보학', '형법총론', '본1', '본2', '본3',
                 '민총A', '민총B', '채총A', '채총B', '친상A', '친상B', '물권', '채각'):
            continue
        if t.isdigit():
            continue
        tokens.append(t)
    return '·'.join(tokens) if tokens else stem


def cmd_batch(book_key: str, count: int):
    """다음 N개 파일 선택 + 각 파일용 프롬프트 출력."""
    state = load_state()
    if book_key not in state:
        print(f'[ERROR] 책 키 없음: {book_key}', file=sys.stderr)
        sys.exit(1)

    book_state = state[book_key]
    processed = set(book_state['completed']) | set(book_state['failed']) | set(book_state['skipped'])

    files = collect_files(book_key)
    next_files = [f for f in files if f.name not in processed][:count]

    if not next_files:
        print(f'[DONE] {book_key}: 남은 파일 없음', file=sys.stderr)
        return

    template = load_template()
    book_info = BOOKS[book_key]

    # 간단 출력: 각 파일의 정보만
    result = {
        'book': book_key,
        'book_full_name': book_info['full_name'],
        'count': len(next_files),
        'remaining': sum(1 for f in files if f.name not in processed),
        'files': [],
    }
    for f in next_files:
        chapter_topic = guess_chapter_topic(f)
        result['files'].append({
            'name': f.name,
            'path': str(f),
            'chapter_topic': chapter_topic,
            'size_kb': f.stat().st_size // 1024,
        })

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_complete_batch(book_key: str, files: list[str]):
    """여러 파일을 한 번에 completed로 표시."""
    state = load_state()
    if book_key not in state:
        print(f'[ERROR] 책 키 없음: {book_key}', file=sys.stderr)
        sys.exit(1)

    for file_name in files:
        book_state = state[book_key]
        for s in ('completed', 'failed', 'skipped'):
            if file_name in book_state[s]:
                book_state[s].remove(file_name)
        book_state['completed'].append(file_name)

    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f'[BATCH COMPLETE] {book_key}: {len(files)}개')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_batch = sub.add_parser('batch')
    p_batch.add_argument('--book', required=True, choices=list(BOOKS))
    p_batch.add_argument('--count', type=int, default=10)

    p_complete = sub.add_parser('complete-batch')
    p_complete.add_argument('--book', required=True, choices=list(BOOKS))
    p_complete.add_argument('--files', nargs='+', required=True)

    args = parser.parse_args()

    if args.cmd == 'batch':
        cmd_batch(args.book, args.count)
    elif args.cmd == 'complete-batch':
        cmd_complete_batch(args.book, args.files)


if __name__ == '__main__':
    main()
