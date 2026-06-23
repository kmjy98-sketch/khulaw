"""전 교재 교차참조 블록 삽입.

과목별로:
  - 타깃: 해당 과목의 모든 교재원문 파일 (강혜림_민법1 제외, 이미 완료)
  - 캐시: 같은 과목 내 다른 교재 파일
  - frontmatter tags 기반 자동 매칭, 실패 시 스킵
"""
import sys, os, re
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402
sys.stdout.reconfigure(encoding='utf-8')

ROOT = vp("sync", "_교재원문")
CASE_RE = re.compile(r'\b(\d{2,4}(?:다|도|헌가|헌마|헌바|헌라|형상|다카|마)\d+)\b')

def load_textbook_files(subject_dir):
    """과목 디렉터리 하위 모든 교재 파일 수집."""
    files = []
    for dpath, dnames, fnames in os.walk(subject_dir):
        if '_backup_phase1' in dpath.split(os.sep):
            continue
        for fn in fnames:
            if not fn.endswith('.md') or fn.startswith('_'):
                continue
            fp = os.path.join(dpath, fn)
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 교재 식별 (과목 하위 첫 폴더)
                parts = dpath.split(os.sep)
                idx = parts.index('_교재원문')
                textbook = parts[idx+2] if idx+2 < len(parts) else 'unknown'
                files.append({'path': fp, 'file': fn, 'content': content, 'textbook': textbook})
            except Exception:
                pass
    return files


TEXTBOOK_TOKENS = {'윤동환_민법의맥', '송영곤_쟁점노트', '송영곤_논점민법_보충',
                    '송영곤_논점민법_본책', '송영곤_사례연습2', '송영곤_사례', '송영곤_요건사실론',
                    '곽낙규_사례연습', '강혜림_민법1', '전경운_민법3', '박승수_민법기본사례',
                    '민법의해석', '김성돈_형법총론', '김기용_형법교안', '서보학_형법총론',
                    '홍형철_기본형법', '반반형법', '작은변사기_형법', '이인규_사례연습',
                    '강성민_헌법OX', '이진_헌법원리1', '법조윤리_한권탁_기출', '김준호_민법강의'}


def tags_from_fm(content):
    """frontmatter에서 tags + 포함_쟁점 + 주제 + 쟁점 + 서브책자 모두 추출."""
    fm = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm: return []
    fm_text = fm.group(1)
    all_tags = []
    # 1) tags: [..]
    tm = re.search(r'tags:\s*\[([^\]]+)\]', fm_text)
    if tm:
        all_tags.extend(t.strip().strip("'\"") for t in tm.group(1).split(','))
    # 2) 포함_쟁점: [..]
    pm = re.search(r'(?:포함_쟁점|쟁점|주제):\s*\[?([^\]\n]+)\]?', fm_text)
    if pm:
        # 콤마로 분리
        vals = pm.group(1).strip()
        all_tags.extend(v.strip().strip("'\"") for v in re.split(r'[,，]', vals))
    # 3) 서브책자에서 힌트
    sm = re.search(r'서브책자:\s*([^\n]+)', fm_text)
    if sm:
        all_tags.extend(re.split(r'[\s,_]+', sm.group(1).strip()))
    meta = {'교재원문', '민법', '형법', '헌법', '선택법', '민사법', '형사법',
            '총론', '각론', '기출', '정리', '24_ocr_x', '32_ocr', '25', '26'}
    return list(dict.fromkeys(t for t in all_tags if t and t not in meta
                              and t not in TEXTBOOK_TOKENS
                              and len(t) >= 2
                              and not re.match(r'^\d+$', t)))


def keywords_from_body(content, limit=10):
    """본문 헤딩에서 쟁점 키워드 추출 (fm/파일명 둘 다 실패 시 fallback)."""
    kws = []
    # 헤딩 (##, ###) 텍스트 수집
    for m in re.finditer(r'^#{2,4}\s+(.+)$', content, re.MULTILINE):
        h = m.group(1).strip()
        # 번호 · 제목 분리
        h = re.sub(r'^[\[\(]?\s*[IVX]+\.?\s*|\d+\.\s*|\(\d+\)\s*', '', h)
        h = re.sub(r'[\[\]\(\)]', '', h).strip()
        if h and 2 <= len(h) <= 30:
            kws.append(h)
        if len(kws) >= limit:
            break
    # 중복 제거 + 과목 메타 제외
    skip = {'민법', '형법', '헌법', '총론', '각론', '개관', '서설', '목차'}
    return [k for k in dict.fromkeys(kws) if k not in skip]


def keywords_from_filename(filename):
    """파일명에서 쟁점 키워드 추출. `_` 구분자로 분할 후 교재·페이지 토큰 제외."""
    stem = filename.replace('.md', '')
    parts = re.split(r'[_\s]+', stem)
    # 페이지 표기 (p0001-0030 등), 교재명 토큰 제거
    skip_pat = re.compile(r'^(p?\d+[-~]?\d*|본\d+|각\d+|차\d+|회차|제\d+장|제\d+절|\d+편)$')
    textbook_tokens = {'윤동환', '민법의맥', '송영곤', '쟁점노트', '논점민법', '사례연습',
                       '사례', '요건사실론', '곽낙규', '박승수', '민법기본사례', '민법의해석',
                       '전경운', '김성돈', '김기용', '서보학', '홍형철', '반반형법', '이인규',
                       '작은변사기', '강성민', '헌법OX', '이진', '헌법원리1', '법조윤리', '한권탁',
                       '교재', '정리', '기출', '강혜림', '민법1', '김준호', '민법강의',
                       '형법교안', '형법총론', '기본형법'}
    kws = []
    for p in parts:
        if not p or len(p) < 2: continue
        if skip_pat.match(p): continue
        if p in textbook_tokens: continue
        # 과목명도 제외
        if p in {'민법', '형법', '헌법', '총론', '각론'}: continue
        kws.append(p)
    return kws


