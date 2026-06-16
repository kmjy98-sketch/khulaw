# -*- coding: utf-8 -*-
"""
batch3 OCR 교정 스크립트 (score 0.0~0.1 구간)
"""
import os, json, re, sys

BASE = 'H:/내 드라이브'


def load_chunk_list():
    with open(BASE + '/.agent/state/batch3_g4.json', encoding='utf-8') as f:
        return json.load(f)


def get_paths(c):
    cp = c['chunk_path']
    cp_fwd = cp.replace('\\', '/')
    prefix = '.agent/data/ocr_chunks/'
    if cp_fwd.startswith(prefix):
        suffix = cp_fwd[len(prefix):]
    else:
        suffix = cp_fwd
    src_path = BASE + '/' + cp_fwd
    dst_path = BASE + '/.agent/data/ocr_chunks_reviewed/' + suffix
    return src_path, dst_path


def ensure_dir(path):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)


# ──────────────────────────────────────────────
# OCR 교정 함수
# ──────────────────────────────────────────────

def correct_ocr(text, filename=''):
    """OCR 오류를 교정한다. 내용 추가/삭제 금지, 오류 교정만."""
    lines = text.split('\n')
    result = []
    in_frontmatter = False
    frontmatter_done = False
    frontmatter_count = 0

    for i, line in enumerate(lines):
        # frontmatter 추적
        if i == 0 and line.strip() == '---':
            in_frontmatter = True
            frontmatter_count = 1
            result.append(line)
            continue
        if in_frontmatter and line.strip() == '---':
            frontmatter_count += 1
            if frontmatter_count >= 2:
                in_frontmatter = False
                frontmatter_done = True
            result.append(line)
            continue
        if in_frontmatter:
            result.append(line)
            continue

        # chunk_meta 주석 보존
        if line.startswith('<!-- chunk_meta:') or line.startswith('<!-- p.'):
            result.append(line)
            continue

        corrected = correct_line(line)
        result.append(corrected)

    return '\n'.join(result)


def correct_line(line):
    """한 줄의 OCR 오류를 교정한다."""
    # 1. 판례색인 특수 패턴 교정
    # 잘못된 판례번호 패턴들
    line = re.sub(r'대판\s*19呂(\d)', r'대판 19\g<1>', line)  # 19呂7 → 1987
    line = re.sub(r'대판\s*19으(\d)', r'대판 19\g<1>', line)  # 19으7 → 1987
    line = re.sub(r'대판\s*199U\.', r'대판 1991.', line)      # 199U. → 1991.
    line = re.sub(r'대판\s*19913\.', r'대판 1991.3.', line)    # 19913. → 1991.3.
    line = re.sub(r'대판\s*199(\d)\.', r'대판 199\g<1>.', line)

    # 판례번호 내 OCR 깨짐
    # 87다카'2088 → 87다카2088 (작은따옴표 제거)
    line = re.sub(r'(대판\s+\d{4}\.\d+\.\d+[^\n]*?)\^(\d)', r'\g<1>\g<2>', line)
    line = re.sub(r"(\d+다카?)'(\d+)", r'\g<1>\g<2>', line)
    line = re.sub(r"(\d+다카?)`(\d+)", r'\g<1>\g<2>', line)

    # 2. 연도+판례번호 붙여쓰기 오류 in 판례목록
    # "대판 1982.6.22. 81다으대판" → 두 줄로 분리
    line = re.sub(r'(대판 \d{4}\.\d+\.\d+\.\s*\[\[[\w]+\]\])\s*대판', r'\g<1>\n대판', line)

    # 3. 연도번호 OCR 오류
    line = re.sub(r'\b19呂(\d)\.', r'19\g<1>.', line)   # 呂 → 8
    line = re.sub(r'\b19으(\d)\.', r'19\g<1>.', line)   # 으 → (숫자)

    # 특정 패턴
    line = line.replace('대판 19呂7.', '대판 1987.')
    line = line.replace('대판 19으7.', '대판 1987.')
    line = line.replace('대판 199U.', '대판 1991.')

    # 4. 판례번호 내 특수문자 교정
    # 84다키'188 → 84다카188
    line = re.sub(r'(\d+)다키\'(\d+)', r'\g<1>다카\g<2>', line)
    # &4다카 → 84다카
    line = re.sub(r'&(\d)다카', r'8\g<1>다카', line)
    # &4다 → 84다
    line = re.sub(r'&(\d)다\b', r'8\g<1>다', line)
    # 어다카2093 → (앞 숫자 복원 어렵지만 패턴 유지)
    # 85^71-1009 → 판례번호 특수문자 제거
    line = re.sub(r'(\d{4}\.\d+\.\d+\.)\s*\d+\^(\d+)-(\d+)', r'\g<1>', line)

    # 5. 줄 중간의 OCR 쓰레기 텍스트 제거 (판례색인)
    # 판례목록에서 페이지번호 다음에 오는 OCR 깨짐 기호들
    # 패턴: 숫자, 숫자= 또는 숫자® 등 단독 줄
    if is_ocr_garbage_line(line):
        return ''

    # 6. 판례번호 뒤 이상 문자 제거
    # [[80다577]] 805, 처럼 실제 페이지번호는 유지
    # 하지만 "80다：1548" 처럼 콜론이 들어간 경우
    line = re.sub(r'(\d+다[가-힣]*):(\d+)', r'\g<1>\g<2>', line)

    # 7. 줄 끝 불필요한 단독 기호 정리 (판례색인 내 단독 줄)
    stripped = line.strip()
    if stripped in ['=', '<', '®', 'S', 's', 'o', 'M', 'X', '§', '§']:
        return ''

    # 8. 형법/민법 교재 OCR 오류
    # "제 4편일반적" → "제4편 일반적" (공백 오류)
    line = re.sub(r'제\s+(\d+)편([가-힣])', r'제\g<1>편 \g<2>', line)
    line = re.sub(r'제\s+(\d+)장([가-힣])', r'제\g<1>장 \g<2>', line)
    line = re.sub(r'제\s+(\d+)절([가-힣])', r'제\g<1>절 \g<2>', line)
    line = re.sub(r'제\s+(\d+)\s+장', r'제\g<1>장', line)
    line = re.sub(r'제\s+(\d+)\s+절', r'제\g<1>절', line)

    return line


