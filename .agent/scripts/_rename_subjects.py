"""과목폴더 명명위반 rename — 정찰(wbk290x26) 제안 그대로 적용.
변시기출(90.기출/번호접두 495) 제외, 빈제안 제외. 기본 DRY-RUN, --apply 시 실제 rename.
"""
import sys, json, os
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"H:\내 드라이브")
OUT = Path(r"C:\Users\111\AppData\Local\Temp\claude\H--------\20603c1d-acd0-40d1-ab66-0cfd1c7587a7\tasks\wbk290x26.output")
APPLY = "--apply" in sys.argv

data = json.loads(OUT.read_text(encoding="utf-8"))
viol = data["result"]["naming_subjects"]["violations"]

# 저자 추정 등 위험한 의미변경은 제외(원제 유지)
EXCLUDE = {
    "2.형사/94.교재/새로쓴형법총론_ocr_x.pdf",  # '서보학_형법총론'은 저자 추정 — 보류
}

plan = []
skip = []
for v in viol:
    path = v["path"].replace("/", os.sep)
    sug = (v.get("suggested") or "").strip()
    issue = v.get("issue", "")
    if "90.기출" in v["path"] or "변시기출" in issue:
        continue  # 495 기출 제외
    if v["path"] in EXCLUDE:
        skip.append((v["path"], "위험-저자추정 보류"))
        continue
    if not sug:
        skip.append((v["path"], "제안없음"))
        continue
    old = ROOT / path
    if not old.exists():
        skip.append((v["path"], "파일없음"))
        continue
    ext = old.suffix
    newname = sug if sug.lower().endswith(ext.lower()) else sug + ext
    new = old.parent / newname
    if new.exists():
        skip.append((v["path"], f"대상존재:{newname}"))
        continue
    plan.append((old, new, issue))

print(f"=== rename 계획 {len(plan)}건 (DRY-RUN={'OFF' if APPLY else 'ON'}) ===")
for old, new, issue in plan:
    rel = old.relative_to(ROOT)
    print(f"  {rel.parent}{os.sep}")
    print(f"    {old.name}")
    print(f"    → {new.name}   [{issue[:30]}]")
if APPLY:
    n = 0
    for old, new, _ in plan:
        os.rename(old, new); n += 1
    print(f"\n[적용완료] {n}건 rename")
print(f"\n=== 건너뜀 {len(skip)}건 ===")
for p, why in skip:
    print(f"  [{why}] {p}")
