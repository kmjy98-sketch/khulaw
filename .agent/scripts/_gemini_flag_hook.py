"""SessionStart hook — flag.json 요약을 stdout에 출력.

Claude Code가 세션 시작 시 이 스크립트를 실행하고,
stdout 내용을 첫 메시지 context에 prepend함.

red/yellow가 있을 때만 출력 (green-only면 출력 없음 → 토큰 소비 0).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

# Windows에서도 한글 출력 안정화
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

FLAG_PATH = Path(vp('.auto-memory', 'gemini_ops', 'flag.json'))


def main() -> int:
    if not FLAG_PATH.exists():
        return 0
    try:
        with FLAG_PATH.open(encoding='utf-8') as f:
            flag = json.load(f)
    except Exception:
        return 0

    summary = flag.get('summary', {})
    red = summary.get('red', 0)
    yellow = summary.get('yellow', 0)

    # green만 있으면 출력 0 — 토큰 절약
    if red == 0 and yellow == 0:
        return 0

    lines = ['## Gemini Ops Watcher 알림', '']
    lines.append(f'- 마지막 갱신: {flag.get("updated_at", "-")}')
    lines.append(f'- 상태 요약: red={red} / yellow={yellow} / green={summary.get("green", 0)} / total={summary.get("total", 0)}')
    lines.append('')

    if red > 0:
        lines.append('### RED (Opus 검토 권장)')
        for entry in flag.get('entries', []):
            if entry.get('severity') != 'red':
                continue
            lines.append(f'- `{entry["log_name"]}` (spec: {entry.get("spec_source", "-")})')
            for v in entry.get('violations', [])[:3]:
                if v['severity'] == 'red':
                    lines.append(f'  - {v["message"]}')
        lines.append('')

    if yellow > 0:
        lines.append('### YELLOW (Sonnet 검토 권장)')
        shown = 0
        for entry in flag.get('entries', []):
            if entry.get('severity') != 'yellow':
                continue
            if shown >= 5:
                lines.append(f'- ... 외 {yellow - shown}건')
                break
            lines.append(f'- `{entry["log_name"]}`')
            for v in entry.get('violations', [])[:2]:
                if v['severity'] == 'yellow':
                    lines.append(f'  - {v["message"]}')
            shown += 1
        lines.append('')

    lines.append('정밀 검토: `/감시` 또는 직접 `flag.json` 확인')
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
