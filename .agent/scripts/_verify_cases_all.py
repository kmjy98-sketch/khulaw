# -*- coding: utf-8 -*-
"""② 사례노트 대법원계 사건번호 전수 verify (T0, law_api 캐시·재개형).
결과: .agent/state/사건번호_전수검증.jsonl (1행=1번호) + 요약 출력."""
import glob, json, os, re, sys, time
sys.path.insert(0, r'E:\법학볼트\.agent\lib')
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'E:\법학볼트')
from law_api import verify_case

OUT = '.agent/state/사건번호_전수검증.jsonl'
done = {}
if os.path.exists(OUT):
    for ln in open(OUT, encoding='utf-8'):
        try:
            d = json.loads(ln); done[d['번호']] = d
        except Exception:
            pass

pat = re.compile(r'\d{2,4}(?:다카|다|도|두|므|마|재다|후|허|그|모|초기)\d{1,6}')
occurs = {}
for s in ['민법', '민사소송법', '헌법', '형법총론', '형법각론']:
    for f in glob.glob('sync/위키/사례/' + s + '/*.md'):
        t = open(f, encoding='utf-8').read()
        for c in set(pat.findall(t)):
            occurs.setdefault(c, []).append(os.path.basename(f)[:-3])

todo = [c for c in sorted(occurs) if c not in done]
print(f'고유 {len(occurs)} / 기검증 {len(done)} / 잔여 {len(todo)}')
with open(OUT, 'a', encoding='utf-8') as fo:
    for i, c in enumerate(todo):
        try:
            r = verify_case(c)
            row = {'번호': c, 'verified': bool(r.get('verified')),
                   '사건명': r.get('사건명', ''), '출현': len(occurs[c])}
        except Exception as e:
            row = {'번호': c, 'verified': None, 'err': repr(e)[:60], '출현': len(occurs[c])}
        fo.write(json.dumps(row, ensure_ascii=False) + '\n')
        fo.flush()
        if i % 100 == 0:
            print(i, '/', len(todo))
        time.sleep(0.25)

rows = [json.loads(l) for l in open(OUT, encoding='utf-8')]
nf = [r for r in rows if r.get('verified') is False]
print(f'완료: 총 {len(rows)} | verified {sum(1 for r in rows if r.get("verified"))} | False {len(nf)} | 오류 {sum(1 for r in rows if r.get("verified") is None)}')
# False 중 단일 출현(오탈 가능성 상위) 상위 30
nf.sort(key=lambda r: r.get('출현', 0))
for r in nf[:30]:
    print('  False:', r['번호'], '(출현', r.get('출현'), ')')
