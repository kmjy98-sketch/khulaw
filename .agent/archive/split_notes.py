import os
import re
import shutil

# Configuration
TARGET_DIR = r"h:\내 드라이브\민사\민법\개념"
ARCHIVE_DIR = os.path.join(TARGET_DIR, "_archive")

def sanitize_filename(name):
    """
    Sanitizes the header text to be a valid filename.
    Removes special characters, replaces spaces with underscores.
    """
    # Remove bracketed content like [개념 1], [쟁점] for cleaner filenames?
    # User might prefer keeping them unique. Let's keep meaningful text.
    # Remove strict regex patterns like [0-9]+. or [개념 1] if they are just numbering.
    
    # Remove leading numbering like "1. ", "2. "
    name = re.sub(r'^\d+\.\s*', '', name)
    
    # Remove [Tags] at the start if any
    name = re.sub(r'^\[.*?\]\s*', '', name)

    # Replace invalid chars
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    # Replace spaces with underscores
    name = name.strip().replace(' ', '_')
    return name

def split_markdown_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by headers level 2 or 3 (assuming level 1 is file title)
    # Regex lookahead to find headers
    # We want to capture the header line and the following content
    
    # Strategy:
    # 1. Frontmatter and Level 1 header might be general context.
    # 2. Level 2 (##) and Level 3 (###) are likely concepts.
    # Let's target the deepest clear semantic unit. 
    # If a file has ##, we split by ##. If it has ### inside, maybe we should split by ###?
    # Let's try splitting by Header 2 (##) first as major concepts. 
    # If a section is too small, maybe it's not a concept.
    
    # Refined Strategy:
    # Treat text between headers as a chunk.
    # Header 2 is the main unit.
    
    lines = content.split('\n')
    
    chunks = []
    current_title = "Intro"
    current_content = []
    original_filename = os.path.basename(file_path)
    
    # Extract existing frontmatter if any (to copy context?)
    # For now, we will create new simple frontmatter or just append source info.
    
    for line in lines:
        # Match ## Header (Level 2)
        match = re.match(r'^(##+)\s+(.+)$', line)
        if match:
            # Save previous chunk if it has content
            if current_content:
                # Filter out empty chunks or just frontmatter junk
                text_content = "\n".join(current_content).strip()
                if len(text_content) > 50: # Minimal length check
                    chunks.append({'title': current_title, 'content': text_content})
            
            # Start new chunk
            current_title = match.group(2).strip()
            current_content = [line] # Include the header in the content? Or as title? 
            # If we make it a file, the filename is the title. The content should start with # Title or just text.
            # Let's include the header line in content for context, but maybe adjust level to H1 (#)
            current_content = [f"# {current_title}"] 
        else:
            current_content.append(line)
            
    # Append last chunk
    if current_content:
         text_content = "\n".join(current_content).strip()
         if len(text_content) > 50:
            chunks.append({'title': current_title, 'content': text_content})

    return chunks

def process_directory():
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)

    files = [f for f in os.listdir(TARGET_DIR) if f.endswith(".md")]
    
    print(f"Found {len(files)} markdown files in {TARGET_DIR}")

    for filename in files:
        file_path = os.path.join(TARGET_DIR, filename)
        
        print(f"Processing: {filename}")
        
        # Split logic
        chunks = split_markdown_file(file_path)
        
        if not chunks:
            print(f" - No chunks found or file too short: {filename}")
            continue

        # Save chunks as new files
        for chunk in chunks:
            if chunk['title'] == "Intro": 
                continue # Skip introduction chunks usually containing just toc or metadata
            
            safe_title = sanitize_filename(chunk['title'])
            if not safe_title: continue

            new_filename = f"{safe_title}.md"
            new_path = os.path.join(TARGET_DIR, new_filename)
            
            # Handle duplicate filenames (append counter)
            counter = 1
            while os.path.exists(new_path):
                new_path = os.path.join(TARGET_DIR, f"{safe_title}_{counter}.md")
                counter += 1
            
            # Add Source Metadata footer
            footer = f"\n\n---\n**Source**: [[{filename}]]"
            
            try:
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write(chunk['content'] + footer)
                print(f"  -> Created: {os.path.basename(new_path)}")
            except Exception as e:
                print(f"  -> Error creating {new_path}: {e}")

        # Move original to archive
        try:
            shutil.move(file_path, os.path.join(ARCHIVE_DIR, filename))
            print(f" - Moved original to {ARCHIVE_DIR}")
        except Exception as e:
            print(f" - Error moving {filename}: {e}")

if __name__ == "__main__":
    process_directory()
