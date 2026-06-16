import os
import re
import shutil
from pathlib import Path

# Configuration
SOURCE_ROOT = Path("h:/내 드라이브")
TARGET_DIR = SOURCE_ROOT / "1.민사" / "개념"
TRASH_DIR = SOURCE_ROOT / "5.기타" / "_trash" / "migrated"

# Ensure directories exist
TARGET_DIR.mkdir(parents=True, exist_ok=True)
TRASH_DIR.mkdir(parents=True, exist_ok=True)

def parse_filename(filename):
    """
    Parses filename to extract metadata.
    Expected patterns:
    1. 2-48_민법_송영곤_기본민법_수업정리_part48(이행인수_종류채권).md
    2. 5-00_민법_송영곤_기본민법_수업정리_(9).md (Less info, but usually has part info or similar)
    """
    
    # Try to extract part number
    part_match = re.search(r"part(\d+)", filename, re.IGNORECASE)
    source_lecture = f"part{part_match.group(1)}" if part_match else "Unknown"
    
    # Try to extract concept name from (...)
    # Logic: Look for text inside the LAST parentheses before extension, or mainly partXX(...)
    concept_match = re.search(r"\(([^)]+)\)\.md$", filename)
    
    if concept_match:
        concept_name = concept_match.group(1)
        # Cleanup: remove spaces, simplify
        concept_name = concept_name.replace(" ", "_")
    else:
        # Fallback: Use filename stem if no parenthesis
        concept_name = Path(filename).stem
        
    return {
        "source_lecture": source_lecture,
        "concept_name": concept_name,
        "original_filename": filename
    }

def process_file(file_path):
    try:
        content = file_path.read_text(encoding='utf-8')
        metadata = parse_filename(file_path.name)
        
        # New H1 Title
        new_title = metadata["concept_name"].replace("_", " ")
        
        # Construct Frontmatter
        frontmatter = f"""---
tags: []
aliases: []
source_lecture: {metadata['source_lecture']}
title: {new_title}
---

# {new_title}
"""
        
        # Prepare Footer
        footer = f"""

---

## Source & Context

- **과목**: #민법
- **강사**: #송영곤
- **강의**: 기본민법
- **출처**: [[{metadata['source_lecture']}]]
- **Original File**: `{metadata['original_filename']}`
"""

        # Transform Content
        # 1. Remove existing H1 titles that look like "# ..." or "# 과목 ..."
        lines = content.split('\n')
        new_lines = []
        skip_header = True
        
        for line in lines:
            # Skip initial H1s or metadata lines until we hit real content
            if skip_header:
                if line.strip().startswith("# ") or line.strip().startswith("---") or line.strip().startswith("#과목"):
                    continue
                if line.strip() == "":
                    continue
                # Found content start
                skip_header = False
                new_lines.append(line)
            else:
                new_lines.append(line)
                
        body_content = "\n".join(new_lines)
        
        # Assemble new content
        final_content = frontmatter + "\n" + body_content + footer
        
        # Define New Path
        new_filename = f"{metadata['concept_name']}.md"
        new_path = TARGET_DIR / new_filename
        
        # Write to New Path
        new_path.write_text(final_content, encoding='utf-8')
        print(f"Created: {new_path}")
        
        # Move original to Trash (simulate 'Move' by write-new-then-move-old)
        shutil.move(str(file_path), str(TRASH_DIR / file_path.name))
        print(f"Moved old to: {TRASH_DIR / file_path.name}")
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    # Find files matching pattern
    # Focusing on identified patterns
    root_dir = SOURCE_ROOT
    patterns = ["*수업정리*.md"]
    
    files = []
    for pattern in patterns:
        files.extend(root_dir.rglob(pattern))
        
    print(f"Found {len(files)} files to migrate.")
    
    for file_path in files:
        # Skip files already in TARGET_DIR or TRASH_DIR
        file_path_str = str(file_path).replace("\\", "/")
        if "1.민사/개념" in file_path_str or "5.기타/_trash" in file_path_str:
            continue
            
        process_file(file_path)

if __name__ == "__main__":
    main()
