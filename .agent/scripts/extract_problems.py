import os
import pypdf
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')

pdf_paths = [
    vp("3.공법", "_분할", "유니온헌법기출편_03_통치구조_국회_대통령.pdf"),
    vp("3.공법", "_분할", "유니온헌법기출편_04_법원_헌법재판소.pdf"),
    vp("3.공법", "_분할", "2027해커스헌법사례형_01_헌법재판.pdf"),
    vp("3.공법", "_분할", "2027해커스헌법사례형_03_헌법총론_통치구조.pdf")
]

target_keywords = [
    "2020헌마264", "2018헌마1162", "2009헌라8", "2002헌바42", "2005다57752",
    "2010헌바132", "2024헌나8", "2022헌라4", "2023헌라5", "2013헌바370",
    "2018헌바211", "2012헌바298", "2021헌나1"
]

for pdf_path in pdf_paths:
    if not os.path.exists(pdf_path):
        continue
    print(f"\n==================== Searching in: {os.path.basename(pdf_path)} ====================")
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            num_pages = len(reader.pages)
            for page_idx in range(num_pages):
                text = reader.pages[page_idx].extract_text()
                for keyword in target_keywords:
                    if keyword in text:
                        print(f"[FOUND] Page {page_idx+1} | Keyword: {keyword}")
                        # Print a snippet around the keyword
                        matches = [m.start() for m in re.finditer(keyword, text)]
                        for m in matches[:2]:  # print up to 2 matches per page
                            start = max(0, m - 150)
                            end = min(len(text), m + 250)
                            snippet = text[start:end].replace('\n', ' ')
                            print(f"  Snippet: ... {snippet} ...")
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
