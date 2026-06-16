#!/usr/bin/env python3
r"""LLM reflow 결과 포맷 수정 (사용자 피드백 반영).

처리 내용:
1. 대괄호 포함 헤딩 (`### [ㄱ]`) → `**[ㄱ]**` 볼드 (Obsidian 위키링크 오인 방지)
2. `## 제N편`, `## 제N장`, `### 제N절` 등 → 볼드 (헤딩 스팸 방지)
3. frontmatter `페이지:` 필드 → 단순 범위 형식 (prefix 제거, `68-84` 등)
4. `^제\d+조` 단독 줄 + 다음 본문 → Obsidian `> [!example]` 콜아웃 감쌈

idempotent: 이미 처리된 파일은 no-op
"""
import sys
import re
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브')
TEXTBOOK_ROOT = ROOT / 'sync' / '_교재원문'

FRONTMATTER_PAT = re.compile(r'^(---\n.*?\n---\n)(.*)$', re.DOTALL)

# 1. [단일 음운/한글] 헤딩 → 볼드
# e.g., `### [ㄱ]`, `### [ㅎ]`, `### [ㄱ] 조문` 등
BRACKET_HEADING_PAT = re.compile(
    r'^(#{1,6})\s+(\[[가-힣ㄱ-ㅎㅏ-ㅣ][가-힣ㄱ-ㅎㅏ-ㅣ\s]{0,10}\].*)$',
    re.MULTILINE
)

# 1-2. 본문 내 [판례], [판례 1], [판례해설] 등 대괄호 라벨 → 괄호로 변경
# Obsidian 위키링크 오인 방지. 볼드 감싼 경우도 처리
# 매치: [판례], [판례 1], **[판례 1]**, [판례해설], [판례연구], [판례평석], [비교판례] 등
WIKILINK_SAFE_LABELS = ('판례', '판시', '판결', '해설', '사례', '쟁점', '요지', '비교', '참고', '예', '요건', '사실관계', '문제', '답안')
_labels_pat = '|'.join(WIKILINK_SAFE_LABELS)
BRACKET_LABEL_PAT = re.compile(
    r'\[((?:' + _labels_pat + r')(?:\s*\d+)?(?:해설|연구|비교|요지|평석)?)\]'
)
# 추가 패턴: [비교판례], [판례평석] 등 2단어 조합
BRACKET_LABEL_COMBO_PAT = re.compile(
    r'\[((?:비교|판례)(?:판례|해설|연구|비교|요지|평석))\]'
)

# 범용 대괄호 라벨 (짧은 한글/영숫자, 독립 단어): [예비죄], [인과관계], [ㄱ], [12사법], [3회 기록형] 등
# 위키링크([[...]])와 callout([!...])는 제외
# 앞뒤 문맥 상관없이 매치: [내용] 형식
GENERIC_BRACKET_PAT = re.compile(
    r'(?<!\[)\[([^\[\]!][^\[\]]{0,30})\](?!\])'
)

# 1-3. HTML 주석 페이지 마커 완전 삭제
PAGE_COMMENT_PAT = re.compile(
    r'<!--\s*(?:page|페이지|p\.)[\s:]*\d+[^>]*-->\n?',
    re.IGNORECASE
)

# 1-4. 편·장 볼드 앞에 `---` 구분선 추가
# `**제N편 ...**`, `**제N장 ...**`
CHAPTER_BOLD_PAT = re.compile(
    r'(?<!\n---\n\n)^(\*\*제\s*\d+\s*(?:편|장)\b[^*]*\*\*)$',
    re.MULTILINE
)

# 2. `## 제N편`, `## 제N장`, `### 제N절`, `#### 제N조` (조는 예외 - 아래)
CHAPTER_HEADING_PAT = re.compile(
    r'^(#{1,6})\s+(제\s*\d+\s*(?:편|장|절)\b.*)$',
    re.MULTILINE
)

