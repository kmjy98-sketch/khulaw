import fitz
import sys
import io
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

pdf_03 = vp("3.공법", "_분할", "유니온헌법기출편_03_통치구조_국회_대통령.pdf")
pdf_04 = vp("3.공법", "_분할", "유니온헌법기출편_04_법원_헌법재판소.pdf")

out_path = r"C:\Users\111\.gemini\antigravity\scratch\missing_dump.txt"

with open(out_path, "w", encoding="utf-8") as f:
    # 1. Inspect pdf_03 Page 2 to 15 (which should contain 문5, 문6, 문7, 문8)
    f.write("=== DUMPING pdf_03 Pages 7 to 18 ===\n")
    doc3 = fitz.open(pdf_03)
    for p in range(6, 17): # Page 7 to 17 (0-indexed 6 to 16)
        f.write(f"\n--- pdf_03 Page {p+1} ---\n")
        f.write(doc3[p].get_text("text"))

    # 2. Inspect pdf_04 Page 2 to 11 (which should contain 문77)
    f.write("\n=== DUMPING pdf_04 Pages 2 to 11 ===\n")
    doc4 = fitz.open(pdf_04)
    for p in range(1, 10): # Page 2 to 10 (0-indexed 1 to 9)
        f.write(f"\n--- pdf_04 Page {p+1} ---\n")
        f.write(doc4[p].get_text("text"))

    # 3. Inspect pdf_04 Page 119 to 121 (which should contain 문140)
    f.write("\n=== DUMPING pdf_04 Pages 119 to 121 ===\n")
    for p in range(118, 121): # Page 119 to 121 (0-indexed 118 to 120)
        f.write(f"\n--- pdf_04 Page {p+1} ---\n")
        f.write(doc4[p].get_text("text"))

print("Done writing missing_dump.txt in UTF-8")
