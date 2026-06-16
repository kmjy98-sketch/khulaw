"""작업용 폴더 PDF 스캔 (일회성, read-only)
각 PDF: 페이지수 / 용량MB / outline(목차) 보유여부 / 최상위 목차 항목수
_chunks 폴더: 기계 100p 분할 여부 표시
"""
import sys
from pathlib import Path
from pypdf import PdfReader

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"H:\내 드라이브\작업용")


def top_outline_count(reader):
    try:
        ol = reader.outline
    except Exception:
        return None
    if not ol:
        return 0
    # 최상위 항목만 카운트 (list 중첩 제외)
    return sum(1 for it in ol if not isinstance(it, list))


def scan(pdf: Path):
    try:
        r = PdfReader(str(pdf))
        pages = len(r.pages)
        oc = top_outline_count(r)
    except Exception as e:
        return (pdf, None, None, f"ERR:{type(e).__name__}")
    size = pdf.stat().st_size / (1024 * 1024)
    return (pdf, pages, size, oc)


top_pdfs = sorted(ROOT.glob("*.pdf"))
chunk_dirs = sorted(ROOT.glob("*_chunks"))

print("=" * 90)
print("최상위 PDF (작업용 직속)")
print("=" * 90)
print(f"{'파일명':<55} {'pages':>6} {'MB':>8} {'목차':>6}")
print("-" * 90)
for pdf in top_pdfs:
    _, pages, size, oc = scan(pdf)
    name = pdf.name if len(pdf.name) <= 54 else pdf.name[:51] + "..."
    oc_s = "없음" if oc == 0 else (str(oc) if isinstance(oc, int) else str(oc))
    if pages is None:
        print(f"{name:<55} {'?':>6} {'?':>8} {oc_s:>6}")
    else:
        print(f"{name:<55} {pages:>6} {size:>8.1f} {oc_s:>6}")

print()
print("=" * 90)
print("_chunks 폴더 (100p 기계분할 흔적)")
print("=" * 90)
for d in chunk_dirs:
    chunks = sorted(d.glob("*.pdf"))
    total_mb = sum(c.stat().st_size for c in chunks) / (1024 * 1024)
    over = sum(1 for c in chunks if c.stat().st_size / (1024 * 1024) > 50)
    base = d.name.replace("_chunks", "")
    base = base if len(base) <= 50 else base[:47] + "..."
    print(f"{base:<52} 청크{len(chunks):>3}개  합{total_mb:>7.1f}MB  50MB초과 {over}개")