# 3. frontmatter 페이지 필드
PAGE_FIELD_PAT = re.compile(r'^(페이지:\s*)(.+)$', re.MULTILINE)
PAGE_RANGE_PAT = re.compile(r'(?:pp?\.?\s*)?(\d+)\s*[-~–—]\s*(\d+)')
SINGLE_PAGE_PAT = re.compile(r'(?:pp?\.?\s*)?(\d+)\s*$')

# 4. 조문 콜아웃 패턴
# `제N조` 또는 `제N조의N` 단독 줄 (선택적 제목 `(...)`)
ARTICLE_HEADER_PAT = re.compile(
    r'^(\*\*)?제\s*\d+\s*조(?:의\s*\d+)?\s*(?:\([^)]*\))?(?:\*\*)?\s*$'
)


def split_frontmatter(text: str) -> tuple[str, str]:
    m = FRONTMATTER_PAT.match(text)
    if m:
        return m.group(1), m.group(2)
    return '', text


def fix_bracket_headings(body: str) -> tuple[str, int]:
    """[ㄱ] 같은 대괄호 헤딩을 볼드로 변경."""
    count = [0]

    def replace(m):
        count[0] += 1
        return f'**{m.group(2)}**'

    new_body = BRACKET_HEADING_PAT.sub(replace, body)
    return new_body, count[0]


def fix_bracket_labels(body: str) -> tuple[str, int]:
    """본문 내 대괄호 라벨 제거 (Obsidian 위키링크 오인 방지).

    - `[판례]` → `판례`
    - `[판례 1]` → `판례 1`
    - `**[판례 1]**` → `**판례 1**`
    - `[예비죄]` → `예비죄`
    - `[ㄱ]` → `ㄱ` (후처리로 볼드)
    - `[12사법]` → `12사법`
    - `[도덕형이상학]` → `도덕형이상학`

    제외:
    - `[[wikilink]]` (이중 대괄호)
    - `[!callout]` (callout 지시자)
    """
    count = [0]

    def replace_to_paren(m):
        """[라벨] → (라벨) 소괄호 변환 (원책 표기 보존, 위키링크 오인 방지)."""
        count[0] += 1
        return '(' + m.group(1) + ')'

    # 1차: 안전 라벨 ([판례], [사례], [예] 등) → 소괄호 변환
    new_body = BRACKET_LABEL_PAT.sub(replace_to_paren, body)
    new_body = BRACKET_LABEL_COMBO_PAT.sub(replace_to_paren, new_body)
    # 2차: 범용 대괄호 — 비활성화 (2026-04-12)
    # 원책 표기 [법조경합], [쟁점], [요건] 등은 교재 고유 포맷이므로 무차별 변환 금지
    # GENERIC_BRACKET_PAT은 원책 표기 파괴가 위키링크 오인보다 심각하여 OFF
    # new_body = GENERIC_BRACKET_PAT.sub(replace_to_paren, new_body)
    return new_body, count[0]


def remove_page_comments(body: str) -> tuple[str, int]:
    """HTML 주석 페이지 마커 완전 삭제."""
    count = [0]

    def replace(m):
        count[0] += 1
        return ''

    new_body = PAGE_COMMENT_PAT.sub(replace, body)
    return new_body, count[0]


def add_chapter_separators(body: str) -> tuple[str, int]:
    """편·장 볼드 앞에 `---` 구분선 추가 (idempotent)."""
    count = [0]
    lines = body.split('\n')
    result = []
    chapter_pat = re.compile(r'^\*\*제\s*\d+\s*(?:편|장)\b[^*]*\*\*$')

    for i, line in enumerate(lines):
        if chapter_pat.match(line.strip()):
            # 이전 줄이 이미 `---`이면 skip
            prev_non_empty = None
            for j in range(len(result) - 1, -1, -1):
                if result[j].strip():
                    prev_non_empty = result[j].strip()
                    break
            if prev_non_empty != '---':
                # 빈 줄 + --- + 빈 줄 추가
                if result and result[-1].strip():
                    result.append('')
                result.append('---')
                result.append('')
                count[0] += 1
        result.append(line)

    return '\n'.join(result), count[0]


