#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify PDF<->MD matching from paddle_ocr_pipeline.ipynb Cell 1."""
import re, sys, io
from pathlib import Path
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DRIVE_ROOT = Path("H:/내 드라이브")
SYNC_ROOT  = DRIVE_ROOT / "sync" / "_교재원문"
SUBJECT_DIRS = ["1.민사", "2.형사", "3.공법", "4.선택법"]

PAGE_RANGE_RE  = re.compile(r'_p(\d+)-(\d+)\.(?:md|qmd)$')
SUBJECT_DIR_RE = re.compile(r'^\d+\.')

def scan_pdfs(drive_root):
    books = {}
    for d in Path(drive_root).iterdir():
        if not d.is_dir() or not SUBJECT_DIR_RE.match(d.name):
            continue
        for pdf in d.rglob("*.pdf"):
            book_id = pdf.stem
            collision = False
            if book_id in books:
                book_id = f"{book_id}__{pdf.parent.name}"
                collision = True
            books[book_id] = {"pdf_path": str(pdf), "collision": collision}
    return books

def scan_md_chunks(sync_root):
    md_map = defaultdict(list)
    for md in Path(sync_root).rglob("*.md"):
        m = PAGE_RANGE_RE.search(md.name)
        if m:
            stem = PAGE_RANGE_RE.sub('', md.name)
            md_map[stem].append(str(md))
    return dict(md_map)

def match_books(books, md_map):
    used_md_stems = set()
    direct, fuzzy, orphan_pdf = [], [], []
    for book_id, info in books.items():
        if book_id in md_map:
            info["md_chunks"] = md_map[book_id]
            info["match_type"] = "direct"
            used_md_stems.add(book_id)
            direct.append(book_id)
            continue
        book_tokens = set(book_id.lower().split("_"))
        best_stem, best_score = None, 0
        for stem in md_map:
            overlap = len(book_tokens & set(stem.lower().split("_")))
            if overlap > best_score and overlap >= 2:
                best_score, best_stem = overlap, stem
        if best_stem:
            info["md_chunks"] = md_map[best_stem]
            info["md_stem_matched"] = best_stem
            info["match_type"] = "fuzzy"
            used_md_stems.add(best_stem)
            fuzzy.append((book_id, best_stem, best_score))
        else:
            info["match_type"] = "orphan_pdf"
            orphan_pdf.append(book_id)
    orphan_md = [s for s in md_map if s not in used_md_stems]
    return direct, fuzzy, orphan_pdf, orphan_md

def find_orphan_md_candidates(orphan_md, books):
    """For each orphan MD stem, find PDF candidates with token overlap >=1."""
    suggestions = {}
    for stem in orphan_md:
        stem_tokens = set(stem.lower().split("_"))
        cands = []
        for book_id in books:
            overlap = len(stem_tokens & set(book_id.lower().split("_")))
            if overlap >= 1:
                cands.append((book_id, overlap))
        cands.sort(key=lambda x: -x[1])
        suggestions[stem] = cands[:2]
    return suggestions

def find_pdfs_outside_subject(sync_root, drive_root):
    """PDFs under sync/_교재원문/ which scan_pdfs ignores."""
    out = []
    for pdf in Path(sync_root).rglob("*.pdf"):
        out.append(str(pdf))
    # Also: PDFs in drive root NOT inside ^\d+\. dirs
    drive_orphan_pdfs = []
    for pdf in Path(drive_root).rglob("*.pdf"):
        # check if any parent is a subject dir
        rel_parts = pdf.relative_to(drive_root).parts
        if rel_parts and SUBJECT_DIR_RE.match(rel_parts[0]):
            continue
        # skip sync/_교재원문 already counted
        if "sync" in rel_parts and "_교재원문" in rel_parts:
            continue
        # skip _trash
        if rel_parts and rel_parts[0] in ("_trash", "_원본보관", "5.기타", "9.스터디 답안지", "0.공유드라이브"):
            continue
        drive_orphan_pdfs.append(str(pdf))
    return out, drive_orphan_pdfs

# === Run ===
books = scan_pdfs(DRIVE_ROOT)
md_map = scan_md_chunks(SYNC_ROOT)
direct, fuzzy, orphan_pdf, orphan_md = match_books(books, md_map)
collisions = [b for b, info in books.items() if info.get("collision")]

print(f"Total PDFs scanned: {len(books)}")
print(f"Total MD stems: {len(md_map)}")
print(f"A. Direct match: {len(direct)}")
print(f"B. Fuzzy match: {len(fuzzy)}")
print(f"C. Orphan PDF (no match): {len(orphan_pdf)}")
print(f"D. Orphan MD (no PDF matched): {len(orphan_md)}")
print(f"E. Collisions (book_id__parent): {len(collisions)}")

print("\n--- B. Fuzzy match samples (up to 5) ---")
for book_id, stem, score in fuzzy[:5]:
    print(f"  PDF[{book_id}] <-> MD[{stem}] (overlap={score})")

print("\n--- D. Orphan MD list (FULL) ---")
suggestions = find_orphan_md_candidates(orphan_md, books)
for stem in orphan_md:
    sample_path = md_map[stem][0]
    parent_dir = str(Path(sample_path).parent.relative_to(SYNC_ROOT))
    cand_str = "; ".join([f"{c[0]} (ov={c[1]})" for c in suggestions[stem]]) or "(no candidate)"
    print(f"  MD[{stem}] | dir={parent_dir} | cand={cand_str}")

print("\n--- E. Collision PDFs ---")
for c in collisions:
    print(f"  {c}")

print("\n--- F. PDFs under sync/_교재원문/ (ignored by scan_pdfs) ---")
sync_pdfs, drive_orphan_pdfs = find_pdfs_outside_subject(SYNC_ROOT, DRIVE_ROOT)
print(f"sync/_교재원문 직속 PDF: {len(sync_pdfs)}")
for p in sync_pdfs[:10]:
    print(f"  {p}")
print(f"\nDrive root non-subject PDFs (excluding _trash/etc): {len(drive_orphan_pdfs)}")
for p in drive_orphan_pdfs[:10]:
    print(f"  {p}")
