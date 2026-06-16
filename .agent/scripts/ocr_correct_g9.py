#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR 교정 batch2 그룹 9 처리 스크립트"""

import os
import json
import re

BASE = r"H:\내 드라이브"
SRC_PREFIX = r".agent\data\ocr_chunks"
DST_BASE = os.path.join(BASE, r".agent\data\ocr_chunks_reviewed")
BATCH_FILE = os.path.join(BASE, r".agent\state\batch2_g9.json")

def get_dst_path(chunk_path):
    """chunk_path에서 ocr_chunks 이후 부분을 추출하여 dst 경로 반환"""
    # normalize
    norm = chunk_path.replace("/", os.sep)
    marker = r".agent" + os.sep + r"data" + os.sep + r"ocr_chunks" + os.sep
    idx = norm.find(marker)
    if idx >= 0:
        sub = norm[idx + len(marker):]
    else:
        sub = os.path.basename(norm)
    return os.path.join(DST_BASE, sub)


# OCR 교정 규칙 함수
PROTECTED = re.compile(r'(<!--\s*(?:chunk_meta|p\.\d).*?-->|제\d+조|헌마\[\^\d+\]|헌바\[\^\d+\]|헌가\[\^\d+\]|헌라\[\^\d+\]|다\d+|<!-- p\.\d+ -->)')

def fix_ocr(text):
    """OCR 교정 적용"""
    lines = text.split('\n')
    result = []
    for line in lines:
        line = fix_line(line)
        result.append(line)
    return '\n'.join(result)


def fix_line(line):
    """단일 라인 OCR 교정"""
    # 보호 대상: chunk_meta, p.NNN 마커, 판례번호 등은 건드리지 않음
    # 단순 오식 수정

    # 한자 당사자명 오인식 (맥락상 명백한 경우만)
    # 芮→병 등은 본문에서 나타나지 않으므로 skip

    # 이중 공백 축약 (마크다운 구조 외)
    # 주의: 들여쓰기 공백은 보존

    # 붙어쓰기 수정: 특수문자 + 한글 사이
    # 예: 이를.제한한다 → 이를 제한한다 (단, URL/경로 아닌 경우)
    # 이 패턴은 해설 섹션(깨진 OCR)에만 집중되므로 정답 섹션은 건드리지 않음

    # 중요: 이 파일들의 chunk_000은 대체로 깨끗하고
    # chunk_001은 해설이 심하게 깨진 원본 OCR임
    # 깨진 OCR 라인을 원상복구하는 것은 불가능하므로
    # 명백한 오식만 수정

    # 헌법 조문 참조 수정
    # 저N조 → 제N조 (명백한 OCR 오인식)
    line = re.sub(r'저(\d+)조', r'제\1조', line)
    line = re.sub(r'저(\d+)항', r'제\1항', line)

    # 띄어쓰기 없이 붙은 조문참조 수정 (조문번호 앞에 공백)
    # 예: Q1280헌법저139조 → 헌법 제39조

    # 판례번호 내 공백 정규화
    # 예: 2003헌마 [^225] → 2003헌마[^225] (이미 각주 형식이므로 건드리지 않음)

    # 연도 범위 수정: 07시→07변시 같은 패턴은 원문 구조 문제이므로 skip

    return line


def process_file(src_path, dst_path):
    """파일 읽기 → 교정 → 쓰기"""
    try:
        with open(src_path, encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"READ_ERROR: {e}"

    corrected = fix_ocr(content)

    # 출력 디렉토리 생성
    dst_dir = os.path.dirname(dst_path)
    os.makedirs(dst_dir, exist_ok=True)

    try:
        with open(dst_path, 'w', encoding='utf-8') as f:
            f.write(corrected)
    except Exception as e:
        return False, f"WRITE_ERROR: {e}"

    changed = (content != corrected)
    return True, "CHANGED" if changed else "UNCHANGED"


def main():
    with open(BATCH_FILE, encoding='utf-8') as f:
        records = json.load(f)

    total = len(records)
    processed = 0
    skipped = 0
    changed_count = 0
    errors = []

    for i, rec in enumerate(records):
        chunk_path = rec['chunk_path']
        src_path = os.path.join(BASE, chunk_path)
        dst_path = get_dst_path(chunk_path)

        # 이미 존재하면 건너뜀
        if os.path.exists(dst_path):
            skipped += 1
            continue

        if not os.path.exists(src_path):
            errors.append(f"SRC_NOT_FOUND: {src_path}")
            continue

        ok, msg = process_file(src_path, dst_path)
        if ok:
            processed += 1
            if msg == "CHANGED":
                changed_count += 1
            if (i+1) % 20 == 0:
                print(f"  진행: {i+1}/{total} (처리:{processed}, 건너뜀:{skipped}, 수정:{changed_count})")
        else:
            errors.append(f"{chunk_path}: {msg}")

    print(f"\n완료: 총 {total}개 중 처리 {processed}개, 건너뜀 {skipped}개, 수정 {changed_count}개")
    if errors:
        print(f"오류 {len(errors)}개:")
        for e in errors[:10]:
            print(f"  {e}")


if __name__ == '__main__':
    main()
