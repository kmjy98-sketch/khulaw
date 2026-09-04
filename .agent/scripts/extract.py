# -*- coding: utf-8 -*-
import re
import os
import sys
_p = os.path.abspath(__file__)
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, 'scripts'))
from _vault import VAULT_ROOT, vp  # noqa: E402

kws = ['관습헌법', '합헌적', '명확성', '법률유보', '의회유보', '선거운동', '정당해산', '비례원칙', '주민투표', '지방자치', '공무원', '비밀선거', '평등선거', '신뢰보호', '직접선거']

with open(vp('5.기타', '_inbox', 'ox_temp.txt'), 'r', encoding='utf-8') as f:
    text = f.read()

# We can find questions by looking for patterns like \n[0-9]{3} or \nQ[0-9]{2} etc.
blocks = re.split(r'\n(?=[0-9OQoz]{3}\s)', text)
res = []

for block in blocks:
    if any(k in block for k in kws):
        res.append(block.strip())

with open(vp('5.기타', '_inbox', 'extracted_ox2.txt'), 'w', encoding='utf-8') as f:
    f.write('\n\n---\n\n'.join(res))
