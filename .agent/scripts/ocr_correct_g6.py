#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR 교정 batch2 그룹 6 처리 스크립트"""
import os
import re
import json
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

BASE = VAULT_ROOT
BATCH_JSON = os.path.join(BASE, r'.agent\state\batch2_g6.json')
OCR_CHUNKS_DIR = os.path.join(BASE, r'.agent\data\ocr_chunks')
REVIEWED_DIR = os.path.join(BASE, r'.agent\data\ocr_chunks_reviewed')

# 보호 패턴: 이 줄은 변경하지 않음
PROTECTED_LINE_RE = re.compile(
    r'(<!--\s*chunk_meta:|<!--\s*p\.\d+|^\s*#+ |^\s*\*\*제\d+조|^\s*tags:|^\s*교재:|^\s*판:|^\s*과목:|^\s*원본_chunk:|^\s*페이지:|^\s*포함_페이지:|^\s*서브책자:|^\s*쟁점:)',
    re.MULTILINE
)


def is_protected_line(line):
    """변경 금지 줄 여부"""
    stripped = line.strip()
    # chunk_meta 주석
    if '<!-- chunk_meta:' in line:
        return True
    if '<!-- p.' in line:
        return True
    # YAML 프론트매터
    if stripped.startswith('tags:') or stripped.startswith('교재:') or \
       stripped.startswith('판:') or stripped.startswith('과목:') or \
       stripped.startswith('원본_chunk:') or stripped.startswith('페이지:') or \
       stripped.startswith('포함_페이지:') or stripped.startswith('서브책자:') or \
       stripped.startswith('쟁점:'):
        return True
    return False


def ocr_correct_line(line):
    """단일 줄 OCR 교정"""
    if is_protected_line(line):
        return line

    original = line

    # 1. 전각 특수문자 → 반각 (맥락상 괄호로 사용되는 경우)
    line = line.replace('\uff1c', '(')   # ＜ → (
    line = line.replace('\uff1e', ')')   # ＞ → )
    line = line.replace('\uff08', '(')   # （ → (
    line = line.replace('\uff09', ')')   # ） → )

    # 2. 붙은 띄어쓰기 복원 — 동사/형용사 앞
    # "수있다/수있고/수없다/수없고"
    line = re.sub(r'수있다', '수 있다', line)
    line = re.sub(r'수있고', '수 있고', line)
    line = re.sub(r'수있으며', '수 있으며', line)
    line = re.sub(r'수있으므로', '수 있으므로', line)
    line = re.sub(r'수없다', '수 없다', line)
    line = re.sub(r'수없고', '수 없고', line)
    line = re.sub(r'수없으며', '수 없으며', line)
    line = re.sub(r'수없으므로', '수 없으므로', line)

    # "하지않는/하지않은/하지않으면/하지않고/하지않을"
    line = re.sub(r'하지않는', '하지 않는', line)
    line = re.sub(r'하지않은', '하지 않은', line)
    line = re.sub(r'하지않으면', '하지 않으면', line)
    line = re.sub(r'하지않고', '하지 않고', line)
    line = re.sub(r'하지않을', '하지 않을', line)
    line = re.sub(r'하지않아', '하지 않아', line)

    # "이어야한다/이어야하고/이어야하며"
    line = re.sub(r'이어야한다', '이어야 한다', line)
    line = re.sub(r'이어야하고', '이어야 하고', line)
    line = re.sub(r'이어야하며', '이어야 하며', line)

    # "있어야한다/있어야하고"
    line = re.sub(r'있어야한다', '있어야 한다', line)
    line = re.sub(r'있어야하고', '있어야 하고', line)
    line = re.sub(r'있어야하며', '있어야 하며', line)

    # "되어야한다/되어야하고"
    line = re.sub(r'되어야한다', '되어야 한다', line)
    line = re.sub(r'되어야하고', '되어야 하고', line)

    # "하여야한다/하여야하고"
    line = re.sub(r'하여야한다', '하여야 한다', line)
    line = re.sub(r'하여야하고', '하여야 하고', line)
    line = re.sub(r'하여야하며', '하여야 하며', line)

    # "않은한" → "않은 한"
    line = re.sub(r'않은한', '않은 한', line)
    line = re.sub(r'없는한', '없는 한', line)

    # "후채" → "후 채" (문맥: 소멸시효 완성 후채무를 → 후 채무를)
    # 단, "후채권" 같은 합성어는 제외해야 하므로 조심
    # "후채무" → "후 채무"
    line = re.sub(r'후채무를', '후 채무를', line)
    line = re.sub(r'후채무이므로', '후 채무이므로', line)

    # "후이를" → "후 이를"
    line = re.sub(r'후이를', '후 이를', line)

    # "인경우에는" → "인 경우에는"
    line = re.sub(r'([가-힣])인경우에는', r'\1인 경우에는', line)
    line = re.sub(r'([가-힣])인경우에도', r'\1인 경우에도', line)
    line = re.sub(r'([가-힣])인경우', r'\1인 경우', line)

    # "한경우에는" → "한 경우에는"
    line = re.sub(r'([가-힣])한경우에는', r'\1한 경우에는', line)
    line = re.sub(r'([가-힣])한경우에도', r'\1한 경우에도', line)
    line = re.sub(r'([가-힣])한경우', r'\1한 경우', line)

    # "때에는" 붙은 경우
    line = re.sub(r'([가-힣])때에는', r'\1 때에는', line)
    line = re.sub(r'([가-힣])때에도', r'\1 때에도', line)

    # "것으로볼" → "것으로 볼"
    line = re.sub(r'것으로볼', '것으로 볼', line)
    line = re.sub(r'것으로보아', '것으로 보아', line)
    line = re.sub(r'것으로본다', '것으로 본다', line)

    # "것이아니라" → "것이 아니라"
    line = re.sub(r'것이아니라', '것이 아니라', line)
    line = re.sub(r'것이아니고', '것이 아니고', line)

    # "후받은" → "후 받은"
    line = re.sub(r'후받은', '후 받은', line)

    # "도달되었다" 앞 붙은 경우들은 문맥상 교정 어렵고 비교적 정확하므로 생략

    return line


