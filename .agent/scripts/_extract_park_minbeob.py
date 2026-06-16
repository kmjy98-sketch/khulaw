"""박승수 민법기본사례 텍스트 PDF 50p 청크 추출"""
import fitz
import os
import re
import json
from datetime import datetime

ROOT = r"H:\내 드라이브"
OUT_RAW = os.path.join(ROOT, "sync", "_ocr_extracted")
PROGRESS = os.path.join(ROOT, ".auto-memory", "ocr_state", "progress.json")

# (pdf_relpath, key, start_page) - start_page는 1-indexed, None이면 처음부터
TARGETS = [
    (r"1.민사\91.보관\박승수_민법기본사례\교재\박승수_민법기본사례_물권가족_23.pdf",
     "1민사__91보관__박승수_민법기본사례__교재__박승수_민법기본사례_물권가족_23",
     51),
    (r"1.민사\91.보관\박승수_민법기본사례\교재\박승수_민법기본사례_목차_23.pdf",
     "1민사__91보관__박승수_민법기본사례__교재__박승수_민법기본사례_목차_23",
     1),
    (r"1.민사\91.보관\박승수_민법기본사례\교재\박승수_민법기본사례_총론채권_23.pdf",
     "1민사__91보관__박승수_민법기본사례__교재__박승수_민법기본사례_총론채권_23",
     1),
]

CHUNK = 50

def normalize_text(text: str) -> str:
    # 한자 → 한글 자주 쓰는 매핑
    h2k = {
        "甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무",
        "原告": "원고", "被告": "피고", "債權者": "채권자", "債務者": "채무자",
        "債權": "채권", "債務": "채무", "所有權": "소유권", "占有": "점유",
    }
    for k, v in h2k.items():
        text = text.replace(k, v)
    # 백링크 정규화
    # § 뒤에 숫자만 (10 이상) → [[§N]]
    text = re.sub(r'§\s*(\d{2,3})(?:조)?', lambda m: f'[[§{m.group(1)}]]', text)
    # 제 N 조 → [[§N]] (10 이상)
    text = re.sub(r'제\s*(\d{2,3})\s*조(?!의)', lambda m: f'[[§{m.group(1)}]]', text)
    # 판례 번호 (YY다N, YY도N, YY헌마N 등)
    text = re.sub(r'(\d{2,4})(다|도|헌[가-힣]+|모|두|구|초|호|허|마)(\d{2,6})\b',
                  lambda m: f'[[{m.group(1)}{m.group(2)}{m.group(3)}]]',
                  text)
    return text

def extract_chunk(doc, start, end, pdf_label):
    parts = []
    for i in range(start - 1, min(end, doc.page_count)):
        page_text = doc[i].get_text()
        page_text = normalize_text(page_text)
        parts.append(f"\n## p{i+1:04d}\n\n{page_text}\n")
    return "".join(parts)

def write_chunk(out_dir, key, start, end, body, pdf_relpath):
    os.makedirs(out_dir, exist_ok=True)
    fname = f"{key}_p{start:04d}-{end:04d}.md"
    fpath = os.path.join(out_dir, fname)
    today = datetime.now().strftime("%Y-%m-%d")
    fm = (
        f"---\n"
        f"source: {pdf_relpath}\n"
        f"page_range: {start}-{end}\n"
        f"extracted_at: {today}\n"
        f"extractor: pymupdf-direct\n"
        f"author: 박승수\n"
        f"subject: 민법\n"
        f"---\n\n"
    )
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(fm + body)
    return fpath, len(body)

def update_progress(key, completed_chunks):
    with open(PROGRESS, encoding="utf-8") as f:
        data = json.load(f)
    if key in data:
        existing = data[key].get("completed_chunks", [])
        merged = existing + [list(c) for c in completed_chunks]
        # dedup
        seen = set()
        uniq = []
        for c in merged:
            t = tuple(c)
            if t not in seen:
                seen.add(t)
                uniq.append(list(c))
        data[key]["completed_chunks"] = uniq
    else:
        data[key] = {"completed_chunks": [list(c) for c in completed_chunks]}
    data[key]["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

results = []
for relpath, key, start_page in TARGETS:
    pdf_path = os.path.join(ROOT, relpath)
    if not os.path.exists(pdf_path):
        print(f"[MISSING] {relpath}")
        continue
    doc = fitz.open(pdf_path)
    n = doc.page_count
    out_dir = os.path.join(OUT_RAW, key)
    print(f"[GO] {key}: {n}p, start_at={start_page}")
    chunks = []
    s = start_page
    while s <= n:
        e = min(s + CHUNK - 1, n)
        body = extract_chunk(doc, s, e, relpath)
        fp, sz = write_chunk(out_dir, key, s, e, body, relpath)
        print(f"  [OK] {os.path.basename(fp)} ({sz}B)")
        chunks.append((s, e))
        s += CHUNK
    update_progress(key, chunks)
    results.append((key, n, chunks))
    doc.close()

print("\n=== SUMMARY ===")
for key, n, chunks in results:
    print(f"{key}: {n}p, chunks={chunks}")
