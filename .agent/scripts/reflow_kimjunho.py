import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

def reflow_kimjunho(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        orig_text = f.read()

    text = orig_text

    # 1. 악성 괄호 노이즈 삭제 (블라인드 처리)
    # 김준호 교재 특유의 깨진 한글/한자/특수기호가 포함된 괄호 일괄 삭제
    nonsense_chars = ['끛', '쁮', '쫓', '깣', '쯔', '빷', '씿', '쯬', '콚', '읓', '쫔', '옻', '滿', '體', '쩨', '즟', '콫', '끷', '갗', '쯦', '쎷', '聽', '쀼', '魏', '쪼', '쯫', '껓', '默', '홏', '쯬', '盟', '씇', '쯬', '끛']
    for c in nonsense_chars:
        text = re.sub(r'\([^)]*' + c + r'[^)]*\)', '', text)
    
    # [^ 형식의 각주가 깨진 형태
    text = re.sub(r'\([^)]*[꽃깣]\[\^[^)]*\)', '', text)
    
    # 끄좇:끼!:끄:if：조 와 같은 콜론 남발 괄호
    text = re.sub(r'\([^)]*:[^)]*:[^)]*\)', '', text)

    # 2. 깨진 판례 형식 복원
    # 대S 2005： 1. 17： 2oSd?1477 -> 대판 2005.1.17. 다1477
    text = re.sub(r'대[S$]\s*(\d{4})[：:]\s*(\d{1,2})\.\s*(\d{1,2})[：:]\s*[A-Za-z0-9?]+(\d+)', r'대판 \1.\2.\3. 다\4', text)
    
    # 3. 줄바꿈 없는 인라인 리스트 강제 분리
    # 문장 끝(.)이나 띄어쓰기 뒤에 오는 a), (1), ①, ② 등을 찾아 마크다운 리스트로 분리
    
    # (1), (2) 등
    text = re.sub(r'([.?!>]\s*)\(([1-9][0-9]?)\)\s*', r'\1\n- \2) ', text)
    
    # a), b) 등
    text = re.sub(r'([.?!>]\s*)([a-z])\)\s*', r'\1\n- \2) ', text)
    
    # ①, ② 등
    text = re.sub(r'([.?!>]\s*)([①-⑳])\s*', r'\1\n- \2 ', text)
    
    # 백), w, 仕) 등 깨진 글머리 기호
    text = re.sub(r'([.?!>]\s*)([白w仕])\)\s*', r'\1\n- ', text)
    
    # (그), (느), (다) -> (1), (2), (3) 처럼 쓰인 깨진 한글 리스트 기호
    text = re.sub(r'([.?!>]\s*)\(([그느다라마바사아자차카타파하])\)\s*', r'\1\n- \2) ', text)

    # 4. 문맥 기반 강제 단락 분리 (숨쉴 틈 만들기)
    text = re.sub(r'([.?!>])\s*(한편|그러나|다만|예컨대|따라서|그러므로|요컨대)\s', r'\1\n\n\2 ', text)

    # 5. 기존 리플로우 로직 (판례 콜아웃 격리 등)
    lines = text.split('\n')
    final_lines = []
    
    for line in lines:
        if re.search(r'대판 \d{4}\.\d{1,2}\.\d{1,2}\.', line) and '[[20' in line and not line.startswith('> ') and not line.startswith('#'):
            if line.startswith('- '):
                line = "- > [!판례] 관련 판례\n  > " + line[2:].replace('. ', '.\n  > ')
            else:
                line = "> [!판례] 관련 판례\n> " + line.replace('. ', '.\n> ')
        final_lines.append(line)

    new_text = '\n'.join(final_lines)

    # 백링크 검증 (매우 중요)
    orig_links = re.findall(r'\[\[.*?\]\]', orig_text)
    new_links = re.findall(r'\[\[.*?\]\]', new_text)
    
    if len(orig_links) != len(new_links):
        print(f"FAILED: Link count mismatch (Orig: {len(orig_links)}, New: {len(new_links)})")
        return False
        
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print("SUCCESS")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    target = r"H:\내 드라이브\sync\_교재원문\민법\강혜림_민법1\물권법총론_물권의의의_김준호_민법강의.md"
    reflow_kimjunho(target)
