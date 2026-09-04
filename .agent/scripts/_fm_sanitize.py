# -*- coding: utf-8 -*-
"""frontmatter YAML 깨짐 수정 — 값에 콜론(: ) 들어간 줄을 따옴표로 감싼다.
원인: '카드감사: 완료 (누락 N건: 상세)' 처럼 값 내부 콜론이 YAML mapping 오류 유발.
멱등(이미 따옴표면 skip). argv[1]=과목(없으면 전체). 본문 불변, frontmatter 값만."""
import glob, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
os.chdir(r"E:\법학볼트")
SUBJ = [sys.argv[1]] if len(sys.argv) > 1 else ["민법", "형법총론", "형법각론", "헌법", "민사소송법", "민사집행법", "행정법"]
fixed = 0
for s in SUBJ:
    for f in glob.glob(f"sync/위키/{s}/*.md"):
        if os.path.basename(f).startswith("_"): continue
        t = open(f, encoding="utf-8").read()
        if not t.startswith("---"): continue
        e = t.find("\n---", 3)
        if e < 0: continue
        fm = t[3:e]; out = []; chg = False
        for ln in fm.split("\n"):
            m = re.match(r"^([^:\n]+):[ \t](.*)$", ln)
            if not m: out.append(ln); continue
            key, val = m.group(1), m.group(2)
            v = val.strip()
            if v and v[0] not in "\"'" and ":" in v:
                esc = v.replace("\\", "\\\\").replace('"', '\\"')
                out.append(f'{key}: "{esc}"'); chg = True
            else:
                out.append(ln)
        if chg:
            open(f, "w", encoding="utf-8").write(t[:3] + "\n".join(out) + t[e:]); fixed += 1
print(f"수정 파일: {fixed}")
