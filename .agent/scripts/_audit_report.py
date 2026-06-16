import json, sys, io
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

d = json.load(open('_md_pdf_audit_result.json', 'r', encoding='utf-8'))

print('=== page_mismatch 27건 ===')
for x in d['page_mismatch']:
    print(f"{x['md']}")
    print(f"   PDF={x['pdf']}")
    print(f"   actual={x['actual_pages']}p | claim_last={x['claimed_last']} | diff=+{x['diff']} | via={x['match_via']}")

print()
print('=== explicit_pdf_missing 12건 ===')
for x in d['explicit_pdf_missing']:
    print(f"  {x['md']}")
    cp = x['claimed_pdf'].split('\n')[0][:120]
    print(f'      claimed: {cp}')

print()
print('=== no_frontmatter 140건 - 디렉터리별 분포 ===')
by_dir = defaultdict(int)
for p in d['no_frontmatter']:
    norm = p.replace('\\', '/')
    parent = '/'.join(norm.split('/')[:2])
    by_dir[parent] += 1
for k,v in sorted(by_dir.items(), key=lambda x:-x[1]):
    print(f'  {v:4d}  {k}')

print()
print('=== no_pdf_info 1178건 - 디렉터리별 분포 (top 15) ===')
by_dir2 = defaultdict(int)
for x in d['no_pdf_info']:
    norm = x['md'].replace('\\', '/')
    parent = '/'.join(norm.split('/')[:2])
    by_dir2[parent] += 1
for k,v in sorted(by_dir2.items(), key=lambda x:-x[1])[:15]:
    print(f'  {v:4d}  {k}')

print()
print('=== matched_ok 샘플 5건 ===')
for x in d['matched_ok_sample'][:5]:
    print(f"  {x['md']}")
    print(f"      -> PDF={x['pdf']} | actual={x['actual_pages']}p | claim_last={x['claimed_last']} | via={x['match_via']}")
