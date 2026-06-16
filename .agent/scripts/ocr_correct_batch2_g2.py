"""
OCR 교정 스크립트 — batch2 그룹 2 (132개 청크)
윤동환_민법의맥 OCR 청크 교정
"""
import os, re, json, sys

INPUT_BASE = 'H:/내 드라이브'
OUTPUT_BASE = 'H:/내 드라이브/.agent/data/ocr_chunks_reviewed'

def correct_ocr(text):
    """OCR 교정 — 판례번호·조문·마커는 절대 건드리지 않음"""
    lines = text.split('\n')
    result_lines = []
    for line in lines:
        # 보호 구역: chunk_meta, 페이지 마커는 그대로
        if (line.strip().startswith('<!-- chunk_meta:') or
                line.strip().startswith('<!-- p.')):
            result_lines.append(line)
            continue

        c = line

        # ── 判例 오인식 패턴 ──
        c = re.sub(r'判f\w+J\s*는', '判例는', c)
        c = re.sub(r'判f\w+[lJj]+', '判例', c)
        c = re.sub(r'判\{f[ilj]+[lJj]+\}', '判例', c)
        c = re.sub(r'判\{fl[jl]\}', '判例', c)
        c = re.sub(r'判\{f[il][lj]\}', '判例', c)
        c = re.sub(r'判i71j', '判例', c)
        c = re.sub(r'判i\w+j', '判例', c)
        c = re.sub(r'判竹Il', '判例', c)
        c = re.sub(r'判伊\|l', '判例', c)
        c = re.sub(r'判\{fl?hj\}', '判例', c)
        c = re.sub(r'判\{[fF][lij]+[lJj]\}', '判例', c)
        c = re.sub(r'判\{外l?', '判例', c)
        c = re.sub(r'判例l\b', '判例', c)

        # ── 대판/대결 오인식 ──
        c = re.sub(r'대떤\s+', '대판 ', c)
        c = re.sub(r'대떤\(', '대판(', c)
        c = re.sub(r'대딴\s+', '대판 ', c)
        c = re.sub(r'대딴\(', '대판(', c)
        c = re.sub(r'대판\s+2CXE\.', '대판 2005.', c)
        c = re.sub(r'대판\s+2CXl\.', '대판 2001.', c)
        c = re.sub(r'대판\s+2CXl3\.', '대판 2003.', c)
        c = re.sub(r'대판\s+2CX\)\.', '대판 2000.', c)
        c = re.sub(r'대판\s+199:3\.', '대판 1993.', c)
        c = re.sub(r'대판\s+199:(\d)\.', lambda m: f'대판 199{m.group(1)}.', c)
        c = re.sub(r'대판\s+1007\.', '대판 1997.', c)
        c = re.sub(r'대판\s+1OO7\.', '대판 1997.', c)
        c = re.sub(r'대판\s+1OO\d\.', lambda m: m.group(0).replace('OO', '00'), c)
        c = re.sub(r'대딴\s+2CX\)\.1\.30\.\s*2CX[0-9l]3다', '대판 2000.1.30. 2003다', c)

        # ── 로마 숫자 오인식 ──
        c = re.sub(r'(?<!\w)m\. (?=[가-힣A-Z\d])', 'III. ', c)
        c = re.sub(r'(?<!\w)w\. (?=[가-힣A-Z\d])', 'IV. ', c)

        # ── 天→친권 오인식 ──
        c = c.replace('천권자', '친권자')
        c = c.replace('천권의', '친권의')
        c = c.replace('천권을', '친권을')
        c = c.replace('천권이', '친권이')
        c = c.replace('천권에', '친권에')
        c = c.replace('천권행사', '친권행사')
        c = c.replace('천권남용', '친권남용')
        c = re.sub(r'천권(?=\s)', '친권', c)

        # ── 대리안 → 대리인 ──
        c = c.replace('대리안이', '대리인이')
        c = c.replace('대리안의', '대리인의')
        c = c.replace('대리안들', '대리인들')
        c = c.replace('대리안에게', '대리인에게')
        c = c.replace('대리안은', '대리인은')
        c = c.replace('대리안을', '대리인을')
        c = c.replace('대리안과', '대리인과')
        c = c.replace('대리안으로', '대리인으로')

        # ── 흐→공 오인식 ──
        c = c.replace('흐무원', '공무원')

        # ── 어미·조사 오인식 ──
        c = c.replace('아니댜죽', '아니다. 즉')
        c = c.replace('있댜죽', '있다. 즉')
        c = c.replace('된댜죽', '된다. 즉')
        # 판례번호 내부 댜 → 다 (예: 94댜3:345 → 94다33345)
        c = re.sub(r'(\d{2,4})댜(\d)', r'\1다\2', c)
        # 판례번호 내부 :3 → 33 (OCR 오인식)
        c = re.sub(r'다(\d*):(\d)', lambda m: '다' + m.group(1) + m.group(2) + m.group(2) if m.group(1) else '다' + m.group(2) + m.group(2), c)
        # 댜 → 다 (어미로 사용된 경우)
        # 패턴1: 댜 뒤에 문장부호/공백/특수문자
        c = re.sub(r'댜([.。,\s\(\)\[\]#*\'\"]|$)', lambda m: '다' + m.group(1), c)
        # 패턴2: 댜 뒤에 바로 한국어 (두 문장 이어붙임) — 문맥 연결어 앞에 줄바꿈 삽입
        c = re.sub(r'댜(관련판례)', r'다\n\n\1', c)
        c = re.sub(r'댜(비교판례)', r'다\n\n\1', c)
        c = re.sub(r'댜(그 후\s)', r'다 \1', c)
        c = re.sub(r'댜(그러나\s)', r'다. \1', c)
        c = re.sub(r'댜(따라서\s)', r'다. \1', c)
        c = re.sub(r'댜(이 때)', r'다. \1', c)
        c = re.sub(r'댜(이경우)', r'다. 이 경우', c)
        c = re.sub(r'댜(즉\s)', r'다. 즉 ', c)
        c = re.sub(r'댜(즉[가-힣])', lambda m: '다. 즉 ' + m.group(1)[1:], c)
        c = re.sub(r'댜(나\))', r'다. \1', c)
        c = re.sub(r'댜(라\))', r'다. \1', c)
        c = re.sub(r'댜(제\d+관)', r'다.\n\n\1', c)
        c = re.sub(r'댜(I+\s)', r'다.\n\n\1', c)
        # 나머지 댜+한국어 — 단순히 '다 ' 로 처리 (띄어쓰기 추가)
        c = re.sub(r'댜([가-힣])', r'다 \1', c)

        # ── 의미 오인식 ──
        c = c.replace('의마를', '의미를')
        c = c.replace('의마가', '의미가')
        c = c.replace('의마는', '의미는')
        c = c.replace('의마에', '의미에')
        c = c.replace('의마로', '의미로')

        # ── 접→점 오인식 ──
        c = c.replace('이라는 접을 들어', '이라는 점을 들어')
        c = c.replace('이라는접을 들어', '이라는 점을 들어')
        c = re.sub(r'\b접을 들어\b', '점을 들어', c)

        # ── 수 있다/없다 붙어쓰기 ──
        c = re.sub(r'수있다', '수 있다', c)
        c = re.sub(r'수없다', '수 없다', c)
        c = re.sub(r'수있고', '수 있고', c)
        c = re.sub(r'수없고', '수 없고', c)
        c = re.sub(r'수있으나', '수 있으나', c)
        c = re.sub(r'수없으나', '수 없으나', c)
        c = re.sub(r'수있으며', '수 있으며', c)
        c = re.sub(r'수없으며', '수 없으며', c)
        c = re.sub(r'수있는', '수 있는', c)
        c = re.sub(r'수없는', '수 없는', c)

        # ── 기타 붙어쓰기 복원 ──
        c = re.sub(r'것은아니', '것은 아니', c)
        c = re.sub(r'것이아니', '것이 아니', c)
        c = re.sub(r'([다나])고한다', r'\1고 한다', c)
        c = re.sub(r'([다나])고한', r'\1고 한', c)
        c = re.sub(r'취소된경우', '취소된 경우', c)
        c = re.sub(r'성립할경우', '성립할 경우', c)
        c = re.sub(r'인정되는경우', '인정되는 경우', c)
        # 대리인 보존 (이미 올바른 경우 변경 없음)

        # ── 오탈자 ──
        c = c.replace('본안과 대리인', '본인과 대리인')  # 구체 문맥
        c = c.replace('이름바', '이른바')
        c = c.replace('아해관계', '이해관계')
        c = c.replace('울을 수', '을 수')  # 주의: 특정 패턴
        c = re.sub(r'고壇[·•]\s*귀속', '과가 귀속', c)
        c = re.sub(r'고壇[·•]', '과가 ', c)
        c = c.replace('있다仁', '있다 (단')
        c = c.replace('EK아래', '다 (아래')
        c = c.replace('하였EK', '하였다')
        c = c.replace('수익을 을리는', '수익을 올리는')
        c = c.replace('가치믈 ', '가치를 ')
        c = c.replace('범위 내에서 한의사', '범위 내에서 한 의사')
        c = c.replace('재무의 일부를면제', '채무의 일부를 면제')
        c = re.sub(r'재무의 일부(?=를)', '채무의 일부', c)
        c = c.replace('선의. 무과실', '선의·무과실')
        c = re.sub(r'선의\.\s*무과실', '선의·무과실', c)

        # 섹션 번호 라인 끝 공백 정리
        c = re.sub(r'^([A-Z]-\d{3,4}[a-z]?)\s*$', r'\1', c)

        result_lines.append(c)

    return '\n'.join(result_lines)


