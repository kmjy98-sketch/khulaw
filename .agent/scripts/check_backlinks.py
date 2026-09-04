import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

def main():
    sync_dir = vp("sync")
    
    # 1. 수집: 모든 존재하는 마크다운 파일명(확장자 제외)
    existing_notes = set()
    for root, _, files in os.walk(sync_dir):
        for f in files:
            if f.endswith('.md'):
                existing_notes.add(f[:-3])

    # 2. 파싱: 모든 마크다운 파일에서 백링크 추출
    # [[노트이름]] 또는 [[노트이름|별칭]] 또는 [[노트이름#헤딩]]
    link_pattern = re.compile(r'\[\[([^|#\]]+)(?:[|#][^\]]*)?\]\]')
    
    missing_case_links = set()
    # 판례번호 정규식: "2016다220679", "99다7992", "2011헌마234" 등
    case_pattern = re.compile(r'\d{2,4}[가-힣A-Za-z]+\d+')

    for root, _, files in os.walk(sync_dir):
        for f in files:
            if not f.endswith('.md'): continue
            
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
            except Exception as e:
                continue
                
            links = link_pattern.findall(content)
            for link in links:
                link = link.strip()
                if link not in existing_notes:
                    if case_pattern.match(link):
                        missing_case_links.add(link)

    # 3. MOC 작성
    moc_path = os.path.join(sync_dir, "_판례색인", "미연결_판례_MOC.md")
    
    # 정렬하여 출력
    sorted_missing = sorted(list(missing_case_links))
    
    with open(moc_path, 'w', encoding='utf-8') as f:
        f.write("# 미연결 판례 MOC\n\n")
        f.write("> 실제 파일이 없으나 문서 내에서 참조(백링크)된 판례 목록입니다.\n\n")
        for case in sorted_missing:
            f.write(f"- [[{case}]]\n")
            
    print(f"Total missing case links found: {len(sorted_missing)}")
    print(f"MOC file created at: {moc_path}")

if __name__ == "__main__":
    main()
