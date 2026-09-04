# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pypdf import PdfReader, PdfWriter
src = 'H:/내 드라이브/작업용/강성민헌법OX/강성민_헌법_최종정리_OX_총론_통치구조.pdf'
outdir = 'H:/내 드라이브/.agent/temp_toc'
r = PdfReader(src)
N = len(r.pages)
def dump(name, pages):
    w = PdfWriter()
    for p in pages:
        if 1 <= p <= N:
            w.add_page(r.pages[p-1])
    out = os.path.join(outdir, name)
    with open(out, 'wb') as f:
        w.write(f)
    print('WROTE', name, len(w.pages))

dump('sm_front_p001-024.pdf', list(range(1, 25)))
print('DONE total', N)
