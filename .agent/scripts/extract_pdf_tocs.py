import os
import pypdf
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')

pdf_files = {
    "숙제": vp("3.공법", "10.이진_헌법원리1", "2026 헌법의 기초이론 결정례 숙제(기말).pdf"),
    "강의계획서": vp("3.공법", "10.이진_헌법원리1", "강의계획서.pdf"),
    "핵정_헌재": vp("3.공법", "_분할", "핵심정리300_01_헌법재판.pdf"),
    "핵정_총론": vp("3.공법", "_분할", "핵심정리300_03_기본권_나머지_헌법총론.pdf"),
    "핵정_통치": vp("3.공법", "_분할", "핵심정리300_04_통치구조.pdf"),
    "유니온_통치": vp("3.공법", "_분할", "유니온헌법기출편_03_통치구조_국회_대통령.pdf"),
    "유니온_헌재": vp("3.공법", "_분할", "유니온헌법기출편_04_법원_헌법재판소.pdf"),
    "해커스_헌재": vp("3.공법", "_분할", "2027해커스헌법사례형_01_헌법재판.pdf"),
    "해커스_통치": vp("3.공법", "_분할", "2027해커스헌법사례형_03_헌법총론_통치구조.pdf")
}

def get_toc(reader, outline, depth=0):
    toc_list = []
    if outline is None:
        return toc_list
    for item in outline:
        if isinstance(item, list):
            toc_list.extend(get_toc(reader, item, depth + 1))
        else:
            title = item.title if hasattr(item, 'title') else str(item)
            page_num = -1
            try:
                # get_page_number might raise exception if target is not resolved
                if hasattr(item, 'page'):
                    page_num = reader.get_page_number(item.page) + 1
            except Exception:
                pass
            toc_list.append((depth, title, page_num))
    return toc_list

for name, path in pdf_files.items():
    print(f"\n===== {name} ({os.path.basename(path)}) =====")
    if not os.path.exists(path):
        print("File not found")
        continue
    try:
        with open(path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            outline = reader.outline
            tocs = get_toc(reader, outline)
            if tocs:
                for depth, title, page in tocs[:50]:  # Limit to 50 items
                    print("  " * depth + f"- {title} (p.{page})")
                if len(tocs) > 50:
                    print(f"  ... and {len(tocs) - 50} more items")
            else:
                print("No PDF outline found. Extracting first 2 pages text:")
                for i in range(min(2, len(reader.pages))):
                    text = reader.pages[i].extract_text()
                    lines = [line.strip() for line in text.split('\n') if line.strip()][:15]
                    print(f"  --- Page {i+1} ---")
                    for line in lines:
                        print(f"    {line}")
    except Exception as e:
        print(f"Error: {e}")