def fix_chapter_headings(body: str) -> tuple[str, int]:
    """## 제N편/장/절 → **제N편/장/절** 볼드 변경."""
    count = [0]

    def replace(m):
        count[0] += 1
        return f'**{m.group(2).strip()}**'

    new_body = CHAPTER_HEADING_PAT.sub(replace, body)
    return new_body, count[0]


def normalize_page_format(frontmatter: str) -> tuple[str, bool]:
    """frontmatter 페이지 필드를 단순 범위 형식으로 정규화 (prefix 제거, 패딩 없음)."""
    m = PAGE_FIELD_PAT.search(frontmatter)
    if not m:
        return frontmatter, False

    val = m.group(2).strip()

    # 범위 형식 매칭
    rm = PAGE_RANGE_PAT.search(val)
    if rm:
        start = int(rm.group(1))
        end = int(rm.group(2))
        new_val = f'{start}-{end}'
    else:
        # 단일 페이지
        sm = SINGLE_PAGE_PAT.search(val)
        if sm:
            page = int(sm.group(1))
            new_val = f'{page}'
        else:
            return frontmatter, False

    if new_val == val:
        return frontmatter, False

    new_frontmatter = frontmatter[:m.start(2)] + new_val + frontmatter[m.end(2):]
    return new_frontmatter, True


def wrap_articles_as_callouts(body: str) -> tuple[str, int]:
    """`제N조` 단독 줄 + 본문 행을 Obsidian `> [!example]` callout으로 감쌈.

    감지 규칙:
    - 독립 줄이 `제N조` 또는 `제N조 (제목)` 또는 `**제N조**` 형태
    - 다음 1~5줄이 non-empty content
    - 본문이 ①②③ 원 숫자로 시작하거나 문장(> 20자 + 종결어미)으로 판단
    - 이미 `>` callout 안에 있으면 skip
    """
    lines = body.split('\n')
    result = []
    count = [0]
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # 이미 callout이면 그대로
        if stripped.startswith('>'):
            result.append(line)
            i += 1
            continue

        m = ARTICLE_HEADER_PAT.match(stripped)
        if m:
            # 다음 행이 본문인지 확인
            j = i + 1
            body_lines = []
            max_lookahead = 10
            while j < len(lines) and j - i < max_lookahead:
                nl = lines[j].strip()
                if not nl:
                    # 빈 줄 2개 연속이면 종료
                    if j + 1 < len(lines) and not lines[j + 1].strip():
                        break
                    body_lines.append(lines[j])
                    j += 1
                    continue
                # 다음 섹션 경계 만나면 종료
                if nl.startswith('#') or nl.startswith('---'):
                    break
                # 새 조문 시작이면 종료
                if ARTICLE_HEADER_PAT.match(nl):
                    break
                # 본문
                body_lines.append(lines[j])
                j += 1
                # 최소 1줄 이상 + 종결어미 있으면 충분
                if len(body_lines) >= 1 and any(
                    kw in nl for kw in ('①', '②', '③', '④', '⑤', '다.', '한다.', '된다.', '있다.', '없다.')
                ):
                    # 종결어미 찾으면 더 보지 않고 현재까지만
                    pass

            # 본문이 있으면 callout으로 감쌈
            if body_lines and any(line.strip() for line in body_lines):
                count[0] += 1
                # 제목 부분 추출 (볼드 표시 제거)
                title = stripped.replace('**', '').strip()
                result.append(f'> [!example] {title}')
                for bl in body_lines:
                    if bl.strip():
                        result.append(f'> {bl.strip()}')
                    else:
                        result.append('>')
                i = j
                continue

        result.append(line)
        i += 1

    return '\n'.join(result), count[0]


