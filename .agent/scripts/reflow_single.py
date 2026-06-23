import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

filepath = vp('sync', '_교재원문', '민법', '송영곤_논점민법_본책', '임대차_임차권_대항력_상가건물임대차_송영곤_논점민법.md')

with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. OCR 오탈자 교정
replacements = {
    '仰판': '대판',
    '而판': '대판',
    "대판'": '대판',
    '대판(2合)': '대판(전원합의체)',
    '금흉기관': '금융기관',
    '배탕요쿠': '배당요구',
    '계햑': '계약',
    '금핵': '금액',
    '토증금줗': '보증금 중',
    '승#흘T디¥': '승계한 다음',
    '호증금': '보증금',
    '마찬가지이디;': '마찬가지이다.',
    '더라서 ': '따라서 ',
    '우선변제권인찬 안은 아찬권등가명 령의 괴행에 따 言% 권 등기를 上] 차면% 조%=항에띠른 J 선변 제권을취득한다.': '우선변제권\n- 임차인은 임차권등기명령의 집행에 따른 임차권등기를 마치면 제3조 제1항에 따른 우선변제권을 취득한다.',
    '0 임차권': '① 임차권',
    '©「전차인」': '② 「전차인」',
    '[예 외-': '[예외 - ',
    '원칙이 채권양수인이': '원칙: 채권양수인이'
}

for old, new in replacements.items():
    text = text.replace(old, new)

lines = text.split('\n')
new_lines = []
merge_flag = False

for i, line in enumerate(lines):
    # 2. 시작 노이즈 제거
    line = re.sub(r'^[ \t]*(?:i WM|!|어 \[|引\]|O|©|⑦|⑧|⑨|■)\s*', '', line)
    
    # 3. 리스트 불릿 교정
    line = re.sub(r'^[ \t]*•\s*', '- ', line)

    # 4. 줄바꿈 병합 (merge_flag)
    if merge_flag and new_lines:
        if line.startswith('- ') or line.startswith('#') or line.startswith('>') or not line.strip():
            # 다음 줄이 독립된 문단이면 병합 취소
            merge_flag = False
            pass # 그냥 넘어가서 아래에서 append 되게 함
        else:
            # 병합
            new_lines[-1] = new_lines[-1] + ' ' + line.strip()
            line = new_lines[-1]
            new_lines.pop() # 대체하기 위해 임시 제거, 아래에서 다시 append 됨
    
    stripped = line.strip()
    
    # 이번 줄이 병합 대상인지 확인
    if stripped and not stripped.startswith('#') and not stripped.startswith('>'):
        # 종결부호로 끝나지 않으면 다음 줄과 병합 예약
        if not re.search(r'[.?!\])>"\'\]\)~]$', stripped):
            merge_flag = True
        else:
            merge_flag = False
    else:
        merge_flag = False

    new_lines.append(line)

# 5. 판례 래핑 (관련 판례 단락을 블록인용으로 변경)
final_lines = []
for line in new_lines:
    # 대판 XXXX.X.X. [[...]] 형태가 포함된 긴 줄글이고, 이미 인용구나 제목이 아닌 경우
    if re.search(r'대판 \d{4}\.\d{1,2}\.\d{1,2}\.', line) and '[[20' in line and not line.startswith('> ') and not line.startswith('#'):
        # 특정 키워드가 있거나 문장 전체가 판례 위주인 경우 콜아웃 적용
        if "주택임대차보호법에 정한 대항력과" in line or "원칙: 채권양수인이" in line or "이러한 경우" in line:
            # 리스트 기호가 있으면 유지하면서 래핑
            if line.startswith('- '):
                line = "- > [!판례] 관련 판례\n  > " + line[2:].replace('. ', '.\n  > ')
            else:
                line = "> [!판례] 관련 판례\n> " + line.replace('. ', '.\n> ')

    final_lines.append(line)

with open(filepath + '.reflowed', 'w', encoding='utf-8') as f:
    f.write('\n'.join(final_lines))

print("Reflow completed. Saved to .reflowed file for inspection.")
