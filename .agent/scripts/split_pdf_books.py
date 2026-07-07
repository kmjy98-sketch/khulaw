import os
import subprocess
import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter

# E:\법학볼트\.agent\scripts\split_pdf_books.py
# 10.도서관/ 하위의 표준 정규화된 원본 PDF를 읽어서 단원별로 분할하고 master 로그에 기록함.

split_plan = [
    {
        "book_name": "compact형각OX",
        "source": "compact형각OX.pdf",
        "target_dir": "2.형사/_원본보관/compact형각OX",
        "splits": [
            ("compact형각OX_00_목차.pdf", 1, 10),
            ("compact형각OX_01_개인적법익.pdf", 11, 250),
            ("compact형각OX_02_사회적법익.pdf", 251, 320),
            ("compact형각OX_03_국가적법익.pdf", 321, 397)
        ]
    },
    {
        "book_name": "논점민집",
        "source": "논점민집.pdf",
        "target_dir": "1.민사/_원본보관/논점민집",
        "splits": [
            ("논점민집_00_목차.pdf", 1, 9),
            ("논점민집_01_이론정리.pdf", 10, 55),
            ("논점민집_02_논점사례.pdf", 56, 170),
            ("논점민집_99_색인.pdf", 171, 185)
        ]
    },
    {
        "book_name": "신민사법선택형_민소",
        "source": "신민사법선택형_민소.pdf",
        "target_dir": "1.민사/_원본보관/신민사법선택형_민소",
        "splits": [
            ("신민사법선택형_민소_00_목차.pdf", 1, 4),
            ("신민사법선택형_민소_01_소송주체.pdf", 5, 70),
            ("신민사법선택형_민소_02_제1심절차.pdf", 71, 270),
            ("신민사법선택형_민소_03_소송병합_다수당사자.pdf", 271, 441)
        ]
    },
    {
        "book_name": "형법요론_각론",
        "source": "형법요론_각론.pdf",
        "target_dir": "2.형사/_원본보관/형법요론_각론",
        "splits": [
            ("형법요론_각론_00_목차.pdf", 1, 17),
            ("형법요론_각론_01_개인적법익.pdf", 18, 650),
            ("형법요론_각론_02_사회적국가적법익.pdf", 651, 1000),
            ("형법요론_각론_99_색인.pdf", 1001, 1043)
        ]
    },
    {
        "book_name": "행정법강해",
        "source": "행정법강해.pdf",
        "target_dir": "3.공법/_원본보관/행정법강해",
        "splits": [
            ("행정법강해_00_목차.pdf", 1, 19),
            ("행정법강해_01_통론_작용법.pdf", 20, 206),
            ("행정법강해_02_절차_의무이행.pdf", 207, 306),
            ("행정법강해_03_손해전보_쟁송.pdf", 307, 739),
            ("행정법강해_04_지방자치_특별행정.pdf", 740, 893),
            ("행정법강해_99_색인.pdf", 894, 925)
        ]
    }
]

WS_ROOT = Path("E:/법학볼트")
LOG_HELPER = WS_ROOT / ".agent" / "scripts" / "log_file_op.py"

def split_pdf(source_path: Path, target_dir: Path, splits: list, book_name: str):
    print(f"\n[시작] {book_name} 분할 처리 중...")
    if not source_path.exists():
        print(f"[오류] 원본 파일이 존재하지 않습니다: {source_path}", file=sys.stderr)
        return False

    try:
        reader = PdfReader(source_path)
    except Exception as e:
        print(f"[오류] PDF 파일을 읽을 수 없습니다: {source_path}. 에러: {e}", file=sys.stderr)
        return False
        
    total_pages = len(reader.pages)
    print(f"원본 전체 페이지 수: {total_pages}")

    target_dir.mkdir(parents=True, exist_ok=True)

    for filename, start_page, end_page in splits:
        # 페이지 검증
        if start_page < 1 or end_page > total_pages or start_page > end_page:
            print(f"[오류] 유효하지 않은 페이지 범위: {start_page} ~ {end_page} (최대 {total_pages})", file=sys.stderr)
            return False

        output_path = target_dir / filename
        writer = PdfWriter()

        # 0-indexed 변환하여 페이지 추가
        for idx in range(start_page - 1, end_page):
            writer.add_page(reader.pages[idx])

        try:
            with open(output_path, "wb") as f:
                writer.write(f)
        except Exception as e:
            print(f"[오류] 분할본 저장 실패: {filename}. 에러: {e}", file=sys.stderr)
            return False

        print(f"  → 분할 생성 완료: {filename} ({start_page} ~ {end_page} 페이지)")

        # log_file_op.py를 사용하여 master 로그 등록
        fake_src = f"{source_path.name} (분할본 {start_page}-{end_page}p)"
        cmd = [
            sys.executable,
            str(LOG_HELPER),
            "--op", "copy",
            "--src", fake_src,
            "--dst", str(output_path),
            "--reason", f"TOC 분할 규칙(#16-D): {book_name} 단원 분할 ({start_page}p-{end_page}p)",
            "--task-id", "pdf-split-20260626"
        ]
        
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res.returncode != 0:
            print(f"[경고] 로그 등록 실패: {res.stderr.strip()}", file=sys.stderr)
        else:
            print(f"  {res.stdout.strip()}")

    return True

def main():
    success_books = []
    failed_books = []

    # 10.도서관 하위의 표준 정규화된 원본 PDF 파일들을 분할 소스로 지정
    library_dir = WS_ROOT / "10.도서관"

    for plan in split_plan:
        src_path = library_dir / plan["source"]
        tgt_dir = WS_ROOT / plan["target_dir"]
        
        ok = split_pdf(src_path, tgt_dir, plan["splits"], plan["book_name"])
        if ok:
            success_books.append(plan)
        else:
            failed_books.append(plan["book_name"])

    print("\n====================================")
    print("작업 결과 요약")
    print(f"성공: {', '.join([b['book_name'] for b in success_books]) or '없음'}")
    print(f"실패: {', '.join(failed_books) or '없음'}")
    print("====================================")

if __name__ == "__main__":
    main()
