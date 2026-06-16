"""
legal_regex.py — 법학 텍스트 OCR 가드레일 정규식.

anchor 라인 식별: 조문번호·사건번호·한자는 LLM 교정 대상에서 제외.
"""
import re

# 조문번호: 제X조, §XX(10 이상)
LAW_ARTICLE = re.compile(r'제\d+조(?:의\d+)?|§\d{2,}')

# 대법원 판례: 대판 YYYY.M.DD, 사건번호 YYdaXXXX 등
SUPREME_COURT = re.compile(
    r'대판\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}'
    r'|대법원\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}'
    r'|\b\d{2,4}\s*다\s*[가-힣]{0,5}\d{1,8}\b'
    r'|\b\d{2,4}\s*[가-힣]{1,4}\s*\d{1,8}\b'
)

# 헌법재판소: 헌재 YYYY.M.DD, YYYY헌마XXXX 등
CONSTITUTIONAL = re.compile(
    r'헌재\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}'
    r'|\d{4}\s*헌\s*[마바사아자]\s*\d{1,5}'
)

# 한자 블록 (CJK Unified Ideographs)
HANJA_BLOCK = re.compile(r'[一-鿿㐀-䶿豈-﫿]+')

# 사건번호 화이트리스트 패턴 (오탐 방지)
CASE_CODE_WHITELIST = re.compile(
    r'\d{2,4}(?:다|카|노|고|합|단|마|바|사|아|자|차|타|파|하)[가-힣]{0,3}\d{1,8}'
)

_ALL_ANCHORS = [LAW_ARTICLE, SUPREME_COURT, CONSTITUTIONAL, HANJA_BLOCK, CASE_CODE_WHITELIST]


def is_anchor_line(text: str) -> bool:
    """텍스트에 법적 식별자(조문·사건번호·한자)가 포함되면 True 반환."""
    return any(p.search(text) for p in _ALL_ANCHORS)


def extract_law_articles(text: str) -> list:
    return [m.group() for m in LAW_ARTICLE.finditer(text)]


def extract_case_numbers(text: str) -> list:
    results = []
    for p in (SUPREME_COURT, CONSTITUTIONAL, CASE_CODE_WHITELIST):
        results.extend(m.group().strip() for m in p.finditer(text))
    return list(dict.fromkeys(results))


def has_hanja(text: str) -> bool:
    return bool(HANJA_BLOCK.search(text))


def split_into_chunks(text: str, max_lines: int = 12,
                       overlap_tokens: int = 50,
                       prefer_paragraph_boundary: bool = True) -> list:
    """
    텍스트를 청크로 분할. 청크 경계는 단락 경계(빈 줄/헤딩) 우선.
    overlap_tokens 만큼 이전 청크의 끝과 겹쳐서 문맥 연속성 보장.

    반환: [{"lines": [...], "start_line": int, "end_line": int}]
    """
    lines = text.splitlines()
    if not lines:
        return []

    def _token_count(line_list):
        return sum(len(l.split()) for l in line_list)

    def _is_boundary(line):
        stripped = line.strip()
        return stripped == "" or stripped.startswith("#")

    chunks = []
    i = 0
    overlap_buf = []

    while i < len(lines):
        chunk_lines = list(overlap_buf)
        start = i

        while i < len(lines) and len(chunk_lines) < max_lines:
            chunk_lines.append(lines[i])
            i += 1

        # 단락 경계 우선: 중간에서 끊기면 다음 단락 경계까지 확장
        if prefer_paragraph_boundary and i < len(lines):
            while i < len(lines) and not _is_boundary(lines[i]):
                chunk_lines.append(lines[i])
                i += 1

        end = start + len(chunk_lines) - len(overlap_buf)
        chunks.append({"lines": chunk_lines, "start_line": start, "end_line": end - 1})

        # 오버랩 버퍼: 마지막 overlap_tokens 토큰에 해당하는 라인
        rev = []
        tok = 0
        for l in reversed(chunk_lines):
            tok += len(l.split())
            rev.append(l)
            if tok >= overlap_tokens:
                break
        overlap_buf = list(reversed(rev))

    return chunks
