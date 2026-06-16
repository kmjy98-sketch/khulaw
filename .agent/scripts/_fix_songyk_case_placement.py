"""
송영곤 사례_가족/담보/물권/민총 신규 폴더에서
첫 파일은 root, 나머지는 _재추출/ 에 분산 배치된 것을
모두 root로 통일.
"""
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

FOLDERS = [
    Path(r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_가족"),
    Path(r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_담보"),
    Path(r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_물권"),
    Path(r"H:\내 드라이브\sync\_교재원문\민법\송영곤_사례_민총"),
]

moves = []
for folder in FOLDERS:
    재추출 = folder / "_재추출"
    if not 재추출.exists():
        continue
    for src in 재추출.iterdir():
        if src.is_file() and src.suffix == ".md":
            dst = folder / src.name
            if dst.exists():
                print(f"[SKIP] dst exists: {dst}")
                continue
            shutil.move(str(src), str(dst))
            moves.append((str(src), str(dst)))
            print(f"  {src.name} -> {dst.parent.name}/")
    # 빈 _재추출/ 디렉토리는 유지(삭제 금지)

print(f"\n총 {len(moves)}건 이동")
