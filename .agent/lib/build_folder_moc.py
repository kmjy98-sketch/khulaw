#!/usr/bin/env python3
"""폴더별 목차를 백업 목차 기반으로 갱신 — 새 노트 파일과 매칭."""
import sys
import re
from pathlib import Path

FOLDERS = [
    ('총칙', 'sync/민법/총칙', '5.기타/_trash/2026-04-10/sync_민법_pre재작성/목차_민법총칙.md'),
    ('물권', 'sync/민법/물권', '5.기타/_trash/2026-04-10/sync_민법_pre재작성/목차_민법물권.md'),
    ('담보물권', 'sync/민법/담보물권', '5.기타/_trash/2026-04-10/sync_민법_pre재작성/목차_민법담보물권.md'),
    ('채권총론', 'sync/민법/채권총론', '5.기타/_trash/2026-04-10/sync_민법_pre재작성/목차_민법채권총론.md'),
    ('채권각론', 'sync/민법/채권각론', '5.기타/_trash/2026-04-10/sync_민법_pre재작성/목차_민법채권각론.md'),
]

LINK_PAT = re.compile(r'\[\[([^\]|#]+)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]')

# 매핑 (백업의 옛 이름 → 새 이름)
MAPPING = {
    '매매_담보책임': '매도인_담보책임',
    '물권적청구권': '물권적_청구권',
}


def build_one(folder: str, note_dir: Path, backup: Path) -> None:
    actual = {f.stem for f in note_dir.glob('*.md') if not f.stem.startswith('_')}

    if not backup.exists():
        print(f'[skip] {backup} not found')
        return

    text = backup.read_text(encoding='utf-8')
    referenced: set[str] = set()

    def replace_link(m: re.Match) -> str:
        name = m.group(1).strip()
        new_name = MAPPING.get(name, name)
        referenced.add(new_name)
        return f'[[{new_name}]]'

    text = LINK_PAT.sub(replace_link, text)

    missing = referenced - actual
    extra = actual - referenced

    text = re.sub(
        r'^---\n.*?\n---',
        f'---\ntags: [민법, {folder}, MOC]\naliases: [민법{folder} 목차, _민법{folder}_목차]\n---',
        text,
        count=1,
        flags=re.DOTALL,
    )

    if extra:
        text += '\n\n## 신규/누락 보강 노트\n\n'
        for n in sorted(extra):
            text += f'- [[{n}]]\n'

    if missing:
        text += (
            '\n\n<!-- 누락 (백업 목차 참조 → 실제 노트 없음): '
            + ', '.join(sorted(missing))
            + ' -->\n'
        )

    out = note_dir.parent / f'_민법{folder}_목차.md'
    out.write_text(text, encoding='utf-8')
    print(
        f'{folder}: {len(actual)} notes, '
        f'백업참조 {len(referenced)}, 누락 {len(missing)}, 추가 {len(extra)}'
    )
    if missing:
        print(f'  누락: {sorted(missing)}')
    if extra:
        print(f'  추가: {sorted(extra)}')


def main() -> int:
    sys.stdout.reconfigure(encoding='utf-8')
    for folder, note_dir_str, backup_str in FOLDERS:
        build_one(folder, Path(note_dir_str), Path(backup_str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
