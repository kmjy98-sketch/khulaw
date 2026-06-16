#!/usr/bin/env python3
"""detc(헌법재판소 결정) API 구조 탐색."""
import sys
import requests
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

OC = 'km9752'
BASE = 'https://www.law.go.kr/DRF'


def probe_search(case_number: str):
    print(f'\n=== SEARCH detc query={case_number} ===')
    r = requests.get(f'{BASE}/lawSearch.do', params={
        'OC': OC, 'target': 'detc', 'type': 'XML',
        'query': case_number, 'display': 20, 'page': 1,
    }, timeout=30)
    print(f'status={r.status_code} len={len(r.text)}')
    root = ET.fromstring(r.text)
    total = root.findtext('.//totalCnt', '?')
    print(f'totalCnt={total}')
    # Detc 요소의 자식 태그 전부 출력
    for i, detc in enumerate(root.findall('.//Detc')):
        print(f'--- Detc[{i}] ---')
        for child in detc:
            txt = (child.text or '')[:80]
            print(f'  <{child.tag}> {txt!r}')
        if i >= 2:
            break


def probe_detail(doc_id: str):
    print(f'\n=== DETAIL detc ID={doc_id} ===')
    r = requests.get(f'{BASE}/lawService.do', params={
        'OC': OC, 'target': 'detc', 'type': 'XML', 'ID': doc_id,
    }, timeout=30)
    print(f'status={r.status_code} len={len(r.text)}')
    root = ET.fromstring(r.text)
    # 루트 자식 전부
    def walk(node, depth=0):
        tag = node.tag
        txt = (node.text or '').strip()[:120]
        if txt or not list(node):
            print('  ' * depth + f'<{tag}> {txt!r}')
        else:
            print('  ' * depth + f'<{tag}>')
        for child in node:
            walk(child, depth + 1)

    walk(root)


if __name__ == '__main__':
    probe_search('2009헌바120')
    # 검색 결과에서 id를 직접 뽑아 상세 조회
    r = requests.get(f'{BASE}/lawSearch.do', params={
        'OC': OC, 'target': 'detc', 'type': 'XML',
        'query': '2009헌바120', 'display': 5, 'page': 1,
    }, timeout=30)
    root = ET.fromstring(r.text)
    detc = root.find('.//Detc')
    if detc is not None:
        doc_id = detc.findtext('결정일련번호') or detc.findtext('헌재결정례일련번호') or None
        if not doc_id:
            # 태그명 모르니 id 속성이나 첫 자식 탐색
            for child in detc:
                if '일련번호' in child.tag or 'id' in child.tag.lower():
                    doc_id = child.text
                    break
        print(f'\nExtracted doc_id: {doc_id}')
        if doc_id:
            probe_detail(doc_id)
