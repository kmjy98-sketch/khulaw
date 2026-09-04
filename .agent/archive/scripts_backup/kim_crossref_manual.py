"""김준호 교재 매칭 실패 19개 파일에 대한 LLM 기반 수동 쟁점 매핑."""
import sys, os, re
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

KIM_ROOT = r"H:\내 드라이브\sync\_교재원문\민법\강혜림_민법1"

MANUAL_MAP = {
    "권리의분류_지배권_김준호_민법강의.md":
        ["지배권", "청구권", "형성권", "항변권", "인격권", "재산권",
         "상대권", "절대권", "권리분류", "권리의분류", "지배", "청구", "형성"],
    "금전_물건_김준호_민법강의.md":
        ["금전", "물건", "동산", "부동산", "주물", "종물", "원물", "과실",
         "특정물", "불특정물", "제98조", "제99조", "제100조", "제101조", "제102조",
         "소비물", "대체물", "권리객체"],
    "단기임대차_갱신_김준호_민법강의.md":
        ["단기임대차", "임대차", "갱신", "제619조", "제639조", "묵시의 갱신",
         "묵시갱신", "법정갱신", "차임", "해지통고", "존속기간"],
    "담보물권_순위_김준호_민법강의.md":
        ["담보물권", "저당권", "질권", "유치권", "순위", "우선변제",
         "부종성", "수반성", "불가분성", "물상대위", "피담보채권"],
    "동물점유자책임_김준호_민법강의.md":
        ["동물점유자", "제759조", "불법행위", "공작물책임", "제758조",
         "점유자", "보관자", "위험책임", "특수불법행위"],
    "물권법서설_재수록_김준호_민법강의.md":
        ["물권법", "물권", "물권법정주의", "제185조", "관습법상", "물권의종류",
         "물권행위", "공시", "공신", "물권변동"],
    "물권법총론_물권의의의_김준호_민법강의.md":
        ["물권", "물권법", "물권법정주의", "제185조", "관습법상의", "물권적청구권",
         "배타성", "대세효", "우선적효력", "물권의본질"],
    "법인제도서설_김준호_민법강의.md":
        ["법인", "사단법인", "재단법인", "비법인사단", "권리능력",
         "제31조", "제32조", "제33조", "제34조", "정관", "이사",
         "대표기관", "법인실체설"],
    "변제_특정물인도채무_김준호_민법강의.md":
        ["변제", "특정물인도", "선관주의", "제374조", "제460조", "제462조",
         "변제충당", "변제공탁", "대물변제", "변제자대위", "채무이행"],
    "사원권_공익권_자익권_김준호_민법강의.md":
        ["사원권", "공익권", "자익권", "사단법인", "사원총회",
         "결의권", "이익배당", "잔여재산분배"],
    "유실물습득_김준호_민법강의.md":
        ["유실물", "습득", "무주물선점", "제252조", "제253조", "제254조",
         "공고", "경찰서", "보상금", "유실물법"],
    "임치_무상편무계약_김준호_민법강의.md":
        ["임치", "무상계약", "편무계약", "제693조", "제694조", "제695조",
         "수치인", "보관의무", "임치물", "소비임치", "혼장임치"],
    "증여_부담부증여_김준호_민법강의.md":
        ["증여", "부담부증여", "제554조", "제555조", "제556조", "제561조",
         "증여의사", "서면증여", "망은행위", "수증자"],
    "채권각론서설_김준호_민법강의.md":
        ["채권각론", "개별적채권관계", "매매", "임대차", "도급",
         "전형계약", "채권관계발생원인", "계약법각론"],
    "채권법목차_총설_김준호_민법강의.md":
        ["채권법", "채권", "채무", "채권관계", "제373조", "제374조",
         "급부", "이행", "채권의목적"],
    "채권편총설_김준호_민법강의.md":
        ["채권", "채무", "채권편", "총설", "급부", "채권의효력",
         "채권자대위", "채권자취소", "다수당사자"],
    "채무인수_채권자제3자계약_김준호_민법강의.md":
        ["채무인수", "병존적채무인수", "면책적채무인수", "이행인수",
         "제453조", "제454조", "제459조", "채권자승낙", "제3자를위한계약",
         "수익자", "요약자", "낙약자"],
    "한국민법전연혁_김준호_민법강의.md":
        ["민법전", "민법연혁", "조선민사령", "1958", "1960",
         "민법제정", "민법개정"],
    "해제_물권적효과설_채권적효과설_김준호_민법강의.md":
        ["해제", "해제효과", "물권적효과", "채권적효과", "원상회복",
         "제548조", "제551조", "해제의제3자", "해지", "합의해제"],
}

