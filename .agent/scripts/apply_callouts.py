"""
윤동환_민법의맥 1부 (164개 파일) 콜아웃 적용 스크립트
- [!판례]: 「...」(대판/대결/헌재 사건번호) 패턴
- [!조문]: **제N조**(제목) 형식 독립 단락
"""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')

BASE = r'H:\내 드라이브\sync\_교재원문\민법\윤동환_민법의맥'

# 대상 파일 목록
files = sorted([f for f in os.listdir(BASE) if not f.startswith('_') and f.endswith('.md')])
TARGET = files[:164]

# 조문 패턴: **제N조**(제목) 또는 **제N조** (제목)
ART_PATTERN = re.compile(
    r'^(\*\*제(\d+조(?:의\d+)?)\*\*\s*[\(（]([^)）]+)[\)）])\s*(.*)',
    re.DOTALL
)

# 단순 참조 패턴 (조문 콜아웃 미적용)
REF_PATTERNS = [
    r'^에 의하지', r'^에 의한다\b', r'^를 따르', r'^로 보아',
    r'^에 따라\b', r'^에 의하여\b', r'^도 마찬가지',
    r'^가 적용', r'^는 적용', r'^에 해당', r'^에 근거', r'^의 법리'
]

# 판례 패턴: 「...」(대판/대결/헌재...) 독립 단락
PREC_PATTERN = re.compile(
    r'^「[^」]+」\s*\((?:대판|대결|헌재)[^)]+\)'
)

def is_ref_only(rest):
    """단순 조문 참조(콜아웃 미적용)인지 판단"""
    if not rest.strip():
        return False  # 빈 경우는 다음 줄 본문 가능
    return any(re.match(p, rest.strip()) for p in REF_PATTERNS)

def extract_yaml_end(lines):
    """YAML frontmatter 끝 줄 인덱스 반환"""
    if not lines or lines[0].strip() != '---':
        return -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return i
    return -1

def keyword_from_article(title):
    """조문 제목에서 논점 키워드 추출"""
    # 괄호 내용을 그대로 사용
    return title.strip()

def apply_callouts(content, filename):
    """파일 내용에 콜아웃 적용"""
    lines = content.split('\n')
    result = []
    i = 0
    yaml_end = extract_yaml_end(lines)

    article_count = 0
    precedent_count = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # YAML frontmatter 그대로 유지
        if i <= yaml_end:
            result.append(line)
            i += 1
            continue

        # 이미 > 로 시작하는 줄 그대로 유지
        if line.startswith('>'):
            result.append(line)
            i += 1
            continue

        # 판례 패턴: 「...」(대판/대결/헌재...)
        if PREC_PATTERN.match(stripped):
            # 논점 키워드 추출 (사건번호 앞 내용 일부)
            m_prec = re.search(r'\((?:대판|대결|헌재)([^)]+)\)', stripped)
            case_no = m_prec.group(0)[1:-1] if m_prec else ''
            # 이미 콜아웃 아닌 경우만 적용
            result.append(f'> [!판례] 판례 — {case_no}')
            result.append(f'> {stripped}')
            precedent_count += 1
            i += 1
            continue

        # 조문 패턴: **제N조**(제목) ...
        m_art = ART_PATTERN.match(stripped)
        if m_art:
            art_header = m_art.group(1)  # **제N조**(제목) 부분
            art_no = m_art.group(2)      # N조
            art_title = m_art.group(3)   # 제목
            rest = m_art.group(4).strip() # 뒤 내용

            # 단순 참조 건너뜀
            if is_ref_only(rest):
                result.append(line)
                i += 1
                continue

            # 콜아웃 헤더
            callout_header = f'> [!조문] 제{art_no} ({art_title})'

            if rest:
                # 같은 줄에 본문이 있는 경우
                result.append(callout_header)
                # **제N조**(제목) 부분을 콜아웃 내용 첫 줄로
                result.append(f'> {art_header} {rest}'.rstrip())
                article_count += 1
                i += 1
            else:
                # 제목만 있는 경우: 다음 줄들이 본문 (- ① 형식)
                # 다음 줄 확인
                j = i + 1
                body_lines = []
                while j < len(lines):
                    nxt = lines[j]
                    nxt_stripped = nxt.strip()
                    # 리스트 형식 본문 (- ① ② ...)
                    if nxt_stripped.startswith('- ①') or nxt_stripped.startswith('- ②') or \
                       nxt_stripped.startswith('- ③') or nxt_stripped.startswith('- ④') or \
                       nxt_stripped.startswith('- ⑤'):
                        body_lines.append(nxt)
                        j += 1
                    elif body_lines and nxt_stripped.startswith('- ⑥') or \
                         (body_lines and nxt_stripped.startswith('- ')):
                        # 연속 리스트
                        body_lines.append(nxt)
                        j += 1
                    else:
                        break

                if body_lines:
                    result.append(callout_header)
                    result.append(f'> {art_header}')
                    for bl in body_lines:
                        result.append(f'> {bl.rstrip()}')
                    article_count += 1
                    i = j
                else:
                    # 본문 없음 → 그대로 유지
                    result.append(line)
                    i += 1
            continue

        # 기본: 그대로 유지
        result.append(line)
        i += 1

    return '\n'.join(result), article_count, precedent_count


def count_patterns(content):
    """처리 전후 패턴 카운트"""
    art_pattern = re.compile(r'^\*\*제\d+조(?:의\d+)?\*\*\s*[\(（]', re.MULTILINE)
    prec_pattern = re.compile(r'^「[^」]+」\s*\((?:대판|대결|헌재)', re.MULTILINE)
    already_art = content.count('> [!조문]')
    already_prec = content.count('> [!판례]')
    return len(art_pattern.findall(content)), len(prec_pattern.findall(content)), already_art, already_prec


# 실행
total_files = 0
total_articles = 0
total_precedents = 0
changed_files = 0

print("콜아웃 적용 시작...")
print(f"대상: {len(TARGET)}개 파일")
print()

for fn in TARGET:
    path = os.path.join(BASE, fn)
    with open(path, encoding='utf-8') as f:
        original = f.read()

    # 이미 처리된 파일 건너뜀
    if '> [!조문]' in original and '> [!판례]' in original:
        continue

    new_content, art_cnt, prec_cnt = apply_callouts(original, fn)

    if new_content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        changed_files += 1
        total_articles += art_cnt
        total_precedents += prec_cnt
        if art_cnt > 0 or prec_cnt > 0:
            print(f"[처리] {fn}: 조문 {art_cnt}개, 판례 {prec_cnt}개")

    total_files += 1

print()
print("=" * 60)
print(f"처리 완료")
print(f"  대상 파일: {len(TARGET)}개")
print(f"  변경된 파일: {changed_files}개")
print(f"  적용된 [!조문] 콜아웃: {total_articles}개")
print(f"  적용된 [!판례] 콜아웃: {total_precedents}개")
