#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR 교정 스크립트 — batch2 그룹 1 (132개 청크)
윤동환 민법의 맥 청크 OCR 교정
"""
import sys, os, json, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = VAULT_ROOT
os.chdir(BASE_DIR)

with open('.agent/state/batch2_g1.json', encoding='utf-8') as f:
    records = json.load(f)


def get_paths(chunk_path):
    """chunk_path → (원본 절대경로, 출력 절대경로)"""
    norm = chunk_path.replace('\\', '/')
    marker = 'ocr_chunks/'
    idx = norm.find(marker)
    if idx == -1:
        raise ValueError(f"ocr_chunks not found in: {chunk_path}")
    rel = norm[idx + len(marker):]  # 민법/윤동환_민법의맥/파일.md
    src = os.path.join(BASE_DIR, '.agent', 'data', 'ocr_chunks', *rel.split('/'))
    dst = os.path.join(BASE_DIR, '.agent', 'data', 'ocr_chunks_reviewed', *rel.split('/'))
    return src, dst


# ──────────────────────────────────────────────
# OCR 교정 패턴 (순서 중요)
# ──────────────────────────────────────────────

# 1) 판례 표시 오식 패턴 교정
#    한자/특수문자가 '(대판', '(판례)' 앞에 잘못 붙는 경우
#    예: 何판 → (대판), 仰판 → (대판), 佃판 → (대판), 住H판 → (대판)
#    예: 邙대판 → (대판), 邙판 → (판례)
#    단순히 앞에 특수문자가 붙은 '판'을 정규화

CORRECTIONS = [
    # ① 판례 표시 앞 한자/특수문자 제거: 何판, 仰판, 佃판, 住H판, 邙대판 등
    # "(대판"으로 시작해야 할 것이 특수문자 + "대판" or "판"으로 나오는 경우
    (re.compile(r'[何仰佃住邙见匚C宮苦]대판\b'), '(대판'),
    (re.compile(r'[何仰佃住邙见匚C宮苦]판\b'), '(대판'),
    (re.compile(r'住H판\b'), '(대판'),
    (re.compile(r'何판\s'), '(대판 '),
    (re.compile(r'仰판\s'), '(대판 '),
    (re.compile(r'佃판\s'), '(대판 '),
    (re.compile(r'住H판\s'), '(대판 '),
    (re.compile(r'邙대판\s'), '(대판 '),
    (re.compile(r'邙판\s'), '판례 '),

    # ② 判例 → 판례 (한자 오인식)
    (re.compile(r'判例'), '판례'),
    (re.compile(r'判[^][]'), lambda m: '판' + m.group(0)[1:]),

    # ③ 법원 로마자/특수문자 혼입 교정
    # "법법원" → "법원", "3 법원" 등은 건드리지 않음
    # "n. " 로 시작하는 번호 패턴 → "II."
    # 로마자 C-NN 패턴은 그대로 (레이아웃 마커)

    # ④ 연도.월.일 오식: 202al0.27 → 2020.10.27 형태로 정규화
    # 'a'가 숫자처럼 인식되는 OCR 오류: 202a → 202x 형태
    # 202al0 → 2020.10, 202a6 → 2020.6, 199a6 → 1990.6 등
    # 주의: 판례번호는 건드리지 않음 (사건번호는 '다', '나' 등으로 식별)
    (re.compile(r'\b(20[0-9])a(\d)\.'), lambda m: m.group(1) + '0.' + m.group(2) + '.'),
    (re.compile(r'\b(19[0-9])a(\d)\.'), lambda m: m.group(1) + '0.' + m.group(2) + '.'),

    # ⑤ 날짜 '.' 뒤에 숫자 'L'(대문자) 오식: 2014.102L → 2014.10.21
    (re.compile(r'(\d{4}\.\d{1,2})(\d)L\b'), lambda m: m.group(1) + '.' + m.group(2) + '1'),
    (re.compile(r'(\d{4}\.\d{1,2}\.)(\d)L\b'), lambda m: m.group(1) + m.group(2) + '1'),

    # ⑥ "한邙" / "한匚" / "한C" 처럼 '한' 뒤에 특수문자가 붙는 경우 → "한다"
    (re.compile(r'한邙'), '한다'),
    (re.compile(r'한匚卜'), '한다.'),   # 匚卜 = 다. 오인식
    (re.compile(r'한匚'), '한다'),
    (re.compile(r'한匸'), '한다'),
    (re.compile(r'한仁'), '한다'),
    (re.compile(r'한C\b'), '한다'),
    (re.compile(r'한卜'), '한다'),
    (re.compile(r'한니匚'), '한다'),

    # ⑦ "있邙" / "있匚" 등 → "있다"
    (re.compile(r'있邙'), '있다'),
    (re.compile(r'있匚'), '있다'),
    (re.compile(r'있匸'), '있다'),
    (re.compile(r'있C\b'), '있다'),

    # ⑧ "된邙" → "된다" 등
    (re.compile(r'된邙'), '된다'),
    (re.compile(r'된匚'), '된다'),

    # ⑨ "것이邙" → "것이다"
    (re.compile(r'것이邙'), '것이다'),
    (re.compile(r'것이匚'), '것이다'),

    # ⑩ "좋邙" / "옳邙" → "좋다" / "옳다"
    (re.compile(r'좋邙'), '좋다'),
    (re.compile(r'옳邙'), '옳다'),
    (re.compile(r'않邙'), '않다'),
    (re.compile(r'아니邙'), '아니다'),

    # ⑪ 문장 끝 특수문자 정리
    # 邙 뒤에 한글이 오는 경우 → "다(" : 邙 = 다(
    (re.compile(r'邙([가-힣(])'), r'다(\1'),
    # 邙 뒤에 공백/구두점이 오는 경우 → "다"
    (re.compile(r'邙([.,:;·\s\n])'), r'다\1'),
    # 匚 뒤에 한글이 오는 경우 → "다("
    (re.compile(r'匚([가-힣(])'), r'다(\1'),
    # 匚 뒤에 공백/구두점이 오는 경우 → "다"
    (re.compile(r'匚([.,:;·\s\n])'), r'다\1'),
    (re.compile(r'匸([.,:;·\s\n])'), r'다\1'),

    # ⑫ "C-" 레이아웃 마커는 건드리지 않음 (C-17, C-23 등)
    # 그 외 단독 C 오식은 조심 (false positive 위험)

    # ⑬ "^" 앞뒤로 나타나는 각주 오식 정리는 하지 않음 (구조 파괴 위험)

    # ⑭ "대결" 앞 특수문자
    (re.compile(r'何결\b'), '(대결'),
    (re.compile(r'邙대결\b'), '(대결'),

    # ⑮ 줄 선두의 "見" "见" → 내용에 따라 다르므로 건드리지 않음

    # ⑯ "오류어" 수정 (실제 확인된 것만)
    (re.compile(r'흐무원'), '공무원'),
    (re.compile(r'공뮤원'), '공무원'),
    (re.compile(r'가독노 차'), '가득 차'),

    # ⑰ "저し48조" → "제548조" 등 (특수문자 + 숫자)
    # "저し" → "제5" : し가 5를 오인식한 것
    (re.compile(r'저し(\d+)조'), lambda m: f'제5{m.group(1)}조'),
    # "저し" → "제" 뒤 숫자 2자리 이상인 경우도 처리
    (re.compile(r'저し(\d{3,})조'), lambda m: f'제{m.group(1)}조'),

    # ⑱ 판례참조 "다" 뒤 오식: "[[93다[^951]]" 형태는 건드리지 않음 (각주 ID와 혼동)
]


def correct_ocr(text: str) -> tuple:
    """OCR 교정 규칙 적용. 마커/메타는 건드리지 않음."""
    lines = text.split('\n')
    corrected_lines = []
    changed = False

    for line in lines:
        original_line = line

        # <!-- p.NNN --> 및 <!-- chunk_meta: ... --> 라인은 건드리지 않음
        if re.match(r'\s*<!--\s*(p\.\d+|chunk_meta)', line):
            corrected_lines.append(line)
            continue

        # YAML frontmatter 라인 (--- 사이)도 건드리지 않음
        # (frontmatter는 처음 몇 줄이므로 전체 텍스트로 처리하는 게 더 나음)
        # → 별도 처리 없이 패턴이 안 매칭되면 그대로 통과

        new_line = line

        for pat, repl in CORRECTIONS:
            if callable(repl):
                new_line = pat.sub(repl, new_line)
            else:
                new_line = pat.sub(repl, new_line)

        if new_line != original_line:
            changed = True
        corrected_lines.append(new_line)

    return '\n'.join(corrected_lines), changed


OVERWRITE = True  # True: 기존 파일 덮어쓰기, False: 건너뜀

def process_file(src, dst):
    """원본 읽기 → OCR 교정 → 출력 쓰기."""
    if os.path.exists(dst) and not OVERWRITE:
        return 'skip'

    if not os.path.exists(src):
        return f'src_missing: {src}'

    os.makedirs(os.path.dirname(dst), exist_ok=True)

    with open(src, encoding='utf-8') as f:
        text = f.read()

    corrected, changed = correct_ocr(text)

    with open(dst, 'w', encoding='utf-8') as f:
        f.write(corrected)

    return 'modified' if changed else 'copied'


# ──────────────────────────────────────────────
# 실행
# ──────────────────────────────────────────────
results = {'skip': 0, 'copied': 0, 'modified': 0, 'error': 0}
errors = []

for i, r in enumerate(records):
    try:
        src, dst = get_paths(r['chunk_path'])
        status = process_file(src, dst)
        if isinstance(status, str) and (status.startswith('src_missing') or status.startswith('error')):
            results['error'] += 1
            errors.append(f"[{i}] {status}")
        else:
            results[status] += 1
    except Exception as e:
        results['error'] += 1
        errors.append(f"[{i}] {r['chunk_path']}: {e}")

total = len(records)
print(f"=== 완료 ===")
print(f"총 {total}개 처리")
print(f"  건너뜀(이미 존재): {results['skip']}개")
print(f"  수정됨:            {results['modified']}개")
print(f"  원본 그대로 복사:  {results['copied']}개")
print(f"  오류:              {results['error']}개")

if errors:
    print("\n--- 오류 목록 ---")
    for e in errors:
        print(e)