def is_ocr_garbage_line(line):
    """판례색인에서 OCR로 깨진 쓰레기 줄인지 확인."""
    stripped = line.strip()
    if not stripped:
        return False

    # 단독 숫자 + 기호 패턴 (예: 532=, 575,', 848.', 655«, 522*)
    if re.match(r'^\d{1,4}[=®§『«*%\s]+$', stripped):
        return True
    # 숫자 + 특수문자 + 숫자 패턴 (예: 3®, 3M, 109%)
    if re.match(r'^\d{1,4}[®§%«*\'\"wS]\s*$', stripped):
        return True
    # 단독 특수문자
    if re.match(r'^[=<>®§«*%oSsXMm\^~]\s*$', stripped):
        return True
    # 기호 + 숫자 (예: ©0)
    if re.match(r'^[©®°]\d+\s*$', stripped):
        return True
    # 짧은 줄에 기호 포함된 쓰레기 (예: "8cf7", "S", "껺")
    if len(stripped) <= 5 and not re.match(r'^[\w가-힣]+$', stripped):
        if re.search(r'[©®°§«»*%\^~|<>{}]', stripped):
            return True
    # 단독 한글 한 글자 이하 (의미없는 OCR 잔류)
    if re.match(r'^[쯔짜껺]\s*$', stripped):
        return True

    return False


# ──────────────────────────────────────────────
# 판례색인 특화 교정
# ──────────────────────────────────────────────

def correct_precedent_index(text):
    """판례색인 파일 특화 교정."""
    lines = text.split('\n')
    result = []
    in_frontmatter = False
    frontmatter_count = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # frontmatter 처리
        if i == 0 and stripped == '---':
            in_frontmatter = True
            frontmatter_count = 1
            result.append(line)
            continue
        if in_frontmatter and stripped == '---':
            frontmatter_count += 1
            if frontmatter_count >= 2:
                in_frontmatter = False
            result.append(line)
            continue
        if in_frontmatter:
            result.append(line)
            continue

        # 빈 줄 유지
        if not stripped:
            result.append(line)
            continue

        # chunk_meta 보존
        if stripped.startswith('<!-- '):
            result.append(line)
            continue

        # 헤더 보존
        if stripped.startswith('#'):
            result.append(line)
            continue

        # 쓰레기 줄 제거 (먼저 체크)
        if is_ocr_garbage_line(line):
            continue

        # 판례 항목 줄 (대판으로 시작) 또는 [[링크]] 줄
        # 대판 다음에 숫자 또는 한자 섞인 연도 모두 포함
        is_precedent = bool(re.match(r'^대판\s+1[89]', stripped) or
                           re.match(r'^\[\[', stripped))

        if is_precedent:
            corrected = correct_precedent_line(stripped)
            if corrected.strip():
                # 여러 줄로 분리된 경우 처리
                for subline in corrected.split('\n'):
                    if subline.strip():
                        result.append(subline)
        else:
            # 판례색인에서 페이지번호 줄 (예: "158, 203, 207") 유지
            if re.match(r'^[\d,\s\.]+$', stripped) and len(stripped) > 2:
                # 끝 쉼표 보정
                clean = re.sub(r'[m®§]\s*$', ',', stripped)
                result.append(clean)
            elif re.match(r'^\d+ \| 판례색인', stripped):
                result.append(stripped)
            else:
                result.append(line)

    return '\n'.join(result)


