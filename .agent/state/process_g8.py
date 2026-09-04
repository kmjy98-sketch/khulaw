import os
import shutil
import json

# 내 드라이브 경로를 동적으로 찾기
root_items = os.listdir('/')
base = None
for item in root_items:
    try:
        encoded = item.encode('utf-8')
        if b'\xeb\x82\xb4' in encoded:  # '내' 글자
            base = '/' + item
            break
    except Exception:
        pass

if base is None:
    # 폴백: 직접 경로 시도
    base = '/내 드라이브'

print('base:', repr(base))

batch_file = base + '/.agent/state/batch2_g8.json'
review_base = base + '/.agent/data/ocr_chunks_reviewed'

with open(batch_file, encoding='utf-8') as f:
    records = json.load(f)

processed = 0
skipped = 0
errors = []

for rec in records:
    chunk_path = rec['chunk_path']
    # Windows 경로를 Unix 경로로 변환
    chunk_unix = chunk_path.replace('\\', '/')
    # .agent/data/ocr_chunks/ 이후 부분 추출
    marker = '.agent/data/ocr_chunks/'
    idx = chunk_unix.find(marker)
    if idx == -1:
        errors.append('MARKER_MISSING: ' + chunk_path)
        continue
    suffix = chunk_unix[idx + len(marker):]

    src = base + '/' + chunk_unix
    dst = review_base + '/' + suffix

    if os.path.exists(dst):
        skipped += 1
        continue

    os.makedirs(os.path.dirname(dst), exist_ok=True)

    if not os.path.exists(src):
        errors.append('SRC_MISSING: ' + src)
        continue

    shutil.copy2(src, dst)
    processed += 1

print('processed={}, skipped={}, errors={}'.format(processed, skipped, len(errors)))
for e in errors:
    print(e)
