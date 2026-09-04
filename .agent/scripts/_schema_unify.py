# -*- coding: utf-8 -*-
"""frontmatter 스키마 통일 — 목차(_{과목}_목차.md)를 권위로 논점노트 정규화.
목차 제목=노트 파일명 정확매칭(추측 금지 #50-C는 LLM이나, 여기선 제목 1:1 결정매칭).
세팅: type=쟁점 · 논점=목차KEY · 대분류 · 중분류(있으면) · 스키마=통일(날짜). 기타 키 보존.
argv[1]=과목(파일럿) 없으면 전체. 매칭/미매칭/목차에있으나노트없음 리포트.
"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
R = r"E:\법학볼트"; os.chdir(R)
WIKI = "sync/위키"
SUBJ = [sys.argv[1]] if len(sys.argv) > 1 else ["민법", "형법총론", "형법각론", "헌법", "민사소송법", "민사집행법", "행정법"]
ENTRY = re.compile(r"\[([^\[\]]+)\]\s*\[\[([^\]]+?)\]\]")

def parse_moc(path):
    cur_dae = cur_jung = ""
    m = {}
    for ln in open(path, encoding="utf-8").read().splitlines():
        h = re.match(r"^(#{2,3})\s+(.+?)\s*$", ln)
        if h:
            txt = re.sub(r"\s*\[[^\]]*\]\s*~\s*\[[^\]]*\]\s*$", "", h.group(2)).strip()
            if len(h.group(1)) == 2: cur_dae, cur_jung = txt, ""
            else: cur_jung = txt
            continue
        for key, title in ENTRY.findall(ln):
            m[title.strip()] = (key.strip(), cur_dae, cur_jung)
    return m

def setfield(fm, key, val):
    if re.search(rf"(?m)^{re.escape(key)}:", fm):
        return re.sub(rf"(?m)^{re.escape(key)}:.*$", f"{key}: {val}", fm)
    return fm + f"\n{key}: {val}"

for s in SUBJ:
    moc = os.path.join(WIKI, s, f"_{s}_목차.md")
    if not os.path.exists(moc): print(f"[{s}] 목차없음 {moc}"); continue
    M = parse_moc(moc)
    notes = [f for f in glob.glob(os.path.join(WIKI, s, "*.md")) if not os.path.basename(f).startswith("_")]
    matched = unmatched = 0; miss_note = []
    seen = set()
    for f in notes:
        title = os.path.basename(f)[:-3]
        if title not in M: unmatched += 1; print(f"  [미매칭노트] {s}/{title}"); continue
        key, dae, jung = M[title]; seen.add(title)
        t = open(f, encoding="utf-8").read()
        e = t.find("\n---", 3)
        if not t.startswith("---") or e < 0: print(f"  [fm없음] {title}"); continue
        fm = t[3:e]
        fm = setfield(fm, "type", "쟁점")
        fm = setfield(fm, "논점", key)
        fm = setfield(fm, "대분류", dae)
        if jung: fm = setfield(fm, "중분류", jung)
        fm = setfield(fm, "스키마", "통일 (2026-06-28)")
        open(f, "w", encoding="utf-8").write(t[:3] + fm + t[e:])
        matched += 1
    miss_note = [tt for tt in M if tt not in seen]
    print(f"[{s}] 매칭 {matched} / 미매칭노트 {unmatched} / 목차에있으나노트없음 {len(miss_note)}: {miss_note[:8]}")
