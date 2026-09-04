"""
split_notes_v2.py
- 복합 파일 → 단일 개념 파일 분리 (## Header 2 기준)
- aliases 자동 추가 (핵심 개념명)
- Navigation 링크 자동 생성 (강의 순서 기반)
"""

import os
import re
import shutil
import json
from pathlib import Path

# Configuration
TARGET_DIR = Path(r"h:\내 드라이브\민사\민법\개념")
ARCHIVE_DIR = TARGET_DIR / "_archive"
STATE_FILE = TARGET_DIR / "concept_order.json"  # Navigation 순서 저장

def sanitize_filename(name: str) -> str:
    """Remove numbering and invalid characters from header text."""
    # Remove leading numbering like "1. ", "2. "
    name = re.sub(r'^\d+\.\s*', '', name)
    # Remove [Tags] at the start
    name = re.sub(r'^\[.*?\]\s*', '', name)
    # Remove star ratings (★, ⭐, etc.)
    name = re.sub(r'\s*[★⭐✓✔]+', '', name)
    # Remove all emojis and special unicode
    name = re.sub(r'[^\w\s가-힣a-zA-Z0-9_\-]', '', name)
    # Remove parentheses content for cleaner filenames
    name = re.sub(r'\s*\([^)]*\)\s*', '', name)
    # Replace spaces with underscores
    name = name.strip().replace(' ', '_')
    return name

def safe_print(msg: str):
    """Print with encoding fallback for Windows console."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('utf-8', errors='replace').decode('utf-8'))

def extract_core_concept(title: str) -> str:
    """Extract core concept name for aliases."""
    # Remove numbering and stars
    core = re.sub(r'^\d+\.\s*', '', title)
    core = re.sub(r'\s*★+', '', core)
    core = re.sub(r'\s*\([^)]*\)', '', core)
    return core.strip()

def split_markdown_file(file_path: Path) -> list[dict]:
    """Split file by ## headers. Returns list of {title, content, order, source}."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract source_lecture from frontmatter
    source_match = re.search(r'source_lecture:\s*(\S+)', content)
    source_lecture = source_match.group(1) if source_match else "unknown"
    
    # Extract part number for ordering (e.g., "part38" -> 38)
    part_match = re.search(r'part(\d+)', source_lecture)
    base_order = int(part_match.group(1)) * 100 if part_match else 0
    
    lines = content.split('\n')
    chunks = []
    current_title = None
    current_content = []
    section_order = 0
    
    for line in lines:
        # Match ## Header (Level 2)
        match = re.match(r'^##\s+(.+)$', line)
        if match:
            # Save previous chunk
            if current_title and current_content:
                text = '\n'.join(current_content).strip()
                if len(text) > 50:
                    chunks.append({
                        'title': current_title,
                        'content': text,
                        'order': base_order + section_order,
                        'source': source_lecture,
                        'original_file': file_path.name
                    })
            
            # Start new chunk
            section_order += 1
            current_title = match.group(1).strip()
            current_content = [f"# {current_title}"]
        elif current_title:
            current_content.append(line)
    
    # Append last chunk
    if current_title and current_content:
        text = '\n'.join(current_content).strip()
        if len(text) > 50:
            chunks.append({
                'title': current_title,
                'content': text,
                'order': base_order + section_order,
                'source': source_lecture,
                'original_file': file_path.name
            })
    
    return chunks

def create_frontmatter(title: str, source: str, aliases: list[str]) -> str:
    """Create YAML frontmatter with aliases."""
    aliases_str = ', '.join(aliases)
    return f"""---
tags: [민법]
aliases: [{aliases_str}]
source_lecture: {source}
title: {title}
---

"""

def create_navigation(prev_file: str | None, next_file: str | None) -> str:
    """Create navigation section."""
    nav = "\n---\n\n## Navigation\n\n"
    if prev_file:
        nav += f"- **Previous**: [[{prev_file}]]\n"
    if next_file:
        nav += f"- **Next**: [[{next_file}]]\n"
    return nav

def process_files(dry_run: bool = False):
    """Main processing function."""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    
    # Get all markdown files (exclude scripts and archive)
    files = [f for f in TARGET_DIR.glob("*.md") 
             if not f.name.startswith(('split_', 'link_', 'README'))]
    
    all_chunks = []
    
    safe_print(f"Phase 1: Splitting {len(files)} files...")
    
    for file_path in files:
        chunks = split_markdown_file(file_path)
        all_chunks.extend(chunks)
        if chunks:
            safe_print(f"  {file_path.name} -> {len(chunks)} concepts")
    
    # Sort by order (lecture order)
    all_chunks.sort(key=lambda x: x['order'])
    
    # Save order mapping
    order_map = []
    
    safe_print(f"\nPhase 2: Creating {len(all_chunks)} concept files...")
    
    for i, chunk in enumerate(all_chunks):
        safe_title = sanitize_filename(chunk['title'])
        if not safe_title:
            continue
        
        # Determine prev/next
        prev_file = sanitize_filename(all_chunks[i-1]['title']) if i > 0 else None
        next_file = sanitize_filename(all_chunks[i+1]['title']) if i < len(all_chunks)-1 else None
        
        # Create aliases
        core_concept = extract_core_concept(chunk['title'])
        aliases = [core_concept] if core_concept != chunk['title'] else []
        
        # Build content
        frontmatter = create_frontmatter(chunk['title'], chunk['source'], aliases)
        navigation = create_navigation(prev_file, next_file)
        source_footer = f"\n---\n\n**Source**: [[{chunk['original_file']}]]"
        
        full_content = frontmatter + chunk['content'] + navigation + source_footer
        
        new_filename = f"{safe_title}.md"
        new_path = TARGET_DIR / new_filename
        
        # Handle duplicates
        counter = 1
        while new_path.exists():
            new_path = TARGET_DIR / f"{safe_title}_{counter}.md"
            counter += 1
        
        order_map.append({
            'order': chunk['order'],
            'file': new_path.name,
            'title': chunk['title'],
            'source': chunk['source']
        })
        
        if not dry_run:
            with open(new_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
        
        safe_print(f"  [{i+1}/{len(all_chunks)}] {new_path.name}")
    
    # Save order mapping
    if not dry_run:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(order_map, f, ensure_ascii=False, indent=2)
        safe_print(f"\nSaved order mapping to {STATE_FILE}")
    
    # Archive originals
    if not dry_run:
        safe_print(f"\nPhase 3: Archiving {len(files)} original files...")
        for file_path in files:
            try:
                shutil.move(str(file_path), str(ARCHIVE_DIR / file_path.name))
            except Exception as e:
                safe_print(f"  Error archiving {file_path.name}: {e}")
    
    safe_print(f"\nDone! Created {len(all_chunks)} concept files.")
    return order_map

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        safe_print("=== DRY RUN MODE ===\n")
    process_files(dry_run=dry_run)
