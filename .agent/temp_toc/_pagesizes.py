# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pypdf import PdfReader, PdfWriter
import io as _io
src = 'H:/내 드라이브/작업용/강성민헌법OX/강성민_헌법_최종정리_OX_총론_통치구조.pdf'
r = PdfReader(src)
N = len(r.pages)

def range_bytes(a, b):
    w = PdfWriter()
    for p in range(a, b + 1):
        w.add_page(r.pages[p - 1])
    buf = _io.BytesIO()
    w.write(buf)
    return len(buf.getvalue())

ranges = {
    'edit1_chong(p1-116)': (1, 116),
    'edit2_tongchi(p117-240)': (117, 240),
    # finer for 편1
    'A_jang1+jang2a(p1-65)': (1, 65),
    'B_jang2b(p66-116)': (66, 116),
    # finer for 편2
    'C_gukhoe(p117-187)': (117, 187),
    'D_daetong+beob(p188-240)': (188, 240),
}
total = os.path.getsize(src)
print('FILE total bytes', total, round(total/1024/1024,1), 'MB', 'pages', N)
print('MB per page (file/N):', round(total/1024/1024/N, 4))
for k,(a,b) in ranges.items():
    bts = range_bytes(a,b)
    print(f'{k}\tp{a}-{b}\t{b-a+1}p\t{round(bts/1024/1024,1)}MB')
