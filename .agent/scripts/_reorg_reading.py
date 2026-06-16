"""독해용 분할 후 재배치+정리 (생성 완료 후 실행).
1) 작업용/{책ID}_*.pdf  →  작업용/{책ID}/  (책별 폴더)
2) 원본 9개            →  작업용/_원본/
3) 깨진 _chunks 8개    →  _trash/2026-06-14/
모두 이동(삭제 아님). 존재할 때만.
"""
import sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"H:\내 드라이브")
W = ROOT / "작업용"
TRASH = ROOT / "_trash" / "2026-06-14"
ORIG = W / "_원본"

# 책ID → 원본파일명
BOOKS = {
    "논점민소": "2026 논점 민사소송법 - 변호사 시험 & 각종 국가고시 대비,_3c_r6_d2.pdf",
    "민사례1": "2026 민사법 사례연습 1 - 진도별 요약형 - 제2판_3c_r6_d2 (1).pdf",
    "헌법300": "2026 표준판례 반영 헌법 핵심정리 300 - 각종 국가고시 대비, 제3전정4판,_3c_r6_d2.pdf",
    "해커스헌": "[5+1] 2027 해커스변호사 변호사시험 기출문제집 헌법 사례형 - 최신개정판ㅣ변호사시험 등 각종 국가고_3c_r6_d2.pdf",
    "반반형법": "COMPACT 형법 - 반반형법 플러스, 제4판_3c_r6_d2.pdf",
    "김기용형총": "김기용_형법총론_교안_26.pdf",
    "논점재산법": "논점민법강의_재산법_26.pdf",
    "유니온헌": "유니온 헌법 기출편(2027 대비).pdf",
    "작은변사기": "작은변사기형법_25.pdf",
}


def safe_move(src: Path, dst_dir: Path):
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        print(f"  [건너뜀-대상존재] {src.name}")
        return False
    shutil.move(str(src), str(dst))
    return True


for bid, origname in BOOKS.items():
    folder = W / bid
    # 1) 분할 파일 책별 폴더로 (원본 제외하고 {bid}_ 로 시작하는 pdf만)
    moved = 0
    for f in sorted(W.glob(f"{bid}_*.pdf")):
        if safe_move(f, folder):
            moved += 1
    # 2) 원본 → _원본/
    orig = W / origname
    omoved = safe_move(orig, ORIG) if orig.exists() else None
    # 3) _chunks → _trash
    chunk = W / f"{Path(origname).stem}_chunks"
    cmoved = safe_move(chunk, TRASH) if chunk.exists() else None
    print(f"[{bid}] 분할 {moved}개 → {bid}/ | 원본 {'이동' if omoved else '-'} | _chunks {'이동' if cmoved else '없음/이동완료'}")

print("\n=== 재배치 완료 ===")
print("작업용/ 책별 폴더 + _원본/ 구성, 깨진 _chunks → _trash/2026-06-14/")
