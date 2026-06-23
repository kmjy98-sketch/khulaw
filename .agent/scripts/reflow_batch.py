import os
import re
import sys
import shutil
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')

base_dir = vp('sync', '_교재원문')
WORKSPACE_ROOT = Path(VAULT_ROOT)

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
    ' 0 임차권': ' ① 임차권',
    ' ©「전차인」': ' ② 「전차인」',
    '[예 외-': '[예외 - ',
    '원칙이 채권양수인이': '원칙: 채권양수인이'
}

noise_pats = [
    re.compile(r'仰판|而판|대판\('),
    re.compile(r'^[ \t]*(?:i WM|!|어 \[|引\]|O|©|⑦|⑧|⑨|■)\s*')
]

processed_files = 0
skipped_files = 0
failed_link_check = 0

for root, dirs, files in os.walk(base_dir):
    for filename in files:
        if not filename.endswith('.md'):
            continue
            
        filepath = os.path.join(root, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                orig_text = f.read()
        except Exception as e:
            continue
            
        # 노이즈가 있는지 간단히 검사 (성능을 위해)
        has_noise = any(old in orig_text for old in replacements.keys())
        if not has_noise:
            for pat in noise_pats:
                if pat.search(orig_text):
                    has_noise = True
                    break
                    
        # 줄바꿈 병합이 필요한 경우가 있을 수 있으므로 무조건 시도하되,
        # 변경사항이 없으면 스킵하는 방식으로 진행
        text = orig_text
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

            # 4. 줄바꿈 병합 (마크다운 표 `|` 시작 줄은 보호)
            if merge_flag and new_lines:
                if (line.startswith('- ') or line.startswith('#')
                        or line.startswith('>') or line.lstrip().startswith('|')
                        or not line.strip()):
                    merge_flag = False
                    # 그대로 추가
                else:
                    new_lines[-1] = new_lines[-1] + ' ' + line.strip()
                    line = new_lines[-1]
                    new_lines.pop()

            stripped = line.strip()
            if (stripped and not stripped.startswith('#')
                    and not stripped.startswith('>')
                    and not stripped.startswith('|')):
                if not re.search(r'[.?!\])>"\'\]\)~]$', stripped):
                    merge_flag = True
                else:
                    merge_flag = False
            else:
                merge_flag = False

            new_lines.append(line)

        # 5. 판례 래핑
        final_lines = []
        for line in new_lines:
            if re.search(r'대판 \d{4}\.\d{1,2}\.\d{1,2}\.', line) and '[[20' in line and not line.startswith('> ') and not line.startswith('#'):
                if "주택임대차보호법에 정한 대항력과" in line or "원칙: 채권양수인이" in line or "이러한 경우" in line:
                    if line.startswith('- '):
                        line = "- > [!판례] 관련 판례\n  > " + line[2:].replace('. ', '.\n  > ')
                    else:
                        line = "> [!판례] 관련 판례\n> " + line.replace('. ', '.\n> ')

            final_lines.append(line)

        new_text = '\n'.join(final_lines)
        
        # 원본과 동일하면 스킵
        if orig_text == new_text:
            continue
            
        # 백링크 유실 검증 (매우 중요)
        orig_links = re.findall(r'\[\[.*?\]\]', orig_text)
        new_links = re.findall(r'\[\[.*?\]\]', new_text)
        
        if len(orig_links) != len(new_links):
            print(f"SKIPPED (Link count mismatch): {filename} (Orig: {len(orig_links)}, New: {len(new_links)})")
            failed_link_check += 1
            continue
            
        # 백업 (5.기타/교재원문_백업/{date}/reflow/{상대경로})
        try:
            rel = Path(filepath).relative_to(WORKSPACE_ROOT)
            backup = WORKSPACE_ROOT / "5.기타" / "교재원문_백업" / date.today().isoformat() / "reflow" / rel
        except ValueError:
            backup = WORKSPACE_ROOT / "5.기타" / "교재원문_백업" / date.today().isoformat() / "reflow" / filename
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(filepath, backup)

        # 안전하게 덮어쓰기
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_text)
            processed_files += 1
            print(f"PROCESSED: {filename}")
        except Exception as e:
            print(f"ERROR saving {filename}: {e}")

print("-" * 40)
print(f"Batch Processing Completed.")
print(f"Processed / Updated files : {processed_files}")
print(f"Failed link checks        : {failed_link_check}")
