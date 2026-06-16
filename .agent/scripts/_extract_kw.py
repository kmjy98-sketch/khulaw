import json
import re

input_file = r"H:\내 드라이브\.agent\state\kw_slices\slice_16.jsonl"
output_file = r"H:\내 드라이브\.agent\state\kw_out\slice_16_out.jsonl"

# 출력 폴더 생성
import os
os.makedirs(os.path.dirname(output_file), exist_ok=True)

def extract_keywords(answer):
    """
    규칙:
    1. 2~14자 연속 문자열만 추출 (원문 그대로)
    2. 명사구 위주, 조사 포함 가능
    3. 답변 길이 12자 이하면 1~2개
    4. 따옴표·괄호가 경계에 걸리면 빼고 안쪽만
    """
    if not answer:
        return []
    
    # 따옴표, 괄호 정리 (경계 제거)
    # "..." 제거, (...) 제거 등
    cleaned = answer.strip()
    
    # 문제: 일단 핵심 명사구를 찾기
    # 2~14자 범위의 연속 부분을 찾는데,
    # 앞뒤로 띄어쓰기가 있거나 문장부호가 있는 부분
    
    kw_list = []
    length = len(cleaned)
    
    # 2~14자 substring 후보 탐색
    for start in range(length):
        for end in range(start + 2, min(start + 15, length + 1)):  # 2~14자
            substr = cleaned[start:end]
            
            # 앞뒤 경계 체크: 앞(start-1) 또는 뒤(end)가 공백/문장부호여야 함
            ok_start = (start == 0 or cleaned[start-1] in ' 、。,．·…')
            ok_end = (end == length or cleaned[end] in ' 、。,．·…')
            
            # 시작과 끝이 모두 경계라면 후보
            if ok_start and ok_end:
                # 앞뒤 공백 제거
                substr_clean = substr.strip()
                if substr_clean and len(substr_clean) >= 2 and len(substr_clean) <= 14:
                    # 불필요한 문장부호 제거
                    substr_clean = substr_clean.strip('"\'「」『』()（）')
                    if substr_clean and 2 <= len(substr_clean) <= 14:
                        kw_list.append(substr_clean)
    
    # 중복 제거 (순서 유지)
    seen = set()
    unique_kw = []
    for kw in kw_list:
        if kw not in seen:
            seen.add(kw)
            unique_kw.append(kw)
    
    # 길이에 따라 개수 제한
    if len(cleaned) <= 12:
        return unique_kw[:2]
    else:
        return unique_kw[:6]


count = 0
with open(input_file, 'r', encoding='utf-8') as f_in, \
     open(output_file, 'w', encoding='utf-8') as f_out:
    for line in f_in:
        line = line.strip()
        if not line:
            continue
        
        try:
            card = json.loads(line)
            k = card.get('k', '')
            a = card.get('a', '')
            
            kw = extract_keywords(a)
            
            output = {"k": k, "kw": kw}
            f_out.write(json.dumps(output, ensure_ascii=False) + '\n')
            count += 1
        except Exception as e:
            print(f"Error: {e}")

print(f"완료 {count}건")
