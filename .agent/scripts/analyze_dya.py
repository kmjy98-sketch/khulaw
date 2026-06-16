import re, os, json, ntpath

out_base = 'H:/내 드라이브/.agent/data/ocr_chunks_reviewed/민법/윤동환_민법의맥'
manifest = 'H:/내 드라이브/.agent/state/batch2_g2.json'

with open(manifest, 'r', encoding='utf-8') as f:
    records = json.load(f)

patterns = {}
examples = {}

for rec in records:
    fname = ntpath.basename(rec['chunk_path'])
    out_path = out_base + '/' + fname
    if os.path.exists(out_path):
        with open(out_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for m in re.finditer(r'.{0,15}댜.{0,20}', content):
            ctx = m.group(0)
            # 정상 단어 제외: 쌍방대리, 단방대리, 대리인 등
            if '대리' in ctx:
                continue
            after_idx = ctx.index('댜') + 1
            after = ctx[after_idx:after_idx+5] if after_idx < len(ctx) else ''
            before_idx = max(0, ctx.index('댜') - 3)
            before = ctx[before_idx:ctx.index('댜')]
            key = repr(before[-2:] + '댜' + after[:3])
            patterns[key] = patterns.get(key, 0) + 1
            if key not in examples:
                examples[key] = ctx

for k, v in sorted(patterns.items(), key=lambda x: -x[1])[:25]:
    print(f'  {k}: {v}  ex: {examples[k]!r}')
