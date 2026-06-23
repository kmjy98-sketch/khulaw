# -*- coding: utf-8 -*-
"""
쟁점노트류 OCR 원문을 '논점 단위'로 분할 + 백링크만 추가 (요약/정리 없음).
원문보존형 위키: 원문 복제 → 논점 분할 → [[백링크]] 추가.

사용:
  python wiki_원문분할.py --dry  쟁점노트_재산법          # 경계(논점) 목록만 출력
  python wiki_원문분할.py --write 쟁점노트_재산법          # 파일 생성(sync/위키/원문/{책}/)
  python wiki_원문분할.py --write 쟁점노트_재산법 --only 채권자취소  # 제목에 키워드 포함된 1건만

규칙(CLAUDE.md):
- #1/#13 원문 그대로(요약·교정 금지), #35 백링크(판례/조문, 표·각주 안 제외), #16 삭제금지(쓰기만).
"""
import os, re, glob, sys, io, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OCR_DIR  = vp("outputs", "01_ocr_llamaparse")
OUT_BASE = vp("sync", "위키", "원문")

# 책 → 과목 (쟁점노트류 정리서)
SUBJ = {
    '쟁점노트_재산법': '민법', '논점민소': '민사소송법', '헌법핵심정리300': '헌법',
    '반반형법': '형법', '김기용_형총교안': '형법', 'compact형총OX': '형법',
}

# 책별 추가 제외 패턴(세부 항목을 H1로 승격한 OCR 노이즈 → 상위 논점 본문에 포함시킴)
# 주의: '02 주제'(쟁점노트=논점, 유지) vs '017 항목'(헌법=세부, 제외)처럼 같은 패턴이 책마다 반대라 책별로 둠
BOOK_RULES = {
    '헌법핵심정리300': [r'^\**\s*Theme\b', r'^[▶►]', r'^쟁점\s*\d', r'^\d{2,4}\s+\S'],
}
# 책별 'keep_only': 이 정규식에 맞는 H1만 논점으로 인정(나머지는 상위 논점 본문에 포함)
BOOK_KEEP = {
    '헌법핵심정리300': r'^제\s*\d+\s*장',   # 본문은 제N장 단위(영문 Chapter/PART 목차·표준판례는 제외)
    '반반형법': r'^제\s*\d+\s*장',
    '김기용_형총교안': r'^제\s*\d+\s*장',
    'compact형총OX': r'^제\s*\d+\s*장',
}
STUB_MIN = 120   # 본문 글자수 이 미만이면 목차 stub으로 보고 파일 생성 안 함

# ---- 1. 책 로드(페이지 순 결합, frontmatter 제거) ----
def load_book(book):
    files = glob.glob(os.path.join(OCR_DIR, f"{book}_llamaparse_p*.md"))
    if not files:
        files = glob.glob(os.path.join(OCR_DIR, f"{book}_p*.md"))
    def startp(f):
        m = re.search(r'_p0*(\d+)-', os.path.basename(f))
        return int(m.group(1)) if m else 0
    files.sort(key=startp)
    body = []
    for f in files:
        txt = open(f, encoding='utf-8').read()
        txt = re.sub(r'^---\n.*?\n---\n', '', txt, count=1, flags=re.S)  # frontmatter 제거
        body.append(txt)
    return files, "\n".join(body)

# ---- 2. 논점 경계 검출(H1 헤더 중 논점성만) ----
def jaeom_title(raw, book='', keep_ov=None, drop_ov=None):
    t = re.sub(r'^(Il|II)?\s*(logo|icon)\s*', '', raw.strip(), flags=re.I).strip()
    t = re.sub(r'\s*<sup>.*?</sup>\s*', '', t).strip()
    if len(t) < 2: return None
    # 제외: 청크 반복 헤더·표지·목차(CONTENTS·말미 페이지번호 라인)
    if 'llamaparse' in t or '미교정' in t: return None
    if t in ('CONTENTS', 'Contents', 'PreFace', 'Preface', '논점', '민사', '소송법',
             '본서의 차례', '차례', '목차'): return None
    if re.match(r'^제.*\s\d{1,4}\s*$', t): return None
    if re.match(r'^PART\s*\d*\s*$', t, re.I): return None            # 영문 편 표제(주제 없는 것)
    if '핵심정리' in t and '300' in t: return None                    # 책표지 제목
    # 제외: OCR 라틴 노이즈 접두(w/m/in/DI/IU/vn) · (N) 소절 · [TIP/[유형별 박스
    if re.match(r'^[a-zA-Z]{1,3}\s+\S', t): return None
    if re.match(r'^\(\d+\)', t): return None
    if t.startswith('['): return None
    # 제외: 편/책표지/소절(숫자.·로마·가나·N))
    if re.match(r'^제\s*\d+\s*편', t): return None
    if '민사법 쟁점노트' in t or re.match(r'^\d{4}\b', t): return None
    if re.match(r'^\d+\.\s', t): return None
    if re.match(r'^[IVXⅠ-Ⅻⅰ-ⅹ]+(\s|$)', t): return None
    if re.match(r'^[가-힣]\.\s', t): return None
    if re.match(r'^\d+\)\s', t): return None
    if re.match(r'^[\d\s.]+$', t): return None
    for pat in (drop_ov if drop_ov is not None else BOOK_RULES.get(book, [])):
        if re.match(pat, t): return None
    keep = keep_ov if keep_ov is not None else BOOK_KEEP.get(book)
    if keep and not re.match(keep, t): return None
    return t

