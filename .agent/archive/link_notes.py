import os
import re

# Base directory for concept notes
BASE_DIR = r"h:\내 드라이브\민사\민법\개념"
ARCHIVE_DIR = os.path.join(BASE_DIR, "_archive")

# Mapping of Keywords to Filenames
# Order matters: longer phrases should be processed before shorter ones to prevent partial matching issues
KEYWORD_MAP = [
    # 6차시 - 의사표시
    ("의사표시 도달주의", "의사표시_도달주의_수령능력.md"),
    ("도달주의", "의사표시_도달주의_수령능력.md"),
    ("수령능력", "의사표시_도달주의_수령능력.md"),
    ("비진의 의사표시", "비진의_의사표시_진의의_의미.md"),
    ("진의 아닌 의사표시", "비진의_의사표시_진의의_의미.md"),
    ("제107조", "비진의_의사표시_진의의_의미.md"),
    ("통정허위표시", "통정허위표시_요건_효과.md"),
    ("제108조", "통정허위표시_요건_효과.md"), 
    ("가장행위", "통정허위표시_요건_효과.md"),
    ("은닉행위", "통정허위표시_요건_효과.md"),
    ("108조 제3자", "통정허위표시_제3자_범위_사례.md"),
    ("선의의 제3자", "통정허위표시_제3자_범위_사례.md"),
    ("채권자취소권", "통정허위표시_채권자취소권.md"),
    ("제126조 유추적용", "표현대리_126조_유추적용.md"),
    ("표현대리 유추", "표현대리_126조_유추적용.md"),

    # 7차시 - 민사집행
    ("경매 공신력", "민사집행법_경매_공신력.md"),
    ("강제경매", "민사집행법_경매_공신력.md"),
    ("임의경매", "민사집행법_경매_공신력.md"),
    ("민집법 91조", "부동산_강제집행_매각조건.md"),
    ("소멸주의", "부동산_강제집행_매각조건.md"),
    ("인수주의", "부동산_강제집행_매각조건.md"),
    ("추심명령", "추심명령_전부명령_비교.md"),
    ("전부명령", "추심명령_전부명령_비교.md"),
    ("압류 경합", "전부명령_무효_경합.md"),
    ("가압류", "가압류_가처분_보전처분.md"),
    ("가처분", "가압류_가처분_보전처분.md"),
    ("보전처분", "가압류_가처분_보전처분.md"),

    # 8차시 - 착오/조건/무효
    ("착오취소", "착오취소_사기강박_경합.md"),
    ("제109조", "착오취소_사기강박_경합.md"),
    ("사기강박", "착오취소_사기강박_경합.md"),
    ("이단의 고의", "착오취소_사기강박_경합.md"),
    ("정지조건", "법률행위_조건_종류_효력.md"),
    ("해제조건", "법률행위_조건_종류_효력.md"),
    ("기성조건", "법률행위_조건_종류_효력.md"),
    ("기한이익", "법률행위_기한_기한이익.md"),
    ("불확정기한", "법률행위_기한_기한이익.md"),
    ("일부무효", "법률행위_일부무효_일부취소.md"),
    ("일부취소", "법률행위_일부무효_일부취소.md"),
    ("제137조", "법률행위_일부무효_일부취소.md"),
    ("무효행위 추인", "무효행위_추인_전환.md"),
    ("무효행위 전환", "무효행위_추인_전환.md"),
    ("제138조", "무효행위_추인_전환.md"),
    ("제139조", "무효행위_추인_전환.md"),

    # 9차시 - 소멸시효
    ("취소권자", "법률행위취소_취소권자_제척기간.md"),
    ("제척기간", "법률행위취소_취소권자_제척기간.md"),
    ("소멸시효 변론주의", "소멸시효_소송상성격_변론주의.md"),
    ("변론주의", "소멸시효_소송상성격_변론주의.md"),
    ("소멸시효 항변", "소멸시효_소송상성격_변론주의.md"),
    ("등기청구권 소멸시효", "소멸시효_대상_소유권이전등기청구권.md"),
    ("소유권이전등기청구권", "소멸시효_대상_소유권이전등기청구권.md"),
    ("소멸시효 기산점", "소멸시효_기산점_법률상장애.md"),
    ("법률상 장애", "소멸시효_기산점_법률상장애.md"),
    ("사실상 장애", "소멸시효_기산점_법률상장애.md"),
    ("단기소멸시효", "소멸시효_기간_단기소멸시효.md"),
    ("3년 단기소멸시효", "소멸시효_기간_단기소멸시효.md"),
    ("불법행위 소멸시효", "불법행위_소멸시효_기산점.md"),
    ("제766조", "불법행위_소멸시효_기산점.md"),
    ("이행지체 기산점", "소멸시효_기산점_이행지체_비교.md"),
    ("소멸시효 중단", "소멸시효_중단_효과.md"),
    ("제168조", "소멸시효_중단_효과.md"),
]

def link_notes():
    files = [f for f in os.listdir(BASE_DIR) if f.endswith(".md") and f != "README.md"]
    
    for filename in files:
        filepath = os.path.join(BASE_DIR, filename)
        
        # Determine files to validly link (exclude current file)
        valid_keywords = [(kw, target) for kw, target in KEYWORD_MAP if target != filename]
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace keywords with links
        for keyword, target_file in valid_keywords:
            # Check if keyword is already linked or part of a link
            # Regex negative lookbehind/lookahead to avoid double linking [[link|keyword]]
            # Simplifying: just look for the keyword if it's not surrounded by [ ]
            
            # Escape regex special characters in keyword
            escaped_kw = re.escape(keyword)
            
            # Pattern: keyword not preceded by [[ or | and not followed by ]] or |
            # This is complex in regex, so we'll use a safer replacement strategy
            # Only replace the first instance to avoid clutter
            
            # Simple check: if [[keyword]] or [[target|keyword]] already exists, skip
            if f"[[{target_file}|{keyword}]]" in content or f"[[{target_file}]]" in content:
                continue
                
            # Naive replacement for now, targeting plain text instances
            # Use a function to ensure we don't replace inside existing links
            def replace_if_not_linked(match):
                # Ensure the match isn't inside [[...]]
                # This logic is hard with simple replace, so we rely on first occurrence usually being safe or using specific sections
                return f"[[{target_file}|{keyword}]]"

            # Apply replacement only once (count=1) per file to avoid over-linking
            # Using sub with string replacement
            new_content = re.sub(f"(?<!\\[\\[)(?<!\\|){escaped_kw}(?!\\]\\])(?!\\|)", f"[[{target_file}|{keyword}]]", content, count=1)
            
            if new_content != content:
                content = new_content
        
        if content != original_content:
            print(f"Linking updated: {filename}")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

if __name__ == "__main__":
    link_notes()
    print("Linking complete.")
