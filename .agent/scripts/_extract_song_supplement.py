"""송영곤 보충자료 5건 직접 OCR 추출 (텍스트 PDF)"""
import fitz
import os
import re
import json
from datetime import datetime

ROOT = r"H:\내 드라이브"
OUT_RAW = os.path.join(ROOT, "sync", "_ocr_extracted")
PROGRESS = os.path.join(ROOT, ".auto-memory", "ocr_state", "progress.json")

# (pdf_relpath, key, label, dup_paths)
TARGETS = [
    (
        r"1.민사\송영곤_기본민법\기타\1-1_[송영곤_변호사]_2026_논점민강12판_보충자료1-26.1.11_1_26.pdf",
        "1민사__30송영곤_기본민법__기타__송영곤_논점민강12판_보충자료1_26111",
        "보충자료1_1.11",
        [r"1.민사\송영곤_기본민법\(1-1)[송영곤 변호사] 2026 논점민강(12판) 보충자료(1)-26.1.11.pdf"],
    ),
    (
        r"1.민사\송영곤_기본민법\기타\송영곤_논점민강12판_보충자료1-26.1.25..pdf",
        "1민사__30송영곤_기본민법__기타__송영곤_논점민강12판_보충자료1_26125",
        "보충자료1_1.25",
        [r"1.민사\송영곤_기본민법\(1)[송영곤 변호사] 2026 논점민강(12판) 보충자료(1)-26.1.25..pdf"],
    ),
    (
        r"1.민사\송영곤_기본민법\기타\2-1[송영곤_변호사]_2026_논점민강12판_보충자료2-26.2.2._26.pdf",
        "1민사__30송영곤_기본민법__기타__송영곤_논점민강12판_보충자료2_2622",
        "보충자료2_2.2",
        [r"1.민사\송영곤_기본민법\(2-1)[송영곤 변호사] 2026 논점민강(12판) 보충자료(2)-26.2.2..pdf"],
    ),
    (
        r"1.민사\31.송영곤_사례\(2-1)[송영곤 변호사] 2026 민사법사례연습 보충자료-26.2.2..pdf",
        "1민사__31송영곤_사례__송영곤_민사법사례연습_보충자료_2622",
        "사례보충_2.2",
        [],
    ),
    (
        r"1.민사\31.송영곤_사례\(5-1)[송영곤 변호사] 2026 민사법사례연습 보충자료(3)-26.2.26..pdf",
        "1민사__31송영곤_사례__송영곤_민사법사례연습_보충자료3_26226",
        "사례보충3_2.26",
        [],
    ),
]

def normalize_text(text: str) -> str:
    h2k = {
        "甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무",
        "原告": "원고", "被告": "피고",
    }
    for k, v in h2k.items():
        text = text.replace(k, v)
    text = re.sub(r'§\s*(\d{2,3})(?:조)?', lambda m: f'[[§{m.group(1)}]]', text)
    text = re.sub(r'제\s*(\d{2,3})\s*조(?!의)', lambda m: f'[[§{m.group(1)}]]', text)
    text = re.sub(r'(\d{2,4})(다|도|헌[가-힣]+|모|두|구|초|호|허|마)(\d{2,6})\b',
                  lambda m: f'[[{m.group(1)}{m.group(2)}{m.group(3)}]]', text)
    return text

def update_progress(key, completed_chunks, dup_paths):
    with open(PROGRESS, encoding="utf-8") as f:
        data = json.load(f)
    entry = {
        "completed_chunks": [list(c) for c in completed_chunks],
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if dup_paths:
        entry["duplicate_paths"] = dup_paths
    data[key] = entry
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

results = []
for relpath, key, label, dup_paths in TARGETS:
    pdf_path = os.path.join(ROOT, relpath)
    if not os.path.exists(pdf_path):
        print(f"[MISS] {label}")
        continue
    doc = fitz.open(pdf_path)
    n = doc.page_count
    out_dir = os.path.join(OUT_RAW, key)
    os.makedirs(out_dir, exist_ok=True)
    parts = []
    for i in range(n):
        t = normalize_text(doc[i].get_text())
        parts.append(f"\n## p{i+1:04d}\n\n{t}\n")
    body = "".join(parts)
    today = datetime.now().strftime("%Y-%m-%d")
    fm = (
        f"---\n"
        f"source: {relpath}\n"
        f"page_range: 1-{n}\n"
        f"extracted_at: {today}\n"
        f"extractor: pymupdf-direct\n"
        f"author: 송영곤\n"
        f"subject: 민법\n"
    )
    if dup_paths:
        fm += "duplicate_paths:\n"
        for d in dup_paths:
            fm += f"  - {d}\n"
    fm += "---\n\n"
    fname = f"{key}_p{1:04d}-{n:04d}.md"
    fpath = os.path.join(out_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(fm + body)
    update_progress(key, [(1, n)], dup_paths)
    print(f"[OK] {label}: {n}p -> {fname} ({len(body)}B)")
    results.append((label, n, fpath))
    doc.close()

print("\n=== SUMMARY ===")
for label, n, fp in results:
    print(f"{label}: {n}p")