def expand_keywords(tags):
    kws = set()
    for t in tags:
        kws.add(t)
        for i in range(len(t)-1):
            for j in range(i+2, min(i+5, len(t)+1)):
                kws.add(t[i:j])
    return [k for k in kws if len(k) >= 2]


def score(oc, target_textbook, kws):
    if oc['textbook'] == target_textbook:
        return (0, 0)  # 같은 교재 제외
    fs = sum(3 for k in kws if k in oc['file'] and len(k) >= 3)
    cs = sum(oc['content'].count(k) for k in kws if len(k) >= 3)
    return (fs, cs)


def nearby_cases(text, kws, window=400):
    ctx = Counter()
    for kw in kws:
        if len(kw) < 3:
            continue
        for km in re.finditer(re.escape(kw), text):
            s, e = max(0, km.start()-window), min(len(text), km.end()+window)
            for m in CASE_RE.finditer(text[s:e]):
                ctx[m.group(1)] += 1
    return ctx.most_common(10)


def build_block(tags, scored, top_cases):
    lines = [
        "\n\n---\n\n",
        "<!-- 교차참조 블록: OCR 손상 보완용. 과목 내 타 교재 매칭. 2026-04-22 -->\n",
        "## 📚 교차참조: 다른 교재 동일 쟁점 판례\n\n",
        f"> 쟁점: `{', '.join(tags[:5])}`. 본문 괄호 안 판례 식별자가 OCR 손상 시 아래를 참조.\n\n",
    ]
    if top_cases:
        lines.append("### 🔑 쟁점 근접 판례 (다른 교재 컨텍스트 기반 빈도 순)\n\n")
        for c, n in top_cases:
            lines.append(f"- [[{c}]] — 타 교재 근접 출현 {n}회\n")
        lines.append("\n")
    if scored:
        lines.append("### 📖 관련 교재 파일\n\n")
        for r in scored[:5]:
            stem = r['file'].replace('.md', '')
            lines.append(f"- [[{stem}]] — {r['textbook']}\n")
    return "".join(lines)


def process_subject(subject_name):
    subject_dir = os.path.join(ROOT, subject_name)
    if not os.path.exists(subject_dir):
        print(f"  {subject_name} 디렉터리 없음, 스킵")
        return 0, 0, 0
    print(f"\n=== {subject_name} ===")
    files = load_textbook_files(subject_dir)
    print(f"  총 {len(files)}개 파일")

    processed = 0
    skipped_block = 0
    skipped_no_tag = 0
    no_match = 0

    for t in files:
        # 강혜림_민법1 (김준호) 이미 완료된 파일 스킵
        if '교차참조 블록: OCR 손상' in t['content']:
            skipped_block += 1
            continue
        tags = tags_from_fm(t['content'])
        # tags가 없거나 비어있으면 파일명 → 본문 헤딩 순서로 fallback
        if not tags:
            tags = keywords_from_filename(t['file'])
        if not tags:
            tags = keywords_from_body(t['content'])
        if not tags:
            skipped_no_tag += 1
            continue
        kws = expand_keywords(tags)
        # 매칭
        scored = []
        for oc in files:
            fs, cs = score(oc, t['textbook'], kws)
            if fs > 0 or cs >= 15:
                scored.append({'path': oc['path'], 'file': oc['file'],
                              'content': oc['content'], 'textbook': oc['textbook'],
                              'fs': fs, 'cs': cs})
        scored.sort(key=lambda x: -(x['fs']*10 + x['cs']))
        scored = scored[:5]
        if not scored:
            no_match += 1
            continue

        # 쟁점 근접 판례
        global_cases = Counter()
        for r in scored:
            for c, v in nearby_cases(r['content'], tags):
                global_cases[c] += v
        top_cases = global_cases.most_common(10)
        if not top_cases:
            no_match += 1
            continue

        block = build_block(tags, scored, top_cases)
        new_content = t['content'].rstrip() + block
        try:
            with open(t['path'], 'w', encoding='utf-8') as f:
                f.write(new_content)
            processed += 1
        except Exception as e:
            print(f"  쓰기 실패 {t['file']}: {e}")

    print(f"  처리: {processed} / 이미완료: {skipped_block} / 태그없음: {skipped_no_tag} / 매칭없음: {no_match}")
    return processed, skipped_no_tag, no_match


if __name__ == '__main__':
    subjects = ['민법', '형법', '헌법', '선택법']
    total_processed = 0
    total_no_match = 0
    for s in subjects:
        p, _, nm = process_subject(s)
        total_processed += p
        total_no_match += nm
    print(f"\n=== 전체 완료 ===")
    print(f"  신규 블록 삽입: {total_processed}")
    print(f"  매칭 실패 (차후 수동 맵): {total_no_match}")
