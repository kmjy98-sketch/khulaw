import os
import shutil

SOURCE_DIR = r"h:\내 드라이브\5.기타\_inbox"
# Broad bar-exam matches need manual subject routing, so keep them in a safe holding area.
BAR_EXAM_DIR = r"h:\내 드라이브\5.기타\보관\변호사시험_모의고사"
LEET_DIR = r"h:\내 드라이브\로스쿨 입시\LEET\보관"

LEET_KEYWORDS = ["해커스", "법저", "시대", "언어", "추리", "LEET"]
BAR_EXAM_KEYWORDS = ["FINAL", "파이널", "변모", "전모", "모의시험"]

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def organize_files():
    ensure_dir(BAR_EXAM_DIR)
    ensure_dir(LEET_DIR)

    files = [f for f in os.listdir(SOURCE_DIR) if os.path.isfile(os.path.join(SOURCE_DIR, f))]
    
    moved_count = 0
    
    for filename in files:
        src_path = os.path.join(SOURCE_DIR, filename)
        dest_dir = None
        
        # Check for Bar Exam keywords first (priority if overlap, though unlikely)
        if any(keyword in filename for keyword in BAR_EXAM_KEYWORDS):
            dest_dir = BAR_EXAM_DIR
        # Check for LEET keywords
        elif any(keyword in filename for keyword in LEET_KEYWORDS):
            dest_dir = LEET_DIR
            
        if dest_dir:
            dest_path = os.path.join(dest_dir, filename)
            try:
                shutil.move(src_path, dest_path)
                print(f"Moved: {filename} -> {dest_dir}")
                moved_count += 1
            except Exception as e:
                print(f"Error moving {filename}: {e}")
    
    print(f"Total files moved: {moved_count}")

if __name__ == "__main__":
    organize_files()
