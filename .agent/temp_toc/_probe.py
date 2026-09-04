# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pypdf import PdfReader
p = r'H:\내 드라이브\작업용\강성민헌법OX\강성민_헌법_최종정리_OX_총론_통치구조.pdf'
r = PdfReader(p)
print('PAGES', len(r.pages))
# check embedded bookmarks/outline
try:
    ol = r.outline
    def walk(o, depth=0):
        for item in o:
            if isinstance(item, list):
                walk(item, depth+1)
            else:
                try:
                    pg = r.get_destination_page_number(item)
                except Exception:
                    pg = '?'
                print('OUTLINE', depth, (pg+1) if isinstance(pg,int) else pg, item.title)
    walk(ol)
except Exception as e:
    print('NO_OUTLINE', repr(e))
