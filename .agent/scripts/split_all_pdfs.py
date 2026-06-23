import os
import sys
import io
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

# Add the parent directory of script to sys.path so we can import pdf_split_100p
sys.path.append(str(Path(VAULT_ROOT)))
try:
    import pdf_split_100p
except ImportError:
    # If not found directly, try adding H:\내 드라이브 to path explicitly
    pass

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

dir_path = Path(vp("작업용"))

target_files = [
    "2026 표준판례 반영 헌법 핵심정리 300 - 각종 국가고시 대비, 제3전정4판,_3c_r6_d2.pdf",
    "COMPACT 형법 - 반반형법 플러스, 제4판_3c_r6_d2.pdf",
    "민사법쟁점노트_재산법_26.pdf",
    "민사법쟁점노트_소송,집행_26.pdf",
    "민사법쟁점노트_가족법_26.pdf",
    "송영곤_사례연습_채권_26.pdf",
    "송영곤_사례연습_민총_26.pdf",
    "송영곤_사례연습_물권_26.pdf",
    "송영곤_사례연습_담보_26.pdf",
    "송영곤_사례연습_가족_26.pdf"
]

print("Starting batch PDF split process...")
print("-" * 60)

for filename in target_files:
    filepath = dir_path / filename
    if not filepath.exists():
        print(f"[MISSING] {filename} does not exist in {dir_path}")
        continue
    
    print(f"[START] Splitting {filename}...")
    try:
        # We call the split_pdf function from pdf_split_100p module
        import pdf_split_100p
        pdf_split_100p.split_pdf(filepath, pages_per_chunk=100)
        print(f"[SUCCESS] Completed splitting {filename}\n")
    except Exception as e:
        print(f"[ERROR] Failed to split {filename}: {e}\n")

print("-" * 60)
print("Batch PDF split process finished.")
