# -*- coding: utf-8 -*-
"""전수 정합성 점검 — 그간 변경(스키마통일·YAML수정·과목rename·진도속성·보드v2) 후 무결성.
읽기전용. PASS/FAIL 집계."""
import glob, json, os, re, sys
import yaml
sys.stdout.reconfigure(encoding="utf-8")
R = r"E:\법학볼트"; os.chdir(R)
WIKI = "sync/위키"
SUBJ = ["민법", "형법총론", "형법각론", "헌법", "민사소송법", "민사집행법", "행정법"]
ENTRY = re.compile(r"\[([^\[\]]+)\]\s*\[\[([^\]]+?)\]\]")
issues = []

# 0) 옛 폴더 잔존
for old in ["민소법", "민집법", "wiki", "쟁점", "원문"]:
    if os.path.isdir(os.path.join(WIKI, old)):
        issues.append(f"[폴더] 옛 폴더 잔존: {old}")

tot = yamlerr = badgwa = notype = nojeom = nodae = noprop = weaktrue = 0
card_marker = 0
dangling_link = 0
for s in SUBJ:
    folder = os.path.join(WIKI, s)
    if not os.path.isdir(folder): issues.append(f"[폴더] 누락: {s}"); continue
    moc = os.path.join(folder, f"_{s}_목차.md")
    if not os.path.exists(moc): issues.append(f"[MOC] 누락: _{s}_목차.md")
    for f in glob.glob(os.path.join(folder, "*.md")):
        b = os.path.basename(f)
        if b.startswith("_"): continue
        tot += 1
        t = open(f, encoding="utf-8").read()
        e = t.find("\n---", 3)
        fm = t[3:e] if t.startswith("---") and e > 0 else ""
        try:
            d = yaml.safe_load(fm)
            if not isinstance(d, dict): raise ValueError("non-dict")
        except Exception as ex:
            yamlerr += 1; issues.append(f"[YAML] {s}/{b}: {str(ex)[:30]}"); continue
        if d.get("과목") != s: badgwa += 1; issues.append(f"[과목] {s}/{b}: 과목={d.get('과목')}")
        if d.get("type") != "쟁점": notype += 1
        if not d.get("논점"): nojeom += 1
        if not d.get("대분류"): nodae += 1
        if "회독" not in d or "약점" not in d or "진도" not in d: noprop += 1
        if d.get("약점") is True: weaktrue += 1
        if "카드감사" in d: card_marker += 1
        # 상위 링크: 옛 과목 목차 링크 잔존?
        if "[[_민소법_목차]]" in t or "[[_민집법_목차]]" in t:
            dangling_link += 1; issues.append(f"[링크] {s}/{b}: 옛 목차 링크")

# MOC ↔ 노트 1:1 (목차 항목 = 노트 파일)
moc_mismatch = []
for s in SUBJ:
    moc = os.path.join(WIKI, s, f"_{s}_목차.md")
    if not os.path.exists(moc): continue
    titles = set()
    cur_legend = False
    for ln in open(moc, encoding="utf-8").read().splitlines():
        if ln.lstrip().startswith(">"): continue  # 범례
        for key, title in ENTRY.findall(ln):
            if title.strip() in ("쟁점", "제목"): continue
            titles.add(title.strip())
    notefiles = set(os.path.basename(f)[:-3] for f in glob.glob(os.path.join(WIKI, s, "*.md")) if not os.path.basename(f).startswith("_"))
    miss_note = titles - notefiles    # 목차엔 있는데 노트 없음
    extra_note = notefiles - titles   # 노트는 있는데 목차 없음
    if miss_note: moc_mismatch.append(f"{s}: 목차O노트X {len(miss_note)} {list(miss_note)[:3]}")
    if extra_note: moc_mismatch.append(f"{s}: 노트O목차X {len(extra_note)} {list(extra_note)[:3]}")

# 스크립트 SUBJ 잔존
script_leftover = []
for pf in glob.glob(".agent/scripts/*.py") + ["6.진도관리/board_server_v2.py"]:
    if os.path.basename(pf) == "_rename_과목.py": continue
    t = open(pf, encoding="utf-8").read()
    if '"민소법"' in t or '"민집법"' in t or "'민소법'" in t or "'민집법'" in t:
        script_leftover.append(os.path.basename(pf))

# _MOC.md 옛 링크
moc_hub = ""
if os.path.exists(os.path.join(WIKI, "_MOC.md")):
    h = open(os.path.join(WIKI, "_MOC.md"), encoding="utf-8").read()
    if "민소법" in h or "민집법" in h or "_민소법_목차" in h: moc_hub = "옛 약칭 잔존"

# .base 속성 점검
base_ok = os.path.exists(os.path.join(WIKI, "진도보드.base"))

print("=" * 48)
print(f"노트 총 {tot}")
print(f"YAML오류 {yamlerr} | 과목불일치 {badgwa} | type!=쟁점 {notype} | 논점없음 {nojeom} | 대분류없음 {nodae} | 진도속성없음 {noprop}")
print(f"약점 true {weaktrue} (0이어야) | 카드감사 마커 {card_marker} | 옛 목차링크 {dangling_link}")
print(f"MOC↔노트 불일치: {moc_mismatch if moc_mismatch else 'OK'}")
print(f"스크립트 옛SUBJ 잔존: {script_leftover if script_leftover else 'OK'}")
print(f"_MOC.md: {moc_hub or 'OK'} | 진도보드.base: {'존재' if base_ok else '없음'}")
print("-" * 48)
if issues:
    print(f"이슈 {len(issues)}건(상위 20):")
    for x in issues[:20]: print("  ", x)
else:
    print("개별 이슈 0건")
print("=" * 48)
print("판정:", "PASS ✅" if (yamlerr==badgwa==notype==nojeom==nodae==noprop==weaktrue==dangling_link==0 and not moc_mismatch and not script_leftover and not moc_hub and base_ok and not issues) else "점검필요 ⚠️")
