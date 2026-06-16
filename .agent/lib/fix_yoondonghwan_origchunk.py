#!/usr/bin/env python3
"""rename_chunks_batch3 부작용 보정: 새 파일의 frontmatter `원본_chunk` 필드를 옛 stem으로 복원."""
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# rename_chunks_batch3_yoondonghwan.MAPPING 재사용
sys.path.insert(0, str(Path('H:/내 드라이브/.agent/lib')))
from rename_chunks_batch3_yoondonghwan import MAPPING, SOURCE_DIR

REVERSE = {v: k for k, v in MAPPING.items()}

def main():
    fixed = 0
    skipped = 0
    for new_stem, old_stem in REVERSE.items():
        new_path = SOURCE_DIR / f'{new_stem}.md'
        if not new_path.exists():
            print(f'  SKIP: {new_stem} 없음')
            skipped += 1
            continue
        text = new_path.read_text(encoding='utf-8')
        # frontmatter 안에서 `원본_chunk:` 라인 찾기
        # 현재 값은 새 stem이거나 또 다른 형태일 수 있음
        new_text = re.sub(
            r'(?m)^원본_chunk:.*$',
            f'원본_chunk: {old_stem}',
            text
        )
        if new_text != text:
            new_path.write_text(new_text, encoding='utf-8')
            fixed += 1
    print(f'복원: {fixed}, 건너뜀: {skipped}')

if __name__ == '__main__':
    main()
