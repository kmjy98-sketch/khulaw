import fitz
import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

pdf_03 = r"H:\내 드라이브\3.공법\_분할\유니온헌법기출편_03_통치구조_국회_대통령.pdf"
pdf_04 = r"H:\내 드라이브\3.공법\_분할\유니온헌법기출편_04_법원_헌법재판소.pdf"

print("--- Scanning pdf_03 for 문5, 문6, 문7, 문8 (Page 2 to 23) ---")
doc3 = fitz.open(pdf_03)
for p in range(1, 23): # 0-indexed, so page 2 to 23
    text = doc3[p].get_text("text")
    # Print page headers or any line that looks like a question header or contains numbers
    print(f"=== Page {p+1} ===")
    lines = text.split('\n')
    for line in lines[:10]: # Print first 10 lines of each page to find the question headers
        print(f"  {line}")

print("\n--- Scanning pdf_04 for 문77 (Page 2 to 12) ---")
doc4 = fitz.open(pdf_04)
for p in range(1, 12):
    text = doc4[p].get_text("text")
    print(f"=== Page {p+1} ===")
    lines = text.split('\n')
    for line in lines[:10]:
        print(f"  {line}")

print("\n--- Scanning pdf_04 for 문140 (Page 109 to 121) ---")
for p in range(108, 121):
    text = doc4[p].get_text("text")
    print(f"=== Page {p+1} ===")
    lines = text.split('\n')
    for line in lines[:10]:
        print(f"  {line}")
