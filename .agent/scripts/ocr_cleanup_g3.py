#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2차/3차 클린업 - batch2 그룹 3 교정본에서 잔여 판례 오인식 수정
대상: H:\내 드라이브\.agent\data\ocr_chunks_reviewed\민법\윤동환_민법의맥\
"""

import re
from pathlib import Path

OUT_ROOT = Path(r"H:\내 드라이브\.agent\data\ocr_chunks_reviewed\민법\윤동환_민법의맥")

def is_protected_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith('<!-- chunk_meta:') or stripped.startswith('<!-- p.')

def cleanup_line(line: str) -> str:
    if is_protected_line(line):
        return line

    # 1) 判例 후처리 잔재 (1차 교정 후 남은 패턴들)
    line = re.sub(r'\xed\x8c\x90\xeb\xa1\x80[夕\|lIj\s]*[lIj\|]*', '判例', line)  # 인코딩 후처리
    line = re.sub(r'判例[夕\|lIj\s]*[lIj\|]*', '判例', line)
    line = re.sub(r'判例\s+([가-힣])', r'判例는 \1', line)
    line = re.sub(r'判例는\s+는\s', '判例는 ', line)

    # 2) 미처리 判例 오인식 패턴
    # 判仇l, 判仇!, 判산lj, 判산1l, 判WI), 判,1, 判{夕|), 判{引) 등
    # - 判 뒤에 한자/특수문자/알파벳 조합 (例 아닌 것)
    line = re.sub(r'判仇[l!\s]', '判例', line)
    line = re.sub(r'判산[lj1\s]+', '判例', line)
    line = re.sub(r'判WI[)l\s]', '判例', line)
    line = re.sub(r'判,1', '判例', line)
    line = re.sub(r'判\{夕\|[)\s]', '判例', line)
    line = re.sub(r'判\{引[)l\s]', '判例', line)
    line = re.sub(r'判｛夕\|[)\s]', '判例', line)
    line = re.sub(r'判｛引[)l\s]', '判例', line)
    line = re.sub(r'判f~I[)\s]', '判例', line)
    line = re.sub(r'判f\:YI[Jj]', '判例', line)
    line = re.sub(r'判f71[Jj]', '判例', line)
    line = re.sub(r'判f[79]1[]\]j]?', '判例', line)

    # 3) 포괄 정리: 判 뒤에 例가 아닌 문자로 시작하는 OCR 잔재
    # 安전한 치환: 判 + 비한글/비공백/비例 문자 1-6개 → 判例
    line = re.sub(r'判(?!例)([^\s가-힣\n例]{1,6})', lambda m: '判例' if not m.group(1).startswith('例') else m.group(0), line)

    return line

def cleanup_file(path: Path) -> bool:
    raw = path.read_text(encoding='utf-8')
    lines = raw.split('\n')
    new_lines = [cleanup_line(l) for l in lines]
    new_text = '\n'.join(new_lines)
    if new_text != raw:
        path.write_text(new_text, encoding='utf-8')
        return True
    return False


def main():
    files = sorted(OUT_ROOT.glob('*.md'))
    total = len(files)
    modified = 0
    for i, f in enumerate(files, 1):
        changed = cleanup_file(f)
        if changed:
            modified += 1
            print(f"[{i:03d}/{total}] FIXED - {f.name}")
    print(f"\nDONE: {total} files, {modified} modified")

if __name__ == '__main__':
    main()
