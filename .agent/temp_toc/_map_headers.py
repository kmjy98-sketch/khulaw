# -*- coding: utf-8 -*-
import sys, io, os, re, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = 'H:/내 드라이브/outputs/01_ocr_llamaparse'
files = sorted(glob.glob(os.path.join(base, '강성민OX3_llamaparse_p*.md')))

# Build an ordered list of (pdf_page, line_text) merging page markers and headers
hdr_re = re.compile(r'^#+\s*(제\d+[편장절관항]|헌법총론|통치구조론|헌법총론론)')
# We want 편/장 level primarily; also 절 for big chapters
want_re = re.compile(r'(제\d+[편장]|헌법총론|통치구조론|^#+\s*제\d+절|^#+\s*제\d+항)')
pmark = re.compile(r'<!--\s*p\.(\d+)\s*-->')

cur_page = 0
results = []
for f in files:
    with open(f, encoding='utf-8') as fh:
        for line in fh:
            line = line.rstrip('\n')
            m = pmark.search(line)
            if m:
                cur_page = int(m.group(1))
                continue
            s = line.strip()
            if s.startswith('#'):
                txt = s.lstrip('#').strip()
                # classify level
                if re.match(r'^(헌법총론|통치구조론)$', txt):
                    results.append((cur_page, 'PART', txt))
                elif re.match(r'^제\d+편', txt):
                    results.append((cur_page, 'PART', txt))
                elif re.match(r'^제\d+장', txt):
                    results.append((cur_page, 'CHAP', txt))
                elif re.match(r'^제\d+절', txt):
                    results.append((cur_page, 'SEC', txt))
                elif re.match(r'^제\d+항', txt):
                    results.append((cur_page, 'SUB', txt))

for pg, lvl, txt in results:
    print(f'p{pg:03d}\t{lvl}\t{txt}')
