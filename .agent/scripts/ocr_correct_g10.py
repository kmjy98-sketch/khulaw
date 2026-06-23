#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR 교정 스크립트 — batch2 g10 형법 185개 청크
교재 유형: 원문OCR형(김성돈, 서보학) vs 리플로우형(반반형법, 홍형철, 이인규, 작은변사기, 김기용)
"""

import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────────────────────
# 공통 OCR 교정 패턴 (모든 소스 공통)
# ─────────────────────────────────────────────────────────────────────────────

COMMON_REPLACEMENTS = [
    # 당사자 한자 오인식
    ('甲', '갑'), ('乙', '을'), ('丙', '병'), ('丁', '정'), ('戊', '무'),
    ('己', '기'), ('庚', '경'), ('辛', '신'), ('壬', '임'), ('癸', '계'),
    # 괄호/기호
    ('(甲)', '(갑)'), ('(乙)', '(을)'), ('(丙)', '(병)'), ('(丁)', '(정)'),
]

# ─────────────────────────────────────────────────────────────────────────────
# 서보학_형법총론 교정 (원문OCR형, 띄어쓰기/오타 교정 강화)
# ─────────────────────────────────────────────────────────────────────────────

# 서보학 교재에서 흔히 나타나는 OCR 오인식 패턴
SEO_PATTERN_REPLS = [
    # 자모 오인식
    ('있없다', '있었다'),
    ('없없다', '없었다'),
    ('되없다', '되었다'),
    ('신설되없고', '신설되었고'),
    ('신설되없다', '신설되었다'),
    ('개정이 있있다', '개정이 있었다'),
    ('개정이 있없다', '개정이 있었다'),
    ('나온 것은', '나온 것은'),
    # 조사·어미 연결
    ('름 ', '를 '),
    ('올 ', '를 '),
    ('울', '을'),
    ('흘', '를'),
    ('틀', '를'),
    ('카 하는', '가 하는'),
    ('씨 ', '서 '),
    ('씻다', '썼다'),
    ('잖다', '않다'),
    ('쉽제', '쉽게'),
    ('알기 쉽게', '알기 쉽게'),
    ('잇다', '있다'),
    ('잎다', '있다'),
    ('같다 .', '같다.'),
    # 판례 표기
    ('대법원판레', '대법원 판례'),
    ('법이론체계', '법이론 체계'),
    ('법전-대학원', '법학전문대학원'),
    ('형법충론', '형법총론'),
    ('형법충홍', '형법총론'),
    ('형법이론체계', '형법이론 체계'),
    ('함양하는방향으로', '함양하는 방향으로'),
    ('사례해결능력', '사례해결 능력'),
    ('기본서의', '기본서의'),
]

# ─────────────────────────────────────────────────────────────────────────────
# 김성돈_형법총론 교정 (원문OCR형)
# ─────────────────────────────────────────────────────────────────────────────

KIM_PATTERN_REPLS = [
    # 각주 번호 OCR 오인식 (숫자 + 영어 혼입)
    # 소문자 로마자 섹션 번호 오인식 (이미 처리된 패턴들)
]

# ─────────────────────────────────────────────────────────────────────────────
# 범용 OCR 오인식 정규식 교정 (모든 소스)
# ─────────────────────────────────────────────────────────────────────────────

def apply_common_corrections(text: str, source_type: str) -> str:
    """공통 OCR 교정 적용"""
    # 당사자 한자 오인식 (주석/메타데이터 블록 제외)
    # 단, 판례번호·조문번호가 포함된 줄은 건드리지 않음
    lines = text.split('\n')
    result = []
    for line in lines:
        # 마커 줄·메타데이터·코드블록은 건드리지 않음
        if (line.startswith('<!-- ') or
            line.startswith('---') or
            line.startswith('```') or
            '판결번호' in line or
            re.search(r'\d+도\d+', line)):  # 판례번호 포함 줄
            result.append(line)
            continue
        # 당사자 한자만 단어 단위로 교체
        for old, new in COMMON_REPLACEMENTS:
            line = line.replace(old, new)
        result.append(line)
    return '\n'.join(result)


def apply_seobohak_corrections(text: str) -> str:
    """서보학 교재 특화 OCR 교정"""
    for old, new in SEO_PATTERN_REPLS:
        text = text.replace(old, new)

    # 공백 오류: 문장 끝에 불필요한 공백 제거
    text = re.sub(r' +\n', '\n', text)
    # 연속 공백 2개 이상 → 1개
    text = re.sub(r'  +', ' ', text)
    # 마침표 앞 공백 제거: "형이다 ." → "형이다."
    text = re.sub(r' \.(\s)', r'.\1', text)
    text = re.sub(r' \.($)', r'.', text)

    return text


def apply_reflowed_corrections(text: str) -> str:
    """리플로우형 교재 교정 (최소한)"""
    # 당사자 한자만 변환
    for old, new in COMMON_REPLACEMENTS:
        text = text.replace(old, new)
    # 기본 공백 정리
    text = re.sub(r' +\n', '\n', text)
    return text


def apply_kimsungdon_corrections(text: str) -> str:
    """김성돈 교재 특화 OCR 교정"""
    # 기본 공통 교정
    for old, new in COMMON_REPLACEMENTS:
        text = text.replace(old, new)

    # 로마자 섹션 번호 오인식 교정
    # "n." → "II.", "m." → "III.", "rv." → "IV." 등
    # 섹션 헤더 패턴에서만 적용 (줄 앞부분)
    lines = text.split('\n')
    result = []
    for line in lines:
        # 헤더 줄에서 로마자 오인식 교정
        if re.match(r'^#{1,6}\s', line):
            line = re.sub(r'^(#{1,6}\s+)n\.', r'\1II.', line)
            line = re.sub(r'^(#{1,6}\s+)m\.', r'\1III.', line)
            line = re.sub(r'^(#{1,6}\s+)in\.', r'\1III.', line)
            line = re.sub(r'^(#{1,6}\s+)rv\.', r'\1IV.', line)
            line = re.sub(r'^(#{1,6}\s+)v\.', r'\1V.', line)
        # 각주 번호 OCR 정리 (영문자+숫자 혼입)
        # [^숫자] 형식 보존, 오인식 패턴 처리
        result.append(line)
    text = '\n'.join(result)

    # 공백 정리
    text = re.sub(r' +\n', '\n', text)
    text = re.sub(r'  +', ' ', text)

    return text


def correct_file(src_path: str, out_path: str) -> bool:
    """OCR 교정 후 저장. 변경이 있으면 True 반환."""
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            original = f.read()
    except Exception as e:
        print(f'  [ERROR] 읽기 실패: {src_path} — {e}')
        return False

    # 소스 유형 판별 (경로에서)
    if '서보학_형법총론' in src_path:
        corrected = apply_seobohak_corrections(original)
    elif '김성돈_형법총론' in src_path:
        corrected = apply_kimsungdon_corrections(original)
    else:
        # 리플로우형 (반반형법, 홍형철, 이인규, 작은변사기, 김기용)
        corrected = apply_reflowed_corrections(original)

    changed = (corrected != original)

    # 출력 디렉터리 생성
    out_dir = os.path.dirname(out_path)
    os.makedirs(out_dir, exist_ok=True)

    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(corrected)
    except Exception as e:
        print(f'  [ERROR] 쓰기 실패: {out_path} — {e}')
        return False

    return changed


def main():
    todo_file = vp('.agent', 'state', 'g10_todo_remaining.txt')

    with open(todo_file, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]

    total = len(lines)
    processed = 0
    modified = 0
    errors = 0

    print(f'처리 대상: {total}개')

    for i, line in enumerate(lines, 1):
        parts = line.split('|||')
        if len(parts) != 2:
            print(f'[{i}/{total}] 잘못된 형식: {line}')
            errors += 1
            continue

        src_path, out_path = parts
        fname = os.path.basename(src_path)

        # 이미 처리된 파일 skip
        out_dir = os.path.dirname(out_path)
        try:
            existing = os.listdir(out_dir)
            if fname in existing:
                print(f'[{i}/{total}] SKIP (기존): {fname}')
                processed += 1
                continue
        except:
            pass

        changed = correct_file(src_path, out_path)
        processed += 1
        if changed:
            modified += 1

        status = 'MOD' if changed else 'COPY'
        if i % 10 == 0 or i <= 5:
            print(f'[{i}/{total}] {status}: {fname}')

    print()
    print(f'완료: 총 {processed}개 처리, {modified}개 수정됨, {errors}개 오류')


if __name__ == '__main__':
    main()
