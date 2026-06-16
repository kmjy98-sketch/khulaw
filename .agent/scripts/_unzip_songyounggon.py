"""송영곤_기본민법의 zip 14개 해체 → 각 zip 위치에 {zip명}/ 폴더로 풀고, 원본 zip → _trash.
한글 파일명(cp437→cp949) 복원. 광고성 PDF는 _격리/ 로 분리.
"""
import sys, zipfile, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"H:\내 드라이브")
BASE = R / "1.민사/30.송영곤_기본민법"
TRASH = R / "_trash/2026-06-14/송영곤_zip원본"
TRASH.mkdir(parents=True, exist_ok=True)


def fix(name: str) -> str:
    # zipfile은 비-UTF8 플래그 시 cp437로 읽음 → 한글은 cp949로 재해석
    try:
        return name.encode("cp437").decode("cp949")
    except Exception:
        return name


zips = sorted(BASE.rglob("*.zip"))
print(f"=== zip {len(zips)}개 해체 ===")
for z in zips:
    outdir = z.parent / z.stem
    outdir.mkdir(exist_ok=True)
    ad = 0
    with zipfile.ZipFile(z) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            real = fix(info.filename)
            # 광고성 분리
            sub = "_격리_광고성" if "광고성" in real else None
            dest = (outdir / sub / Path(real).name) if sub else (outdir / Path(real).name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            if sub:
                ad += 1
    # 원본 zip → _trash
    t = TRASH / z.name
    if not t.exists():
        shutil.move(str(z), str(t))
    n = len(list(outdir.rglob("*.*")))
    flag = f"  (광고성 {ad} 격리)" if ad else ""
    print(f"  [해체] {z.relative_to(BASE)} → {outdir.name}/ ({n}개){flag}")
print("zip 해체 완료, 원본 zip → _trash")