def ocr_correct(text):
    """전체 텍스트 OCR 교정"""
    lines = text.split('\n')
    corrected_lines = []
    changed = False

    for line in lines:
        new_line = ocr_correct_line(line)
        if new_line != line:
            changed = True
        corrected_lines.append(new_line)

    return '\n'.join(corrected_lines), changed


def process_file(src_path, out_path):
    """단일 파일 처리"""
    out_dir = os.path.dirname(out_path)
    os.makedirs(out_dir, exist_ok=True)

    with open(src_path, encoding='utf-8') as f:
        content = f.read()

    corrected, was_changed = ocr_correct(content)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(corrected)

    return was_changed


def main():
    with open(BATCH_JSON, encoding='utf-8') as f:
        records = json.load(f)

    total = 0
    skipped = 0
    modified = 0
    copied = 0
    errors = []

    for rec in records:
        chunk_rel = rec['chunk_path'].replace('/', os.sep)
        rel_after = chunk_rel.replace(r'.agent\data\ocr_chunks' + os.sep, '')
        out_path = os.path.join(REVIEWED_DIR, rel_after)
        src_path = os.path.join(BASE, chunk_rel)

        total += 1

        if os.path.exists(out_path):
            skipped += 1
            continue

        if not os.path.exists(src_path):
            errors.append('NOT_FOUND: ' + src_path)
            continue

        try:
            was_changed = process_file(src_path, out_path)
            if was_changed:
                modified += 1
            else:
                copied += 1
        except Exception as e:
            errors.append('ERROR: ' + src_path + ' : ' + str(e))

    processed = total - skipped - len(errors)
    print('총 %d개 레코드' % total)
    print('  건너뜀(기존): %d' % skipped)
    print('  처리됨: %d' % processed)
    print('    수정됨: %d' % modified)
    print('    변경없음(복사): %d' % copied)
    if errors:
        print('  오류: %d' % len(errors))
        for e in errors[:10]:
            print('    ' + e)


if __name__ == '__main__':
    main()
