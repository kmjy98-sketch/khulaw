# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import fitz
src = 'H:/내 드라이브/작업용/강성민헌법OX/강성민_헌법_최종정리_OX_총론_통치구조.pdf'
outdir = 'H:/내 드라이브/.agent/temp_toc'
doc = fitz.open(src)
N = doc.page_count

def render(pageno, tag, zoom=2.0):
    # pageno is 1-based PDF internal index
    pg = doc.load_page(pageno - 1)
    mat = fitz.Matrix(zoom, zoom)
    pix = pg.get_pixmap(matrix=mat)
    out = os.path.join(outdir, f'sm_{tag}_p{pageno:03d}.png')
    pix.save(out)
    print('RENDER', out, pix.width, 'x', pix.height)

pages = [int(x) for x in sys.argv[1:]]
if not pages:
    pages = list(range(1, 13))
for p in pages:
    render(p, 'pg')
print('DONE total', N)
