"""
드라이런: 실제 파일 수정 없이 콜아웃 적용 결과 미리보기
"""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')

BASE = r'H:\내 드라이브\sync\_교재원문\민법\윤동환_민법의맥'
files = sorted([f for f in os.listdir(BASE) if not f.startswith('_') and f.endswith('.md')])
TARGET = files[:164]

ART_PATTERN = re.compile(
    r'^(\*\*제(\d+조(?:의\d+)?)\*\*\s*[\(（]([^)）]+)[\)）])\s*(.*)',
    re.DOTALL
)
REF_PATTERNS = [
    r'^에 의하지', r'^에 의한다\b', r'^를 따르', r'^로 보아',
    r'^에 따라\b', r'^에 의하여\b', r'^도 마찬가지',
    r'^가 적용', r'^는 적용', r'^에 해당', r'^에 근거', r'^의 법리'
]
PREC_PATTERN = re.compile(r'^「[^」]+」\s*\((?:대판|대결|헌재)[^)]+\)')

def is_ref_only(rest):
    if not rest.strip():
        return False
    return any(re.match(p, rest.strip()) for p in REF_PATTERNS)

def extract_yaml_end(lines):
    if not lines or lines[0].strip() != '---':
        return -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return i
    return -1

def simulate(content):
    lines = content.split('\n')
    yaml_end = extract_yaml_end(lines)
    art_count = 0
    prec_count = 0
    skip_count = 0
    art_title_only = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if i <= yaml_end:
            i += 1
            continue
        if line.startswith('>'):
            i += 1
            continue
        if PREC_PATTERN.match(stripped):
            prec_count += 1
            i += 1
            continue
        m = ART_PATTERN.match(stripped)
        if m:
            rest = m.group(4).strip()
            if is_ref_only(rest):
                skip_count += 1
                i += 1
                continue
            if rest:
                art_count += 1
                i += 1
            else:
                j = i + 1
                body_lines = []
                while j < len(lines):
                    nxt = lines[j].strip()
                    if nxt.startswith('- ①') or nxt.startswith('- ②') or \
                       nxt.startswith('- ③') or nxt.startswith('- ④') or \
                       nxt.startswith('- ⑤') or nxt.startswith('- ⑥'):
                        body_lines.append(nxt)
                        j += 1
                    elif body_lines and nxt.startswith('- '):
                        body_lines.append(nxt)
                        j += 1
                    else:
                        break
                if body_lines:
                    art_count += 1
                    art_title_only += 1
                    i = j
                else:
                    skip_count += 1
                    i += 1
            continue
        i += 1
    return art_count, prec_count, skip_count, art_title_only

total_art = 0
total_prec = 0
total_skip = 0
changed = 0

for fn in TARGET:
    path = os.path.join(BASE, fn)
    with open(path, encoding='utf-8') as f:
        content = f.read()

    art, prec, skip, title_only = simulate(content)
    total_art += art
    total_prec += prec
    total_skip += skip
    if art > 0 or prec > 0:
        changed += 1
        if fn in [
            '권리능력_대리의무_법인정관_3회_윤동환_민법의맥.md',
            '계약_성립요건_채각A_윤동환_민법의맥.md',
            '법정지상권_관습법_본3_윤동환_민법의맥.md',
        ]:
            print(f"[샘플] {fn}: 조문 {art}개 (제목only {title_only}), 판례 {prec}개, 건너뜀 {skip}개")

print()
print(f"변경 예정 파일: {changed}개")
print(f"적용 예정 [!조문]: {total_art}개")
print(f"적용 예정 [!판례]: {total_prec}개")
print(f"건너뜀 (단순 참조/본문 없음): {total_skip}개")

# 샘플 변환 결과 미리보기
print()
print("=== 변환 미리보기 ===")
from apply_callouts import apply_callouts

fn = '법정지상권_관습법_본3_윤동환_민법의맥.md'
path = os.path.join(BASE, fn)
with open(path, encoding='utf-8') as f:
    content = f.read()

new_content, art_cnt, prec_cnt = apply_callouts(content, fn)
lines_orig = content.split('\n')
lines_new = new_content.split('\n')

# 변경된 부분만 출력 (앞 100줄)
print(f"\n{fn}: {art_cnt}개 조문, {prec_cnt}개 판례 적용")
for i, (orig, new) in enumerate(zip(lines_orig[:300], lines_new[:350])):
    pass  # 길이 비교는 복잡하므로 단순 검색

# > [!조문] 줄 찾아서 주변 출력
for i, line in enumerate(lines_new):
    if '> [!조문]' in line:
        start = max(0, i-1)
        end = min(len(lines_new), i+4)
        print(f"\n--- L{i+1} 주변 ---")
        for j in range(start, end):
            print(f"  {repr(lines_new[j])[:100]}")
        break