def process_file(src_path, out_path):
    """파일 읽기 → 교정 → 쓰기. 변경 여부 반환."""
    with open(src_path, 'r', encoding='utf-8') as f:
        original = f.read()

    corrected = correct_ocr(original)
    changed = (corrected != original)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(corrected)

    return changed


def main():
    manifest_path = 'H:/내 드라이브/.agent/state/batch2_g2.json'
    with open(manifest_path, 'r', encoding='utf-8') as f:
        records = json.load(f)

    total = len(records)
    processed = 0
    skipped = 0
    modified = 0
    errors = []

    for i, rec in enumerate(records):
        chunk_path = rec['chunk_path'].replace('\\', '/')
        # chunk_path 예: .agent/data/ocr_chunks/민법/윤동환_민법의맥/파일.md
        # 출력 경로: ocr_chunks_reviewed/민법/윤동환_민법의맥/파일.md
        rel = chunk_path.replace('.agent/data/ocr_chunks/', '')
        src = INPUT_BASE + '/' + chunk_path
        out = OUTPUT_BASE + '/' + rel

        # 강제 재처리 (댜 패턴 추가 교정을 위해 기존 파일 덮어쓰기)
        # if os.path.exists(out):
        #     skipped += 1
        #     continue

        try:
            changed = process_file(src, out)
            processed += 1
            if changed:
                modified += 1
            if (i + 1) % 20 == 0:
                print(f'  [{i+1}/{total}] processed={processed} modified={modified}',
                      flush=True)
        except Exception as e:
            errors.append((chunk_path, str(e)))
            print(f'  ERROR {chunk_path}: {e}', file=sys.stderr)

    print(f'\n완료: 총 {total}개 중 처리={processed}, 건너뜀={skipped}, 수정됨={modified}')
    if errors:
        print(f'오류 {len(errors)}개:')
        for p, e in errors:
            print(f'  {p}: {e}')


if __name__ == '__main__':
    main()