def correct_precedent_line(line):
    """판례 항목 줄 교정."""
    # 연도 OCR 오류
    line = line.replace('19呂7', '1987')
    line = line.replace('19으7', '1987')
    line = line.replace('199U', '1991')
    line = line.replace('19913', '1991.3')

    # 197. → 1987. (0이 누락된 연도 오류)
    line = re.sub(r'\b197\.(\d+\.\d+\.)', r'1987.\g<1>', line)

    # 판례번호 내 OCR 특수문자
    # 패턴: 숫자다(카?)특수문자숫자
    line = re.sub(r"(\d+다[가-힣]*)['\`](\d+)", r'\g<1>\g<2>', line)
    # &숫자다 → 8숫자다 (& → 8 오인식)
    line = re.sub(r'&(\d)다', r'8\g<1>다', line)
    # 콜론 삽입 오류: 83다카:116 → 83다카116
    line = re.sub(r'(\d+다[가-힣]*):(\d+)', r'\g<1>\g<2>', line)
    # 81다크W → 81다카(W는 OCR 오인식, 삭제)
    line = re.sub(r'(\d+다)크(\w)', r'\g<1>카', line)
    # 82다카= → 제거 (불완전 항목)
    line = re.sub(r'(\d+다[가-힣]*)=\s*$', '', line)
    # 82다카* → 제거
    line = re.sub(r'(\d+다[가-힣]*)\*\s*$', '', line)
    # 87다카6M → 87다카6 (말미 알파벳 제거)
    line = re.sub(r'(\d+다[가-힣]+\d+)[A-Za-z]\s*$', r'\g<1>', line)
    # »4다카石 같은 완전 깨진 항목: »로 시작하면 제거
    if re.match(r'^»', line.strip()):
        return ''
    # 연결된 두 판례 분리: "[[81다533]]대판" → "[[81다533]]\n대판"
    line = re.sub(r'(\]\])\s*대판\s', r'\g<1>\n대판 ', line)
    # 이대판 → \n대판
    line = re.sub(r'이대판\s', r'\n대판 ', line)
    # 숫자+한글(번호뒤 한글)대판 형식 분리: "71 대판" → "71\n대판"
    line = re.sub(r'(\d+)\s+(대판\s+\d{4})', r'\g<1>\n\g<2>', line)
    # 84다카'188 → 84다카188
    line = re.sub(r'다키\'', '다카', line)
    # 특수 OCR 문자 정리: ■ → (제거)
    line = line.replace('■', '')
    line = line.replace('▲', '')
    # 줄 끝 m → , 변환 (444m → 444,)
    line = re.sub(r'(\d+)m\s*$', r'\g<1>,', line)
    # 스페이스 정리
    line = re.sub(r'\s+', ' ', line).rstrip()

    return line


# ──────────────────────────────────────────────
# 메인 처리
# ──────────────────────────────────────────────

def process_chunk(src_path, dst_path, filename):
    with open(src_path, encoding='utf-8') as f:
        text = f.read()

    # 파일 유형에 따른 교정
    if '판례색인' in filename:
        corrected = correct_precedent_index(text)
        corrected = correct_ocr(corrected, filename)
    else:
        corrected = correct_ocr(text, filename)

    ensure_dir(dst_path)
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.write(corrected)

    return True


def main():
    chunks = load_chunk_list()
    done = 0
    skipped = 0
    failed = 0

    for c in chunks:
        src_path, dst_path = get_paths(c)
        filename = os.path.basename(src_path)

        if os.path.exists(dst_path):
            skipped += 1
            continue

        if not os.path.exists(src_path):
            print(f'[MISSING] {src_path}', flush=True)
            failed += 1
            continue

        try:
            process_chunk(src_path, dst_path, filename)
            done += 1
            print(f'[OK] {filename}', flush=True)
        except Exception as e:
            print(f'[ERR] {filename}: {e}', flush=True)
            failed += 1

    print(f'\n처리완료: {done}개 | 건너뜀(기존): {skipped}개 | 실패: {failed}개', flush=True)


if __name__ == '__main__':
    main()
