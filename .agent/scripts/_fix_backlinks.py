# -*- coding: utf-8 -*-
"""사례노트 깨진 백링크 수리(2026-07-08 감사 P1): 공백↔언더스코어 표기차만 기계 치환.
통칭 링크(실파일 부재·후보 다수)는 보고만. --dry 로 미리보기."""
import glob, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"E:\법학볼트")
DRY = "--dry" in sys.argv

# 볼트 전체 md basename 인덱스 (Obsidian 해석 방식)
names = {}
for f in glob.glob("sync/**/*.md", recursive=True) + glob.glob("outputs/**/*.md", recursive=True):
    names.setdefault(os.path.basename(f)[:-3], []).append(f)

pat = re.compile(r"\[\[([^\]|#]+)([^\]]*)\]\]")
fixed, unresolved = [], {}
for f in glob.glob("sync/위키/사례/*/*.md"):
    t = open(f, encoding="utf-8").read()
    changed = t
    for m in set(pat.findall(t)):
        target = m[0].strip()
        if target in names or not target:
            continue
        cands = set()
        for v in {target.replace(" ", "_"), target.replace("_", " ")}:
            if v in names:
                cands.add(v)
        if len(cands) == 1:
            new = cands.pop()
            changed = changed.replace(f"[[{m[0]}{m[1]}]]", f"[[{new}{m[1]}]]")
            fixed.append((os.path.basename(f)[:-3], target, new))
        else:
            unresolved.setdefault(target, []).append(os.path.basename(f)[:-3])
    if changed != t and not DRY:
        open(f, "w", encoding="utf-8").write(changed)

print(f"치환 {len(fixed)}건{' (dry)' if DRY else ''}")
for note, old, new in fixed[:20]:
    print(f"  {note}: [[{old}]] -> [[{new}]]")
print(f"\n미해결(통칭·부재) {len(unresolved)}종:")
for k, notes in sorted(unresolved.items(), key=lambda x: -len(x[1]))[:25]:
    print(f"  [[{k}]] x{len(notes)} — {notes[0][:40]}")
