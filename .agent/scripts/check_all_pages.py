import os
import pypdf
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

dir_path = "H:/내 드라이브/작업용"

if not os.path.exists(dir_path):
    print(f"Directory not found: {dir_path}")
    sys.exit(1)

files = [f for f in os.listdir(dir_path) if f.lower().endswith('.pdf')]
files.sort()

print(f"Total PDFs found: {len(files)}")
print("-" * 60)

for f in files:
    filepath = os.path.join(dir_path, f)
    try:
        with open(filepath, 'rb') as fh:
            reader = pypdf.PdfReader(fh)
            num_pages = len(reader.pages)
            print(f"[OK] {f}: {num_pages}p")
    except Exception as e:
        print(f"[ERROR] {f} - {e}")
