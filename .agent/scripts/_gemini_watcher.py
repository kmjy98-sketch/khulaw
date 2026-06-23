"""Gemini Op 로그 watcher — 표준 라이브러리만 사용.

상시 가동:
- .auto-memory/gemini_ops/logs/ 폴링 (3초 간격)
- 신규/변경 파일 → frontmatter + 본문 파싱 → _verify_rules 적용
- 결과를 .auto-memory/gemini_ops/flag.json에 누적
- watcher 자체 로그는 _watcher.log
- 예외 발생 시 5초 후 재시도 (작업 스케줄러 재시작과 이중 보호)

부팅 시 자동 시작: _register_watcher_task.ps1 참조
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# 표준 라이브러리만 사용 (watchdog 미사용)
sys.path.insert(0, str(Path(__file__).parent))
from _verify_rules import evaluate  # noqa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

BASE = Path(VAULT_ROOT)
LOG_DIR = BASE / '.auto-memory/gemini_ops/logs'
FLAG_PATH = BASE / '.auto-memory/gemini_ops/flag.json'
STATE_PATH = BASE / '.auto-memory/gemini_ops/_watcher_state.json'
WATCHER_LOG = BASE / '.auto-memory/gemini_ops/_watcher.log'

POLL_INTERVAL = 3.0  # 초
ERROR_BACKOFF = 5.0  # 예외 발생 시 대기 시간


def watcher_log(msg: str) -> None:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}\n'
    try:
        WATCHER_LOG.parent.mkdir(parents=True, exist_ok=True)
        with WATCHER_LOG.open('a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass  # 로그 자체 실패는 무시


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with STATE_PATH.open(encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'mtimes': {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open('w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_flag() -> dict:
    if FLAG_PATH.exists():
        try:
            with FLAG_PATH.open(encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'updated_at': None, 'entries': []}


def save_flag(flag: dict) -> None:
    FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FLAG_PATH.open('w', encoding='utf-8') as f:
        json.dump(flag, f, ensure_ascii=False, indent=2)


def parse_log(path: Path) -> tuple:
    """로그 파일 → (frontmatter dict, body str)."""
    text = path.read_text(encoding='utf-8')
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


def scan_logs(state: dict) -> list:
    """변경된 로그 파일 목록 반환."""
    changed = []
    if not LOG_DIR.exists():
        return changed
    for entry in LOG_DIR.iterdir():
        if not entry.is_file() or entry.suffix != '.md':
            continue
        if entry.name.startswith('_'):
            continue
        mtime = entry.stat().st_mtime
        prev = state['mtimes'].get(str(entry))
        if prev is None or mtime > prev + 0.5:
            changed.append(entry)
            state['mtimes'][str(entry)] = mtime
    return changed


def process_log(path: Path) -> dict:
    """로그 1건 처리 → flag.json에 들어갈 entry 생성."""
    fm, body = parse_log(path)
    result = evaluate(body, fm)
    return {
        'log_path': str(path.relative_to(BASE)).replace('\\', '/'),
        'log_name': path.name,
        'checked_at': datetime.now().isoformat(timespec='seconds'),
        'severity': result['severity'],
        'violations': result['violations'],
        'spec_source': fm.get('spec_source', ''),
        'verify_status': fm.get('verify_status', 'pending'),
    }


def update_flag(new_entries: list) -> None:
    """flag.json 갱신 — 같은 log_path 재처리 시 덮어쓰기."""
    flag = load_flag()
    by_path = {e['log_path']: e for e in flag['entries']}
    for entry in new_entries:
        by_path[entry['log_path']] = entry
    flag['entries'] = sorted(
        by_path.values(),
        key=lambda e: e['checked_at'],
        reverse=True,
    )
    flag['updated_at'] = datetime.now().isoformat(timespec='seconds')
    flag['summary'] = {
        'red': sum(1 for e in flag['entries'] if e['severity'] == 'red'),
        'yellow': sum(1 for e in flag['entries'] if e['severity'] == 'yellow'),
        'green': sum(1 for e in flag['entries'] if e['severity'] == 'green'),
        'total': len(flag['entries']),
    }
    save_flag(flag)


def tick() -> None:
    """1회 폴링 사이클."""
    state = load_state()
    changed = scan_logs(state)
    if not changed:
        return
    entries = []
    for path in changed:
        try:
            entry = process_log(path)
            entries.append(entry)
            watcher_log(f'processed {path.name} → {entry["severity"]}')
        except Exception as e:
            watcher_log(f'ERROR processing {path.name}: {e}')
    if entries:
        update_flag(entries)
        save_state(state)


def main() -> None:
    watcher_log('watcher started')
    while True:
        try:
            tick()
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            watcher_log('watcher stopped (KeyboardInterrupt)')
            break
        except Exception as e:
            watcher_log(f'FATAL: {e}\n{traceback.format_exc()}')
            time.sleep(ERROR_BACKOFF)


if __name__ == '__main__':
    main()
