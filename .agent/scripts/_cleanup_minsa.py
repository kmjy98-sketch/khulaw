"""작업용 잔여 민사책 정리: 깨진 _chunks → _trash, 플랫 파일 → 책별 폴더 (대분류 유지).
이동만(삭제 아님).
"""
import sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"H:\내 드라이브")
W = ROOT / "작업용"
TRASH = ROOT / "_trash" / "2026-06-14"

# 파일prefix → 폴더명 (대분류 분할 유지, 폴더화만)
GROUPS = [
    ("송영곤_신민사법선택형연습1", "신민사법선택형"),
    ("송영곤_사례연습", "송영곤사례연습"),
    ("김준호_민법강의", "김준호민법강의"),
    ("민사법쟁점노트", "민사법쟁점노트"),
    ("강성민_헌법_최종정리_OX", "강성민헌법OX"),
    ("compact형총OX", "compact형총OX"),
]


def safe_move(src: Path, dst_dir: Path):
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        print(f"  [건너뜀-대상존재] {src.name}")
        return False
    shutil.move(str(src), str(dst))
    return True


# 1) 남은 _chunks 전부 → _trash
chunks = sorted(W.glob("*_chunks"))
print(f"=== 깨진 _chunks {len(chunks)}개 → _trash ===")
for c in chunks:
    safe_move(c, TRASH)
    print(f"  [이동] {c.name}")

# 2) 플랫 파일 책별 폴더화
print("\n=== 플랫 민사책 폴더화 ===")
for prefix, folder in GROUPS:
    fs = sorted(W.glob(f"{prefix}_*.pdf"))
    moved = sum(safe_move(f, W / folder) for f in fs)
    print(f"  [{folder}/] {moved}개")

# 3) 김기용 standalone 목차(4p) → 기존 김기용형총/ 폴더로 합류
for f in sorted(W.glob("김기용_형법총론_목차*.pdf")):
    if safe_move(f, W / "김기용형총"):
        print(f"  [김기용형총/] 합류: {f.name}")

print("\n=== 정리 완료 ===")
