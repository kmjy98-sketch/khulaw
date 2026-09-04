import os
import re

SOURCE_FILE = r"h:\내 드라이브\민사\(5-27)민법_송영곤_민법입문_전사문.md"
OUTPUT_DIR = r"h:\내 드라이브\민사\split"
CHUNK_SIZE = 45000  # Characters (approx 12-15k tokens)

def split_transcript():
    if not os.path.exists(SOURCE_FILE):
        print(f"Error: Source file not found: {SOURCE_FILE}")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines(keepends=True)
    
    current_chunk = []
    current_char_count = 0
    file_count = 1
    
    # Header regex to identify split points (Level 1 or 2 headers)
    header_pattern = re.compile(r'^#{1,2}\s')

    for line in lines:
        # Check if we should split
        if current_char_count >= CHUNK_SIZE:
            # If line is a header, split here
            if header_pattern.match(line):
                write_chunk(current_chunk, file_count)
                current_chunk = []
                current_char_count = 0
                file_count += 1
            # If we are way past chunk size (e.g. +5000 chars) and still no header, force split at paragraph break
            elif current_char_count >= CHUNK_SIZE + 5000 and line.strip() == "":
                write_chunk(current_chunk, file_count)
                current_chunk = []
                current_char_count = 0
                file_count += 1
        
        current_chunk.append(line)
        current_char_count += len(line)

    # Write remaining chunk
    if current_chunk:
        write_chunk(current_chunk, file_count)

def write_chunk(lines, count):
    filename = f"(5-27)민법_송영곤_민법입문_part_{count:02d}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"Created: {filename} ({sum(len(l) for l in lines)} chars)")

if __name__ == "__main__":
    split_transcript()
