import os
import hashlib
import json
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

sync_dir = vp("sync")
output_report = r"C:\Users\111\.gemini\antigravity\scratch\sync_analysis.json"

def get_sha256(filepath):
    h = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def analyze():
    analysis = {
        "total_files": 0,
        "total_dirs": 0,
        "structure": {},
        "area_counts": {
            "_교재원문": 0,
            "_meta": 0,
            "wiki": 0,
            "1-1_기말": 0,
            "_ocr_extracted": 0,
            "_백업_2026-04-30": 0,
            "_백업_2026-05-05": 0,
            "_백업_기타": 0,
            "_trash_2026-04-30": 0,
            "_trash_2026-05-05": 0,
            "_trash_기타": 0,
            "_재추출": 0,
            "기타": 0
        },
        "empty_dirs": [],
        "duplicated_groups": {},
        "markers": {
            "need_check": [],      # [확인필요]
            "need_table_fix": []   # [표복구필요]
        },
        "file_details": []
    }

    hashes = {} # hash -> list of filepaths

    for root, dirs, files in os.walk(sync_dir):
        # Exclude output directories
        if 'output' in dirs:
            dirs.remove('output')
        if any(part == 'output' for part in root.split(os.sep)):
            continue

        rel_root = os.path.relpath(root, sync_dir)
        if rel_root == ".":
            rel_root = ""

        # Check for empty directories
        if not dirs and not files:
            analysis["empty_dirs"].append(rel_root)

        analysis["total_dirs"] += 1

        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, sync_dir)
            analysis["total_files"] += 1

            # Get area classification
            area = "기타"
            parts = rel_path.split(os.sep)
            first_part = parts[0]
            
            if first_part == "_교재원문":
                area = "_교재원문"
            elif first_part == "_meta":
                area = "_meta"
            elif first_part in ["wiki", "위키"]:
                area = "wiki"
            elif first_part == "1-1_기말":
                area = "1-1_기말"
            elif first_part == "_ocr_extracted":
                area = "_ocr_extracted"
            elif first_part == "_백업":
                if len(parts) > 1 and "2026-04-30" in parts[1]:
                    area = "_백업_2026-04-30"
                elif len(parts) > 1 and "2026-05-05" in parts[1]:
                    area = "_백업_2026-05-05"
                else:
                    area = "_백업_기타"
            elif first_part == "_trash" or first_part == ".trash":
                if len(parts) > 1 and "2026-04-30" in parts[1]:
                    area = "_trash_2026-04-30"
                elif len(parts) > 1 and "2026-05-05" in parts[1]:
                    area = "_trash_2026-05-05"
                else:
                    area = "_trash_기타"
            elif first_part == "_재추출":
                area = "_재추출"

            analysis["area_counts"][area] += 1

            # Check file size & hash for duplication
            size = os.path.getsize(filepath)
            # Only compute hash for files > 0 bytes to find actual duplicates
            if size > 0:
                fhash = get_sha256(filepath)
                if fhash:
                    hashes.setdefault((size, fhash), []).append(rel_path)

            # Check for markers in filename and file content
            marker_check = False
            marker_table = False

            if "[확인필요]" in file:
                marker_check = True
            if "[표복구필요]" in file:
                marker_table = True

            # If it's a text file (md, txt, json etc.), search inside
            if file.endswith(('.md', '.txt', '.json', '.py', '.html')):
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if "[확인필요]" in content:
                            marker_check = True
                        if "[표복구필요]" in content:
                            marker_table = True
                except Exception:
                    pass

            if marker_check:
                analysis["markers"]["need_check"].append(rel_path)
            if marker_table:
                analysis["markers"]["need_table_fix"].append(rel_path)

            analysis["file_details"].append({
                "rel_path": rel_path,
                "size": size,
                "area": area
            })

    # Filter duplicate groups (only where there are 2 or more files with the same size & hash)
    for (size, fhash), paths in hashes.items():
        if len(paths) > 1:
            analysis["duplicated_groups"][f"{size}_{fhash}"] = paths

    # Write results
    with open(output_report, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=4)

    print(f"Analysis completed. Total files: {analysis['total_files']}. Results written to {output_report}")

if __name__ == "__main__":
    analyze()
