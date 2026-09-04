# -*- coding: utf-8 -*-
"""논점노트 frontmatter에 진도속성 배선(Bases 닫힌루프). 멱등(회독: 있으면 skip).
파이썬은 구조적 frontmatter 추가용(PDF/삭제 아님). argv[1]=파일럿 건수(0=전체).
필드: 회독·선택·사례·기록(int) / 약점(bool) / 진도(미착수·진행·완료) / 최근복습(date)."""
import glob, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
R = r"E:\법학볼트"; os.chdir(R)
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0
SUBJ = ["민법", "형법총론", "형법각론", "헌법", "민사소송법", "민사집행법", "행정법"]
FIELDS = [("회독", "0"), ("선택", "0"), ("사례", "0"), ("기록", "0"),
          ("약점", "false"), ("진도", "미착수"), ("최근복습", '""')]
added = skipped = 0
for s in SUBJ:
    for f in sorted(glob.glob(f"sync/위키/{s}/*.md")):
        b = os.path.basename(f)
        if b.startswith("_"): continue
        t = open(f, encoding="utf-8").read()
        if not t.startswith("---"): continue
        end = t.find("\n---", 3)
        if end < 0: continue
        if re.search(r"(?m)^회독:", t[3:end]): skipped += 1; continue
        ins = "\n".join(f"{k}: {v}" for k, v in FIELDS)
        open(f, "w", encoding="utf-8").write(t[:end] + "\n" + ins + t[end:])
        added += 1
        if LIMIT and added >= LIMIT:
            print(f"[파일럿 {LIMIT}] 추가:{added} (다음: {b})"); sys.exit()
print(f"진도속성 추가:{added} skip(이미있음):{skipped}")
