#!/usr/bin/env python3
"""민법 API 응답의 조문단위 구조 탐색."""
import sys
import requests
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

r = requests.get('https://www.law.go.kr/DRF/lawService.do', params={
    'OC': 'km9752', 'target': 'law', 'type': 'XML', 'ID': '001706',
}, timeout=60)
root = ET.fromstring(r.text)
units = root.findall('.//조문단위')
print(f'조문단위 total: {len(units)}')

# 제103조 찾아 구조 출력
for u in units:
    num = u.findtext('조문번호', '')
    if num == '103':
        print('\n=== 제103조 조문단위 구조 ===')
        for child in u:
            if list(child):
                print(f'<{child.tag}>')
                for gc in child:
                    txt = (gc.text or '').strip()[:120]
                    print(f'  <{gc.tag}> {txt!r}')
            else:
                txt = (child.text or '').strip()[:200]
                print(f'<{child.tag}> {txt!r}')
        break

# 첫 3개 조문의 조문번호/제목/내용 출력
print('\n=== 샘플: 첫 5개 조문 ===')
for u in units[:5]:
    num = u.findtext('조문번호', '')
    title = u.findtext('조문제목', '')
    content = (u.findtext('조문내용', '') or '').strip()[:120]
    print(f'조{num}조 [{title}] {content!r}')
