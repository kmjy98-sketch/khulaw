import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402
sys.stdout.reconfigure(encoding='utf-8')

base = vp("sync", "_교재원문", "민법", "윤동환_민법의맥")
files = sorted([f for f in os.listdir(base) if not f.startswith('_') and f.endswith('.md')])
target = files[:164]

# 판례 인용 독립 단락 탐색
# 「 기호 포함 줄에서 사건번호 패턴 확인
print("=== 판례 인용 줄 앞 글자 분석 ===")
quote_start = {}
for fn in target:
    path = os.path.join(base, fn)
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        s = line.strip()
        # 사건번호 패턴
        if re.search(r'\((?:대판|대결|헌재)\s+\d{4}', s):
            ch = s[0] if s else ''
            if ch not in quote_start:
                quote_start[ch] = 0
            quote_start[ch] += 1

# 빈도순 출력
print("판례 줄 첫 글자 빈도:")
for ch, cnt in sorted(quote_start.items(), key=lambda x: -x[1])[:20]:
    print(f"  '{ch}' ({ord(ch) if ch else 'empty'}): {cnt}회")

# 교재원문 본체 파일에서 구체적 패턴 확인
print("\n=== 물권A 파일 판례 줄 샘플 ===")
fn = '구분소유권_성립요건_물권A_윤동환_민법의맥.md'
path = os.path.join(base, fn)
with open(path, encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    s = line.strip()
    if re.search(r'\((?:대판|대결|헌재)\s+\d{4}', s) and len(s) > 50:
        prev = lines[i-1].strip() if i > 0 else ''
        print(f"L{i+1}[prev='{prev[:20]}']: {repr(s[:120])}")
        if i > 30:
            break