OTHER_ROOTS = [
    r"H:\내 드라이브\sync\_교재원문\민법\송영곤_쟁점노트",
    r"H:\내 드라이브\sync\_교재원문\민법\송영곤_논점민법_본책",
    r"H:\내 드라이브\sync\_교재원문\민법\송영곤_논점민법_보충",
    r"H:\내 드라이브\sync\_교재원문\민법\전경운_민법3",
    r"H:\내 드라이브\sync\_교재원문\민법\곽낙규_사례연습",
    r"H:\내 드라이브\sync\_교재원문\민법\박승수_민법기본사례",
    r"H:\내 드라이브\sync\_교재원문\민법\윤동환_민법의맥",
    r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례연습2",
    r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례",
]

other_cache = []
for rt in OTHER_ROOTS:
    if not os.path.exists(rt):
        continue
    for fn in os.listdir(rt):
        if not fn.endswith('.md') or '김준호' in fn:
            continue
        fp = os.path.join(rt, fn)
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                other_cache.append({'path': fp, 'file': fn, 'content': f.read()})
        except Exception:
            pass
print(f"타 교재 캐시: {len(other_cache)}개\n")

CASE_RE = re.compile(r'\b(\d{2,4}(?:다|도|헌가|헌마|헌바|형상|다카)\d+)\b')
processed = 0
still_empty = []

for fn, kws in MANUAL_MAP.items():
    fp = os.path.join(KIM_ROOT, fn)
    if not os.path.exists(fp):
        continue
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    if '교차참조 블록: OCR 손상 보완용' in content:
        continue

    scored = []
    for oc in other_cache:
        fs = sum(3 for k in kws if k in oc['file'] and len(k) >= 3)
        cs = sum(oc['content'].count(k) for k in kws if len(k) >= 3)
        if fs > 0 or cs >= 10:
            scored.append({'path': oc['path'], 'file': oc['file'],
                          'content': oc['content'], 'fs': fs, 'cs': cs})
    scored.sort(key=lambda x: -(x['fs']*10 + x['cs']))
    scored = scored[:5]

    if not scored:
        still_empty.append(fn)
        continue

    global_cases = Counter()
    for r in scored:
        for kw in kws:
            if len(kw) < 3:
                continue
            for km in re.finditer(re.escape(kw), r['content']):
                s, e = max(0, km.start()-400), min(len(r['content']), km.end()+400)
                local = r['content'][s:e]
                for m in CASE_RE.finditer(local):
                    global_cases[m.group(1)] += 1
        r['cases'] = sorted(set(CASE_RE.findall(r['content'])))
    top_cases = global_cases.most_common(10)

    fm = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    tags = []
    if fm:
        tm = re.search(r'tags:\s*\[([^\]]+)\]', fm.group(1))
        if tm:
            tags = [t.strip() for t in tm.group(1).split(',')
                    if t.strip() not in ('교재원문', '민법', '김준호_민법강의')]

    lines = [
        "\n\n---\n\n",
        "<!-- 교차참조 블록: OCR 손상 보완용. 수동 쟁점 맵 기반 (LLM 확장). 2026-04-22 -->\n",
        "## 📚 교차참조: 다른 교재 동일 쟁점 판례\n\n",
        f"> 쟁점: `{', '.join(tags[:5])}`. 본문 괄호 안 판례 식별자가 OCR 손상 시 아래를 참조.\n",
        f"> 확장 키워드(수동): `{', '.join(kws[:8])}...`\n\n",
    ]
    if top_cases:
        lines.append("### 🔑 쟁점 근접 판례 (다른 교재 컨텍스트 기반 빈도 순)\n\n")
        for case, cnt in top_cases:
            lines.append(f"- [[{case}]] — 타 교재 근접 출현 {cnt}회\n")
        lines.append("\n")
    if scored:
        lines.append("### 📖 관련 교재 파일\n\n")
        for r in scored[:5]:
            stem = r['file'].replace('.md', '')
            lines.append(f"- [[{stem}]] (판례 {len(r['cases'])}개)\n")

    new_content = content.rstrip() + "".join(lines)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(new_content)
    processed += 1
    print(f"  OK {fn[:55]}: 판례 {len(top_cases)}개, 파일 {len(scored)}개")

print(f"\n처리: {processed}개 / 여전히 매칭 안 됨: {len(still_empty)}")
if still_empty:
    for f in still_empty:
        print(f"  - {f}")
