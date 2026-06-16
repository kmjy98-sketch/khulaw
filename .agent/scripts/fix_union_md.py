"""
유니온 헌법 기출 마크다운 파일 정리 스크립트

처리 내용:
1. --- Page X --- 제거 (OCR 페이지 마커), 책 페이지 번호로 환산
2. I XXX 단독 행 제거 (책 페이지 인쇄 번호)
3. XX년 변호사시험 중복 연도표기 제거
4. 월첼 @ 구분자 제거
5. 홉 문 N 형식 → #### [YYYY년 변시 헌법 문N] 변환
6. 21-25 기출 헤더에 (XX년 변시, p.XXX) 추가
7. OCR 핵심 테마 라벨 패턴 정리

페이지 공식:
- 통치구조 파일: 책 페이지 = OCR 페이지 + 280
- 법원헌재 파일: 책 페이지 = OCR 페이지 + 404
"""

import re
import os


def process_file(input_path, base_page):
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    current_ocr_page = None
    result_lines = []
    skip_count = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ─── 1. --- Page X --- 제거, OCR 페이지 추적 ───
        page_match = re.match(r'^--- Page (\d+) ---$', stripped)
        if page_match:
            current_ocr_page = int(page_match.group(1))
            i += 1
            continue

        # ─── 2. I XXX 단독 행 제거 ───
        if re.match(r'^I \d+$', stripped):
            i += 1
            continue

        # ─── 3. XX년 변호사시험(시범) 단독 행 제거 ───
        if re.match(r'^\d{2}년 변호사시[험범]$', stripped):
            i += 1
            continue

        # ─── 4. 월첼 @ 구분자 제거 ───
        if stripped == '월첼 @':
            i += 1
            continue

        # ─── 5. 홉 문 N → 정규 헤더 변환 ───
        hob_match = re.match(r'^홉 문 (\d+)$', stripped)
        if hob_match:
            prob_num = hob_match.group(1)
            # 다음 줄 확인
            next_stripped = lines[i + 1].strip() if i + 1 < len(lines) else ''
            year_match = re.match(r'^(\d{2})년 변호사시[험범]$', next_stripped)
            if year_match:
                year_short = year_match.group(1)
                year_full = 2000 + int(year_short)
                book_page = (base_page + current_ocr_page) if current_ocr_page else None
                if 2021 <= year_full <= 2025 and book_page:
                    annotation = f' ({year_short}년 변시, p.{book_page})'
                else:
                    annotation = ''
                result_lines.append(f'#### [{year_full}년 변시 헌법 문{prob_num}]{annotation}')
                i += 2  # 헤더 + 연도 행 건너뜀
            else:
                # 연도 행 없는 경우 그냥 헤더로만
                result_lines.append(f'#### [?년 변시 헌법 문{prob_num}]')
                i += 1
            continue

        # ─── 6. #### [YYYY년 변시 헌법 문N] 헤더 처리 ───
        header_match = re.match(r'^(#{1,6})\s*\[(\d{4})년 변시 헌법 (문\d+)\](.*)', line)
        if header_match:
            prefix = header_match.group(1)
            year = int(header_match.group(2))
            problem = header_match.group(3)
            rest = header_match.group(4).strip()

            if 2021 <= year <= 2025 and current_ocr_page is not None:
                book_page = base_page + current_ocr_page
                year_short = str(year)[2:]
                annotation = f'({year_short}년 변시, p.{book_page})'
                new_line = f'{prefix} [{year}년 변시 헌법 {problem}] {annotation}'
                if rest:
                    new_line += f' {rest}'
            else:
                new_line = f'{prefix} [{year}년 변시 헌법 {problem}]'
                if rest:
                    new_line += f' {rest}'

            result_lines.append(new_line)

            # 다음 줄이 중복 연도 표기면 건너뜀
            if i + 1 < len(lines) and re.match(r'^\d{2}년 변호사시[험범]$', lines[i + 1].strip()):
                i += 2
            else:
                i += 1
            continue

        # ─── 7. OCR 핵심 테마 라벨 정리 ───
        line_fixed = line
        # lW뀔I...톨 패턴 → **[핵심]**
        line_fixed = re.sub(r'^lW뀔I\S*톨\s+', '**[핵심]** ', line_fixed)
        # ·m뼈l힘펌톨 패턴 → **[핵심]**
        line_fixed = re.sub(r'^·m뼈l힘펌톨\s+', '**[핵심]** ', line_fixed)
        # 숫자+댈톨 패턴 (예: 111댈톨) → **[핵심]**
        line_fixed = re.sub(r'^\d{2,3}댈톨\s+', '**[핵심]** ', line_fixed)
        # 홉 문 N (연도 없는 단독) — 이미 위에서 처리됨
        # 째 앞에 줄바꿈 패턴
        line_fixed = re.sub(r'^홉뼈\S*\s+', '**[핵심]** ', line_fixed)

        result_lines.append(line_fixed)
        i += 1

    with open(input_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(result_lines))

    print(f"  완료: {os.path.basename(input_path)}")
    print(f"  원본 줄 수: {len(lines)} → 처리 후: {len(result_lines)}")


if __name__ == '__main__':
    base_dir = r"H:\내 드라이브\3.공법\10.이진_헌법원리1\유니온 마크다운"

    print("=== 통치구조·국회·대통령 파일 처리 ===")
    process_file(
        os.path.join(base_dir, "유니온_기출_통치구조_국회_대통령.md"),
        base_page=280  # 책 페이지 = OCR 페이지 + 280
    )

    print("\n=== 법원·헌법재판소 파일 처리 ===")
    process_file(
        os.path.join(base_dir, "유니온_기출_법원_헌법재판소.md"),
        base_page=404  # 책 페이지 = OCR 페이지 + 404
    )

    print("\n=== 모두 완료 ===")