def process_file(path: Path, dry_run: bool = False, skip_article: bool = False) -> dict:
    orig = path.read_text(encoding='utf-8')
    frontmatter, body = split_frontmatter(orig)

    # 1. frontmatter 페이지 정규화
    new_frontmatter, page_changed = normalize_page_format(frontmatter)

    # 2. 본문 헤딩 수정
    new_body, bracket_count = fix_bracket_headings(body)
    new_body, chapter_count = fix_chapter_headings(new_body)
    new_body, label_count = fix_bracket_labels(new_body)

    # 2-1. 페이지 주석 삭제
    new_body, page_comment_count = remove_page_comments(new_body)

    # 2-2. 편·장 구분선 추가
    new_body, separator_count = add_chapter_separators(new_body)

    # 3. 조문 콜아웃 (LLM reflow된 파일에만 적용)
    article_count = 0
    if not skip_article:
        new_body, article_count = wrap_articles_as_callouts(new_body)

    new_text = new_frontmatter + new_body
    changed = new_text != orig

    if changed and not dry_run:
        path.write_text(new_text, encoding='utf-8')

    return {
        'path': str(path),
        'page_changed': page_changed,
        'bracket_headings': bracket_count,
        'chapter_headings': chapter_count,
        'bracket_labels': label_count,
        'page_comments': page_comment_count,
        'chapter_separators': separator_count,
        'article_callouts': article_count,
        'changed': changed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sample', type=int, default=0)
    parser.add_argument('--skip-article', action='store_true',
                        help='조문 콜아웃 감쌈 건너뛰기 (frontmatter+헤딩만)')
    parser.add_argument('--page-only', action='store_true',
                        help='frontmatter 페이지 정규화만 (본문 건드리지 않음)')
    parser.add_argument('paths', nargs='*')
    args = parser.parse_args()

    if args.paths:
        targets = [Path(p).resolve() for p in args.paths]
    else:
        targets = []
        for f in TEXTBOOK_ROOT.rglob('*.md'):
            if '_trash' in f.parts:
                continue
            if f.name == '_교재목차.md':
                continue
            targets.append(f)

    if args.sample > 0:
        targets = targets[:args.sample]

    print(f'대상: {len(targets)}개 파일')
    print(f'모드: {"DRY-RUN" if args.dry_run else "EXECUTE"}')
    print()

    total = 0
    changed = 0
    page_changed = 0
    bracket_total = 0
    chapter_total = 0
    label_total = 0
    page_comment_total = 0
    separator_total = 0
    article_total = 0
    errors = []

    for f in targets:
        try:
            if args.page_only:
                # frontmatter만
                orig = f.read_text(encoding='utf-8')
                frontmatter, body = split_frontmatter(orig)
                new_fm, page_ch = normalize_page_format(frontmatter)
                if page_ch and not args.dry_run:
                    f.write_text(new_fm + body, encoding='utf-8')
                total += 1
                if page_ch:
                    page_changed += 1
                    changed += 1
                continue

            stats = process_file(f, dry_run=args.dry_run, skip_article=args.skip_article)
            total += 1
            if stats['changed']:
                changed += 1
            if stats['page_changed']:
                page_changed += 1
            bracket_total += stats['bracket_headings']
            chapter_total += stats['chapter_headings']
            label_total += stats['bracket_labels']
            page_comment_total += stats['page_comments']
            separator_total += stats['chapter_separators']
            article_total += stats['article_callouts']
        except Exception as e:
            errors.append((f, str(e)))

    print(f'=== 요약 ===')
    print(f'  처리: {total}')
    print(f'  변경: {changed}')
    print(f'  페이지 정규화: {page_changed}')
    if not args.page_only:
        print(f'  대괄호 헤딩 볼드 변환: {bracket_total}')
        print(f'  제N편/장/절 볼드 변환: {chapter_total}')
        print(f'  대괄호 라벨 제거: {label_total}')
        print(f'  페이지 주석 삭제: {page_comment_total}')
        print(f'  편·장 구분선 추가: {separator_total}')
        if not args.skip_article:
            print(f'  조문 콜아웃 감쌈: {article_total}')
    if errors:
        print(f'  에러: {len(errors)}')
        for f, e in errors[:5]:
            print(f'    {f}: {e}')


if __name__ == '__main__':
    main()
