#!/usr/bin/env python3
"""LLM reflow 디스패치 및 진행 상황 추적 (단계 D).

상태 파일: .agent/state/llm_reflow_progress.json

기능:
1. 교재별 파일 목록 생성 (크기 오름차순)
2. 미완료 파일 선택 (completed/failed/skipped 제외)
3. 배치 단위로 다음 N개 파일 경로 반환
4. 파일 완료 시 상태 업데이트

사용:
    # 초기화
    python .agent/lib/dispatch_llm_reflow.py init

    # 다음 5개 파일 선택 (서보학 책)
    python .agent/lib/dispatch_llm_reflow.py next --book 서보학_형법총론 --count 5

    # 파일 완료 기록
    python .agent/lib/dispatch_llm_reflow.py complete --book 서보학_형법총론 --file 고의_서보학_형법총론.md

    # 진행 상황 요약
    python .agent/lib/dispatch_llm_reflow.py status
"""
import sys
import json
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브')
TEXTBOOK_ROOT = ROOT / 'sync' / '_교재원문'
STATE_PATH = ROOT / '.agent' / 'state' / 'llm_reflow_progress.json'

BOOKS = {
    # 기존 등록 (일부 완료)
    '윤동환_민법의맥': '민법/윤동환_민법의맥',
    '강혜림_민법1': '민법/강혜림_민법1',
    '박승수_민법기본사례': '민법/박승수_민법기본사례',
    '서보학_형법총론': '형법/서보학_형법총론',
    '송영곤_쟁점노트': '민법/송영곤_쟁점노트',
    # 추가 등록 — 미진행 교재
    '김기용_형법교안': '형법/김기용_형법교안',
    '김성돈_형법총론': '형법/김성돈_형법총론',
    '강성민_헌법OX': '헌법/강성민_헌법OX',
    '법조윤리_한권탁_기출': '선택법/법조윤리_한권탁_기출',
    '곽낙규_사례연습': '민법/곽낙규_사례연습',
    '민법의해석': '민법/민법의해석',
    # 추가 등록 — reflow_progress_log 기준 완료 교재 (재가동 시 참조)
    '이진_헌법원리1': '헌법/이진_헌법원리1',
    '송영곤_논점민법_보충': '민법/송영곤_논점민법_보충',
    '송영곤_논점민법_본책': '민법/송영곤_논점민법_본책',
    '송영곤_사례': '민법/송영곤_사례',
    '송영곤_사례연습2': '민법/송영곤_사례연습2',
    '송영곤_요건사실론': '민법/송영곤_요건사실론',
    # 2026-04-18 증분 — 수정 및 진행.md #17 미반영 PDF 처리 결과
    '홍형철_기본형법': '형법/홍형철_기본형법',
    '전경운_민법3': '민법/전경운_민법3',
    '반반형법': '형법/반반형법',
    '작은변사기_형법': '형법/작은변사기_형법',
    '이인규_사례연습': '형법/이인규_사례연습',
}


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    return {}


def save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


EXCLUDED_DIR_NAMES = {'_backup_phase1', '_backup_phase2', '_backup_phase25', '_재추출', '_legacy', '_archive'}


def collect_files(book_key: str) -> list[Path]:
    """책의 모든 .md 파일 (크기 오름차순). 백업·재추출·레거시 디렉터리 제외."""
    rel = BOOKS[book_key]
    root = TEXTBOOK_ROOT / rel
    files = [
        f for f in root.rglob('*.md')
        if f.name != '_교재목차.md'
        and not (set(f.parts) & EXCLUDED_DIR_NAMES)
    ]
    files.sort(key=lambda f: f.stat().st_size)
    return files


def cmd_init():
    """상태 파일 초기화."""
    state = {}
    for book_key in BOOKS:
        files = collect_files(book_key)
        state[book_key] = {
            'total': len(files),
            'completed': [],
            'failed': [],
            'skipped': [],
        }
    save_state(state)
    print(f'[INIT] 상태 파일 생성: {STATE_PATH}')
    for book, info in state.items():
        print(f'  {book}: 총 {info["total"]} 파일')


def cmd_next(book_key: str, count: int):
    """다음 N개 파일 선택 (완료/실패/스킵 제외)."""
    state = load_state()
    if book_key not in state:
        print(f'[ERROR] 책 키 없음: {book_key}')
        sys.exit(1)

    book_state = state[book_key]
    processed = set(book_state['completed']) | set(book_state['failed']) | set(book_state['skipped'])

    files = collect_files(book_key)
    next_files = []
    for f in files:
        if f.name not in processed:
            next_files.append(f)
            if len(next_files) >= count:
                break

    if not next_files:
        print(f'[DONE] {book_key}: 모든 파일 처리됨')
        return

    print(f'[NEXT {book_key}] {len(next_files)}개 선택 (남은: {len(files) - len(processed)})')
    for f in next_files:
        print(f'  {f}')


def cmd_complete(book_key: str, file_name: str, status: str = 'completed'):
    """파일 완료 기록."""
    state = load_state()
    if book_key not in state:
        print(f'[ERROR] 책 키 없음: {book_key}')
        sys.exit(1)

    book_state = state[book_key]
    if status not in ('completed', 'failed', 'skipped'):
        print(f'[ERROR] 상태는 completed|failed|skipped 중 하나')
        sys.exit(1)

    # 중복 제거
    for s in ('completed', 'failed', 'skipped'):
        if file_name in book_state[s]:
            book_state[s].remove(file_name)

    book_state[status].append(file_name)
    save_state(state)
    print(f'[{status.upper()}] {book_key}/{file_name}')


def cmd_status():
    """진행 상황 요약."""
    state = load_state()
    if not state:
        print('[EMPTY] 상태 파일이 없거나 비어있음')
        return

    print(f'{"책":25s} {"총":>5s} {"완료":>5s} {"실패":>5s} {"스킵":>5s} {"진행률":>8s}')
    print('-' * 60)
    total_all = 0
    completed_all = 0
    for book, info in state.items():
        total = info['total']
        comp = len(info['completed'])
        fail = len(info['failed'])
        skip = len(info['skipped'])
        pct = (comp + fail + skip) / total * 100 if total > 0 else 0
        total_all += total
        completed_all += comp
        print(f'{book:25s} {total:>5d} {comp:>5d} {fail:>5d} {skip:>5d} {pct:>7.1f}%')
    print('-' * 60)
    print(f'{"합계":25s} {total_all:>5d} {completed_all:>5d} '
          f'                  {completed_all/total_all*100:>7.1f}%')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    sub.add_parser('init')

    p_next = sub.add_parser('next')
    p_next.add_argument('--book', required=True, choices=list(BOOKS))
    p_next.add_argument('--count', type=int, default=5)

    p_comp = sub.add_parser('complete')
    p_comp.add_argument('--book', required=True, choices=list(BOOKS))
    p_comp.add_argument('--file', required=True)
    p_comp.add_argument('--status', default='completed',
                        choices=['completed', 'failed', 'skipped'])

    sub.add_parser('status')

    args = parser.parse_args()

    if args.cmd == 'init':
        cmd_init()
    elif args.cmd == 'next':
        cmd_next(args.book, args.count)
    elif args.cmd == 'complete':
        cmd_complete(args.book, args.file, args.status)
    elif args.cmd == 'status':
        cmd_status()


if __name__ == '__main__':
    main()
