"""
OCR 오독 교정: 헌법 기출 유니온 마크다운
- 저1{digits}[.]{spaces}{조/항/호} → 제{digits}{조/항/호}
- 조으1{digits} → 조의{digits}
"""
import re
from pathlib import Path

src = Path(r"H:\내 드라이브\3.공법\10.이진_헌법원리1\유니온 마크다운\유니온_기출_법원_헌법재판소.md")

text = src.read_text(encoding='utf-8')
original = text

# Pass 1: 저1{digits}[.?][spaces]{조/항/호} → 제{digits}{조/항/호}
# 공백이 있는 경우(예: 저11 항)도 처리
pattern1 = r'저1(\d+)\.?\s*([조항호])'
matches1 = re.findall(pattern1, text)
text = re.sub(pattern1, r'제\1\2', text)

# Pass 2: 조으1{digits} → 조의{digits}  (예: 저1457조으12 → 제457조의2)
pattern2 = r'조으1(\d+)'
matches2 = re.findall(pattern2, text)
text = re.sub(pattern2, r'조의\1', text)

src.write_text(text, encoding='utf-8')

print(f"Pass 1 (저1→제): {len(matches1)}건")
for d, s in matches1:
    print(f"  저1{d}{s} → 제{d}{s}")
print(f"\nPass 2 (조으1→조의): {len(matches2)}건")
for d in matches2:
    print(f"  조으1{d} → 조의{d}")
print("\n완료.")
