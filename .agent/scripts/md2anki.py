# -*- coding: utf-8 -*-
"""outputs/02_cards/*.md → Anki TSV 2종 변환.
- cloze 섹션(### 판례/학설 cloze, 헤더 Text⇥출처⇥태그) → anki_cloze.tsv (Cloze 노트)
- rule 섹션(### 조문·요건 rule, 헤더 앞⇥뒤⇥출처⇥태그) → anki_basic.tsv (Basic 노트)
태그 5축(과목::/속성::/주제::/난이도::/출처::)은 공백구분 그대로 Anki Tags로.
사건번호는 출처열에만(앞면 누설 0 유지).
"""
import glob, os, re

CARDS = r"H:\내 드라이브\outputs\02_cards"
OUT = r"H:\내 드라이브\outputs\anki"
os.makedirs(OUT, exist_ok=True)

basic, cloze = [], []   # basic:(front,back,src,tags)  cloze:(text,src,tags)
files = 0
skipped = []

for fp in sorted(glob.glob(os.path.join(CARDS, "*.md"))):
    files += 1
    try:
        content = open(fp, encoding="utf-8").read()
    except Exception as e:
        skipped.append((os.path.basename(fp), str(e)))
        continue
    for m in re.finditer(r"```tsv\s*\n(.*?)\n```", content, re.S):
        lines = [l for l in m.group(1).split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        hdr0 = lines[0].split("\t")[0].strip()
        is_rule = hdr0 in ("앞", "Front", "앞면")
        is_cloze = hdr0 in ("Text", "text", "본문")
        if not (is_rule or is_cloze):
            continue  # 헤더 불명 블록 skip
        for line in lines[1:]:
            c = [x.strip() for x in line.split("\t")]
            if is_rule and len(c) >= 4:
                basic.append((c[0], c[1], c[2], c[3]))
            elif is_cloze and len(c) >= 3:
                # cloze: 일부 파일은 4열(Text 분할)일 수 있어 끝 3열 기준
                cloze.append((c[0], c[-2], c[-1]))

# Basic: Front, Back, 출처, Tags  (Anki 신형 임포트 헤더)
with open(os.path.join(OUT, "anki_basic.tsv"), "w", encoding="utf-8") as f:
    f.write("#separator:tab\n#html:false\n#columns:Front\tBack\t출처\tTags\n#tags column:4\n")
    for r in basic:
        f.write("\t".join(r) + "\n")

# Cloze: Text, 출처, Tags
with open(os.path.join(OUT, "anki_cloze.tsv"), "w", encoding="utf-8") as f:
    f.write("#separator:tab\n#html:false\n#notetype:Cloze\n#columns:Text\t출처\tTags\n#tags column:3\n")
    for r in cloze:
        f.write("\t".join(r) + "\n")

print("파일 %d개 / Basic(rule) %d장 / Cloze %d장 / 합 %d장" % (files, len(basic), len(cloze), len(basic)+len(cloze)))
if skipped:
    print("skip:", skipped[:5])
