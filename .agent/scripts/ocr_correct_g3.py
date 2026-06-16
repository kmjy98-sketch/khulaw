#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR 교정 스크립트 — batch2 그룹 3
대상: H:\내 드라이브\.agent\state\batch2_g3.json
출력: H:\내 드라이브\.agent\data\ocr_chunks_reviewed\
"""

import json
import os
import re
import shutil
from pathlib import Path

BASE = Path(r"H:\내 드라이브")
INPUT_JSON = BASE / ".agent" / "state" / "batch2_g3.json"
OCR_ROOT = BASE / ".agent" / "data" / "ocr_chunks"
OUT_ROOT = BASE / ".agent" / "data" / "ocr_chunks_reviewed"

# ── 보호 패턴 (변경 금지) ──────────────────────────────────
PROTECTED_PATTERNS = [
    re.compile(r'<!--\s*p\.\d+\s*-->'),          # <!-- p.NNN -->
    re.compile(r'<!--\s*chunk_meta:.*?-->'),       # <!-- chunk_meta: ... -->
    re.compile(r'\*\*제\d+조(?:의\d+)?\*\*'),     # **제N조**
    re.compile(r'제\d+조(?:의\d+)?'),              # 제N조 (단독)
]

def is_protected_line(line: str) -> bool:
    """chunk_meta 줄 또는 페이지 마커 줄은 보호"""
    stripped = line.strip()
    if stripped.startswith('<!-- chunk_meta:') or stripped.startswith('<!-- p.'):
        return True
    return False

# ── OCR 교정 규칙 ─────────────────────────────────────────
def correct_ocr(text: str) -> str:
    lines = text.split('\n')
    corrected = []
    for line in lines:
        if is_protected_line(line):
            corrected.append(line)
            continue
        line = correct_line(line)
        corrected.append(line)
    return '\n'.join(corrected)

def correct_line(line: str) -> str:
    # 1) 한자 오인식 수정
    # 判例 계열 오인식 (判lfl, 判1夕l, 判f91, 判竹lI, 判f7l, 判1911, 判{§|, 判i?II, 判j~lj 등)
    line = re.sub(r'判[lf1fi\{}\[\]|竹夕j~i\?][0-9lfl7891§\?]*[lj|]*', '判例', line)
    line = re.sub(r'判例[lj|]+', '判例', line)  # 후처리

    # 判伊], 判1§II, 判~I, 判f§I], 判{91), 判{§II, 判j91 등 추가 패턴
    line = re.sub(r'判[伊~f\{][§91lj\]I|]*', '判例', line)

    # 2) 숫자/영문 혼용 오인식
    # 연도 패턴에서 'C' → '0': 2C03 → 2003, 2CXX3 → 2003, 2COO → 2000 등
    line = re.sub(r'\b(1|2)(C)(0{0,2}[0-9])\b', lambda m: m.group(1) + '0' + m.group(3), line)
    line = re.sub(r'\b(20)C([0-9])', r'\g<1>0\2', line)
    line = re.sub(r'\b(20)CX+([0-9])', r'\g<1>0\2', line)
    line = re.sub(r'\b(19|20)([0-9C]{2})\b', lambda m: m.group(0).replace('C', '0'), line)

    # 판례번호에서 f → 0: [.f → [.0, Cf → 0 등
    line = re.sub(r'([0-9])Cf([0-9])', r'\g<1>0\2', line)
    line = re.sub(r'([0-9])[.][f]([0-9])', r'\g<1>.\g<2>', line)
    line = re.sub(r'\[\.f([0-9])', r'[\g<1>', line)
    line = re.sub(r'\[\.([麟腐])', r'[', line)  # 특수문자 제거

    # 3) 특수문자/OCR 아티팩트 수정
    # 'l' → '1' (숫자 문맥)
    line = re.sub(r'(?<=[다판결])(\s+)l([0-9])', r'\g<1>\g<2>', line)  # 판례번호 앞 l
    line = re.sub(r'\b([0-9]{4})l([0-9])', r'\g<1>1\g<2>', line)      # 연도 뒤 l

    # 4) 붙어버린 띄어쓰기 복원 (한국어 특수 케이스)
    # '이익을포기' → '이익을 포기', '소멸하게한' → '소멸하게 한' 등
    # 주의: 법률 용어, 판례번호 쪽은 건드리지 않음

    # 조사 뒤에 붙은 체언/용언 분리 (너무 공격적이면 오히려 해가 되므로 명시적 케이스만)
    corrections = [
        # 띄어쓰기
        (r'채무자가파산', '채무자가 파산'),
        (r'채권자가주채무자에', '채권자가 주채무자에'),
        (r'보증인이주재무자의', '보증인이 주채무자의'),
        (r'이익을포기', '이익을 포기'),
        (r'이익을해하지', '이익을 해하지'),
        (r'권리를행사할', '권리를 행사할'),
        (r'권리를재판상', '권리를 재판상'),
        (r'권리를소멸시효', '권리를 소멸시효'),
        (r'청구할수있다', '청구할 수 있다'),
        (r'청구할수있는', '청구할 수 있는'),
        (r'청구할수없다', '청구할 수 없다'),
        (r'행사할수있다', '행사할 수 있다'),
        (r'행사할수있는', '행사할 수 있는'),
        (r'행사할수없다', '행사할 수 없다'),
        (r'볼수있다', '볼 수 있다'),
        (r'볼수없다', '볼 수 없다'),
        (r'할수없다', '할 수 없다'),
        (r'할수있다', '할 수 있다'),
        (r'인정할수있다', '인정할 수 있다'),
        (r'소멸하게한', '소멸하게 한'),
        (r'성립하지않', '성립하지 않'),
        (r'허용하지않', '허용하지 않'),
        (r'적용되지않', '적용되지 않'),
        (r'인정되지않', '인정되지 않'),
        (r'존재하지않', '존재하지 않'),
        (r'해당하지않', '해당하지 않'),
        (r'발생하지않', '발생하지 않'),
        (r'있는바,', '있는바, '),
        # 한자 오인식 추가
        (r'재권자', '채권자'),   # 재→채
        (r'재권양도', '채권양도'),
        (r'재무자', '채무자'),   # 재→채
        (r'재무불이행', '채무불이행'),
        (r'재채무', '채채무'),   # 이중 교정 방지: 일단 스킵
        (r'재무를', '채무를'),
        (r'재무에', '채무에'),
        (r'재무인', '채무인'),
        (r'재무액', '채무액'),
        (r'재무이행', '채무이행'),
        (r'재무자의', '채무자의'),
        (r'재무자가', '채무자가'),
        (r'재무자에', '채무자에'),
        (r'재무자는', '채무자는'),
        (r'재무자를', '채무자를'),
        (r'재무자에게', '채무자에게'),
        # '주재무' → '주채무'
        (r'주재무자', '주채무자'),
        (r'주재무를', '주채무를'),
        (r'주재무의', '주채무의'),
        (r'주재무가', '주채무가'),
        (r'주재무에', '주채무에'),
        (r'주재무인', '주채무인'),
        (r'주재무는', '주채무는'),
        (r'주재무도', '주채무도'),
        (r'주재무', '주채무'),    # 나머지 전체
        # '보증재무' → '보증채무'
        (r'보증재무', '보증채무'),
        # '공재무' → '공채무' / '부재무' → '부채무'
        (r'연대재무자', '연대채무자'),
        (r'연대재무', '연대채무'),
        (r'비재변제', '비채변제'),  # 비채변제
        # 기타 '재' → '채' (명사 문맥)
        (r'금전재무', '금전채무'),
        (r'이행재무', '이행채무'),
        (r'담보재무', '담보채무'),
        (r'분담재무', '분담채무'),
        (r'근재무', '근채무'),
        (r'중첩재무', '중첩채무'),
    ]

    for pattern, replacement in corrections:
        line = re.sub(pattern, replacement, line)

    # 이중 교정 방지: '채채무' → '채무'
    line = line.replace('채채무', '채무')

    # 5) 이어붙은 두 문장 분리 (마침표 뒤 바로 대문자·가나·한글이 붙은 경우)
    # "하였다.判例는" → "하였다. 判例는"
    line = re.sub(r'([다하였음됩니다]\.)([가-힣A-Z])', r'\1 \2', line)
    # "한다(대판 XXXX). 다만" 형태 이미 줄바꿈 된 경우는 해당 없음

    # 6) 명백한 숫자 오인식 수정
    # 'l ' 이 숫자 '1' 역할: 'l회' → '1회', 'l항' → '1항'
    line = re.sub(r'\bl([회항조절관]\b)', r'1\1', line)

    # 7) OCR 잔해 문자 제거 (특수기호 오인식)
    # '거호巴l' '判伊' 등 미처리 잔재 정리
    line = re.sub(r'거호巴[l|]', '', line)
    line = re.sub(r'寒', '98', line)   # 연도: '1寒.4.11.' → '1998.4.11.' 등 문맥별로 어렵지만 일단 표시
    line = re.sub(r'奭', '2005', line) # 유사한 패턴
    # '2C03' → '2003' 추가
    line = re.sub(r'2C0([0-9])', r'200\1', line)
    line = re.sub(r'2CXX0', '2000', line)
    line = re.sub(r'2CXX([0-9])', r'200\1', line)
    line = re.sub(r'2COO', '2000', line)
    line = re.sub(r'1002\.', '2002.', line)   # '1002.5.12' → '2002.5.12' (앞 자리 오인식)
    line = re.sub(r'1000\.', '2000.', line)
    line = re.sub(r'1001\.', '2001.', line)
    line = re.sub(r'1002\.', '2002.', line)
    line = re.sub(r'1004\.', '2004.', line)
    line = re.sub(r'1003\.', '2003.', line)

    # 8) '1 얗3' 등 연도 오인식
    line = re.sub(r'1\s*얗\s*3', '1993', line)

    return line


def process_chunk(chunk_path_rel: str) -> tuple[bool, bool]:
    """
    Returns (processed: bool, modified: bool)
    """
    # 입력 경로 (절대)
    src = BASE / chunk_path_rel

    # 출력 경로: .agent\data\ocr_chunks\ 이후 부분을 out_root 아래에 배치
    rel_after = chunk_path_rel.replace('.agent\\data\\ocr_chunks\\', '')
    rel_after = rel_after.replace('.agent/data/ocr_chunks/', '')
    dst = OUT_ROOT / rel_after

    # 이미 존재하면 건너뜀
    if dst.exists():
        return False, False

    if not src.exists():
        print(f"  [MISSING] {src}")
        return False, False

    # Read
    raw = src.read_text(encoding='utf-8')

    # OCR 교정
    corrected = correct_ocr(raw)
    modified = (corrected != raw)

    # Write
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(corrected, encoding='utf-8')

    return True, modified


def main():
    records = json.loads(INPUT_JSON.read_text(encoding='utf-8'))
    total = len(records)
    processed = 0
    modified = 0
    skipped = 0

    for i, rec in enumerate(records, 1):
        chunk_path = rec['chunk_path']
        ok, mod = process_chunk(chunk_path)
        if ok:
            processed += 1
            if mod:
                modified += 1
            status = "MOD" if mod else "COPY"
            print(f"[{i:03d}/{total}] {status} - {Path(chunk_path).name}")
        else:
            # 이미 존재하거나 소스 없음
            dst_check = OUT_ROOT / chunk_path.replace('.agent\\data\\ocr_chunks\\', '')
            if dst_check.exists():
                skipped += 1
                print(f"[{i:03d}/{total}] SKIP - {Path(chunk_path).name}")
            else:
                print(f"[{i:03d}/{total}] ERROR - {chunk_path}")

    print(f"\nDONE: total={total}, processed={processed}, modified={modified}, skipped={skipped}")


if __name__ == '__main__':
    main()