def split_book(book, keep_ov=None, drop_ov=None, h2=False, marker=None):
    files, text = load_book(book)
    lines = text.split('\n')
    cur_page, in_table = None, False
    mk = re.compile(marker) if marker else None
    segs = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        pm = re.match(r'<!--\s*p\.?\s*(\d+)\s*-->', s)
        if pm:
            cur_page = int(pm.group(1)); continue
        if '<table' in s: in_table = True
        if '</table>' in s: in_table = False
        if in_table: continue
        if mk:                       # 마커 모드: 본문 텍스트 라인을 경계로(헤더 레벨 무관, OCR이 평문화한 '[사례 N]' 등)
            if mk.match(s):
                t = re.sub(r'\s+', ' ', re.sub(r'\*+', '', s)).strip()[:80]
                if t:
                    segs.append({'title': t, 'page': cur_page, 'idx': i})
            continue
        hm = re.match(r'^#{1,2}\s+(.+)$' if h2 else r'^#\s+(.+)$', ln)
        if hm:
            t = jaeom_title(hm.group(1), book, keep_ov, drop_ov)
            if t:
                segs.append({'title': t, 'page': cur_page, 'idx': i})
    return files, lines, segs

# ---- 3. 백링크(#35): 표/각주 밖에서만 판례·조문 ----
# 사건번호 본체(민사 다/형사 도/행정 두/… + 헌법 YYYY헌X)
NUMP = (r'\d{2,4}(?:다|도|두|마|모|므|르|허|카|초|그|재|추|수)\d+'
        r'|\d{4}헌(?:마|바|가|라|나|아|사)\d+')
CASE = re.compile(r'(대판|대결|대법원|헌재|헌법재판소)\s*(?:\(全合\)|\(전합\))?\s*'
                  r'(\d{2,4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*,?\s*(' + NUMP + r')')
BARE = re.compile(r'(?<!\[)(?<!, )(?<![\d.])(' + NUMP + r')(?!\])')   # 무날짜 사건번호(이중 wrap 방지)
STAT = re.compile(r'(?<!\[\[)제\s*(\d{2,4})\s*조(?:의\s*\d+)?(?:\s*제\s*\d+\s*항)?')

def add_links(block):
    out, in_table = [], False
    for ln in block.split('\n'):
        s = ln.strip()
        if '<table' in s: in_table = True
        if in_table or s.startswith('[^') or s.startswith('|') or s.startswith('```'):
            out.append(ln)
            if '</table>' in s: in_table = False
            continue
        ln = CASE.sub(lambda m: f"[[{m.group(1)} {m.group(2)}.{m.group(3)}.{m.group(4)}, {m.group(5)}]]", ln)
        ln = BARE.sub(lambda m: f"[[{m.group(1)}]]", ln)
        ln = STAT.sub(lambda m: f"[[§{m.group(1)}]]" if int(m.group(1)) >= 10 else m.group(0), ln)
        out.append(ln)
    return '\n'.join(out)

# ---- 4. 파일명 슬러그 ----
def slug(t):
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'논점\s*\d+\s*', '', t)
    t = re.sub(r'[\\/:*?"<>|\[\]]', '', t).strip()
    t = re.sub(r'\s+', '_', t)
    return t[:50] or 'untitled'

