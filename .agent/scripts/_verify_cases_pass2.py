# -*- coding: utf-8 -*-
"""② 2차 패스: False 281건 분류 정제.
A) 19xx 4자리 연도 → 2자리 변환 재검증(표기 문제)
B) 잔여 False → 출현 파일 목록과 함께 보고(오기·DB미수록 후보)"""
import json, os, re, sys, time, glob
sys.path.insert(0, r'E:\법학볼트\.agent\lib')
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'E:\법학볼트')
from law_api import verify_case

rows = [json.loads(l) for l in open('.agent/state/사건번호_전수검증.jsonl', encoding='utf-8')]
false_rows = [r for r in rows if r.get('verified') is False]

# 출현 파일 재수집
pat = re.compile(r'\d{2,4}(?:다카|다|도|두|므|마|재다|후|허|그|모|초기)\d{1,6}')
occurs = {}
for s in ['민법', '민사소송법', '헌법', '형법총론', '형법각론']:
    for f in glob.glob('sync/위키/사례/' + s + '/*.md'):
        t = open(f, encoding='utf-8').read()
        for c in set(pat.findall(t)):
            occurs.setdefault(c, []).append(s + '/' + os.path.basename(f)[:-3])

OUT2 = '.agent/state/사건번호_2차분류.json'
done2 = {}
if os.path.exists(OUT2):
    done2 = json.load(open(OUT2, encoding='utf-8'))

result = done2
for r in false_rows:
    c = r['번호']
    if c in result:
        continue
    m = re.match(r'^(19\d{2})(다카|다|도|두|므|마|재다|후|허|그|모|초기)(\d+)$', c)
    entry = {'출현파일': occurs.get(c, [])}
    if m:
        alt = m.group(1)[2:] + m.group(2) + m.group(3)
        try:
            v = verify_case(alt)
            if v.get('verified'):
                entry['분류'] = 'A_표기(2자리연도로 verified)'
                entry['정번호'] = alt
                entry['사건명'] = v.get('사건명', '')
            else:
                entry['분류'] = 'B_미확인(2자리 변환도 실패)'
                entry['시도'] = alt
        except Exception as e:
            entry['분류'] = 'ERR'
            entry['err'] = repr(e)[:60]
        time.sleep(0.25)
    else:
        entry['분류'] = 'B_미확인(현대 형식)'
    result[c] = entry
    if len(result) % 40 == 0:
        json.dump(result, open(OUT2, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(len(result), '/', len(false_rows))

json.dump(result, open(OUT2, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
a = [k for k, v in result.items() if v['분류'].startswith('A_')]
b = [k for k, v in result.items() if v['분류'].startswith('B_')]
err = [k for k, v in result.items() if v['분류'] == 'ERR']
print(f'2차 완료: A표기 {len(a)} / B미확인 {len(b)} / ERR {len(err)}')
# B 중 출현 2+ (오기면 파급 큼)
multi = sorted([(k, len(v["출현파일"])) for k, v in result.items()
                if v['분류'].startswith('B_') and len(v['출현파일']) >= 2],
               key=lambda x: -x[1])
print('B 중 출현 2+ :', len(multi))
for k, n in multi[:20]:
    print(' ', k, n, result[k]['출현파일'][:3])
