# -*- coding: utf-8 -*-
"""과목 약칭→풀네임: 민소법→민사소송법, 민집법→민사집행법.
폴더 리네임(이동, 삭제아님) + 노트 frontmatter 과목 + 상위링크 + MOC + _MOC + 스크립트 SUBJ + 목표json.
멱등(이미 풀네임이면 폴더 리네임 skip)."""
import glob, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
R = r"E:\법학볼트"; os.chdir(R)
PAIRS = [("민사소송법", "민사소송법"), ("민사집행법", "민사집행법")]
log = []

# 1) 폴더 리네임
for old, new in PAIRS:
    op = os.path.join("sync", "위키", old); npth = os.path.join("sync", "위키", new)
    if os.path.isdir(op) and not os.path.isdir(npth):
        os.rename(op, npth); log.append(f"폴더 {old}→{new}")
    elif os.path.isdir(npth):
        log.append(f"폴더 {new} 이미존재(skip)")

# 2) MOC 파일명 + 내부, 노트 frontmatter 과목 + 상위링크
for old, new in PAIRS:
    d = os.path.join("sync", "위키", new)
    if not os.path.isdir(d): continue
    om = os.path.join(d, f"_{old}_목차.md"); nm = os.path.join(d, f"_{new}_목차.md")
    if os.path.exists(om) and not os.path.exists(nm):
        os.rename(om, nm); log.append(f"MOC {os.path.basename(om)}→{os.path.basename(nm)}")
    for f in glob.glob(os.path.join(d, "*.md")):
        t = open(f, encoding="utf-8").read(); o = t
        t = re.sub(rf"(?m)^과목:\s*{old}\s*$", f"과목: {new}", t)
        t = t.replace(f"[[_{old}_목차]]", f"[[_{new}_목차]]")
        if os.path.basename(f).startswith("_"):  # MOC 내부 과목/제목
            t = re.sub(rf"(?m)^과목:\s*{old}\s*$", f"과목: {new}", t)
            t = t.replace(old, new)
        if t != o: open(f, "w", encoding="utf-8").write(t)

# 3) _MOC.md 허브
moc = os.path.join("sync", "위키", "_MOC.md")
if os.path.exists(moc):
    t = open(moc, encoding="utf-8").read(); o = t
    for old, new in PAIRS:
        t = t.replace(f"_{old}_목차", f"_{new}_목차").replace(old, new)
    if t != o: open(moc, "w", encoding="utf-8").write(t); log.append("_MOC.md 갱신")

# 4) 스크립트 SUBJ (.py)
pyfiles = glob.glob(".agent/scripts/*.py") + ["6.진도관리/board_server_v2.py"]
for pf in pyfiles:
    if not os.path.exists(pf): continue
    t = open(pf, encoding="utf-8").read(); o = t
    for old, new in PAIRS:
        t = t.replace(f'"{old}"', f'"{new}"').replace(f"'{old}'", f"'{new}'")
    if t != o: open(pf, "w", encoding="utf-8").write(t); log.append(f"SUBJ {os.path.basename(pf)}")

# 5) 진도보드_목표.json 초기화
goal = os.path.join("6.진도관리", "백업", "진도보드_목표.json")
os.makedirs(os.path.dirname(goal), exist_ok=True)
json.dump({"방학_단원": [], "내신_학기별": {}}, open(goal, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
log.append("진도보드_목표.json 초기화")

for x in log: print(" ", x)
print("rename 완료")