def run(book, write, only, subj_ov=None, keep_ov=None, drop_ov=None, h2=False, marker=None):
    files, lines, segs = split_book(book, keep_ov, drop_ov, h2, marker)
    print(f"# {book} | OCR {len(files)}청크 | 검출 논점 {len(segs)}개")
    for k, sg in enumerate(segs):
        end = segs[k+1]['idx'] if k+1 < len(segs) else len(lines)
        npg = sum(1 for j in range(sg['idx'], end) if re.match(r'<!--\s*p\.', lines[j].strip()))
        sg['end'], sg['lines'] = end, npg
    if not write:
        for k, sg in enumerate(segs):
            print(f"{k+1:3} p.{str(sg['page']):>4} (~{sg['lines']}p)  {sg['title']}")
        return
    outdir = os.path.join(OUT_BASE, book)
    os.makedirs(outdir, exist_ok=True)
    n = skipped = 0
    for k, sg in enumerate(segs):
        if only and only not in sg['title']: continue
        body = '\n'.join(lines[sg['idx']:sg['end']]).strip()
        content = re.sub(r'(?m)^#.*$|<!--.*?-->|\s+', '', body)
        if len(content) < STUB_MIN:
            skipped += 1; continue
        body = add_links(body)
        endpg = segs[k+1]['page'] if k+1 < len(segs) and segs[k+1]['page'] else sg['page']
        fm = (f"---\ntype: 원문\n과목: {subj_ov or SUBJ.get(book,'민법')}\n주제: {sg['title']}\n"
              f"출처책: {book}\n포함_페이지: {sg['page']}-{endpg}\n"
              f"원천: {book}_llamaparse OCR (논점분할 {k+1}/{len(segs)})\n"
              f"가공: 원문 그대로 + 백링크만 (요약·교정 없음, 2026-06-16)\n---\n\n")
        path = os.path.join(outdir, f"{k+1:03d}_{slug(sg['title'])}.md")
        open(path, 'w', encoding='utf-8').write(fm + body + '\n')
        n += 1
        print(f"  쓰기: {os.path.basename(path)}  (p.{sg['page']}-{endpg})")
    print(f"# 생성 {n}개 (stub 제외 {skipped}) → {outdir}")

def make_index(book):
    d = os.path.join(OUT_BASE, book)
    files = sorted(f for f in glob.glob(os.path.join(d, '*.md'))
                   if os.path.basename(f) != '_index.md')
    rows = []
    for f in files:
        txt = open(f, encoding='utf-8').read()
        sj = re.search(r'^주제:\s*(.+)$', txt, re.M)
        pg = re.search(r'^포함_페이지:\s*(.+)$', txt, re.M)
        nm = os.path.basename(f)[:-3]
        rows.append((nm, sj.group(1).strip() if sj else nm, pg.group(1).strip() if pg else ''))
    out = [f"# {book} 원문 논점 색인", "",
           f"> 원문보존형(원문 복제 + 백링크, 요약 없음). 총 {len(rows)}논점. 생성 2026-06-16.", ""]
    out += [f"{i+1}. [[{nm}|{sj}]] (p.{pg})" for i, (nm, sj, pg) in enumerate(rows)]
    open(os.path.join(d, '_index.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print(f"색인: {len(rows)}논점 → {d}\\_index.md")

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('book', nargs='?')
    p.add_argument('--write', action='store_true')
    p.add_argument('--index', action='store_true')
    p.add_argument('--dry', action='store_true')
    p.add_argument('--only')
    p.add_argument('--subj')
    p.add_argument('--keep')                 # keep_only 정규식(이 패턴 H1만 논점)
    p.add_argument('--drop')                 # 제외 정규식, '||' 구분 다중
    p.add_argument('--config')               # JSON {book,subj,keep,drop,write,index,only,h2} (한글 CLI 인자 회피용)
    p.add_argument('--h2', action='store_true')   # H2(##)도 분할 경계로
    p.add_argument('--marker')                    # 본문 텍스트 라인 경계 정규식(평문 '[사례 N]' 등)
    args = p.parse_args()
    if args.config:                          # JSON 설정(ASCII 경로)에서 모든 옵션 로드
        c = json.load(open(args.config, encoding='utf-8-sig'))
        bk = c['book']
        if c.get('index'):
            make_index(bk)
        else:
            run(bk, c.get('write', True), c.get('only'), c.get('subj'), c.get('keep'), c.get('drop'), c.get('h2', False), c.get('marker'))
    elif args.index:
        make_index(args.book)
    else:
        drop_ov = args.drop.split('||') if args.drop else None
        run(args.book, args.write, args.only, args.subj, args.keep, drop_ov, args.h2, args.marker)
