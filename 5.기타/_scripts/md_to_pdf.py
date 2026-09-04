"""마크다운 풀이흐름 노트 -> PDF 변환 스크립트
fpdf2 + markdown 라이브러리 사용, 맑은 고딕 폰트
"""
import sys
import re
import markdown
from fpdf import FPDF

FONT_DIR = "C:/Windows/Fonts"

class KoreanPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        # 맑은 고딕 폰트 등록
        self.add_font('Malgun', '', f'{FONT_DIR}/malgun.ttf')
        self.add_font('Malgun', 'B', f'{FONT_DIR}/malgunbd.ttf')
        self.add_font('Malgun', 'I', f'{FONT_DIR}/malgunsl.ttf')  # 슬랜트를 이탤릭으로
        self.add_font('Malgun', 'BI', f'{FONT_DIR}/malgunbd.ttf')
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        if self.page_no() > 1:
            self.set_font('Malgun', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 5, self._header_text, align='C')
            self.ln(8)
            self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font('Malgun', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'- {self.page_no()} -', align='C')
        self.set_text_color(0, 0, 0)

    _header_text = ''


def clean_md(text):
    """마크다운 인라인 마크업 제거 (PDF 텍스트용)"""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\[\^[^\]]+\]', '', text)  # 각주 참조 제거
    text = re.sub(r'\[\[(.+?)\]\]', r'\1', text)  # wikilink -> plain
    return text.strip()


def parse_table(lines):
    """마크다운 테이블 파싱 -> list of rows (each row = list of cells)"""
    rows = []
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|')]
        # 앞뒤 빈 셀 제거
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]
        # 구분선 행 스킵
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        rows.append(cells)
    return rows


def render_table(pdf, rows):
    """테이블을 PDF에 렌더링"""
    if not rows:
        return

    num_cols = max(len(r) for r in rows)
    # 사용 가능 너비
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_w = avail_w / num_cols

    # 헤더
    if rows:
        pdf.set_font('Malgun', 'B', 8)
        pdf.set_x(pdf.l_margin)
        for cell in rows[0]:
            text = clean_md(cell)
            pdf.cell(col_w, 6, text, border=1, align='C')
        pdf.ln()

    # 본문 행
    pdf.set_font('Malgun', '', 8)
    for row in rows[1:]:
        max_h = 6
        # 각 셀의 높이 미리 계산
        cell_texts = []
        for i, cell in enumerate(row):
            text = clean_md(cell)
            cell_texts.append(text)
            # 텍스트 길이에 따라 높이 추정
            text_w = pdf.get_string_width(text)
            if text_w > col_w - 2:
                lines_needed = int(text_w / (col_w - 2)) + 1
                needed_h = 6 * lines_needed
                if needed_h > max_h:
                    max_h = needed_h

        x_start = pdf.l_margin
        y_start = pdf.get_y()

        # 페이지 넘김 체크
        if y_start + max_h > pdf.h - pdf.b_margin:
            pdf.add_page()
            y_start = pdf.get_y()
            x_start = pdf.l_margin

        for i, text in enumerate(cell_texts):
            x = x_start + i * col_w
            pdf.set_xy(x, y_start)
            pdf.multi_cell(col_w, 6, text, border=1, align='L')

        # 다음 행 위치
        pdf.set_xy(x_start, y_start + max_h)
    pdf.ln(2)


def render_md_to_pdf(md_text, output_path):
    """마크다운 텍스트를 PDF로 변환"""
    pdf = KoreanPDF()

    lines = md_text.split('\n')
    i = 0
    first_h1 = True
    in_code_block = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- frontmatter 스킵 ---
        if i == 0 and stripped == '---':
            i += 1
            while i < len(lines) and lines[i].strip() != '---':
                i += 1
            i += 1
            continue

        # --- 코드 블록 ---
        if stripped.startswith('```'):
            if not in_code_block:
                in_code_block = True
                i += 1
                code_lines = []
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # 닫는 ``` 스킵
                # 코드 블록 렌더링
                pdf.set_font('Malgun', '', 8)
                pdf.set_fill_color(240, 240, 240)
                for cl in code_lines:
                    text = cl.rstrip()
                    pdf.set_x(pdf.l_margin)
                pdf.cell(pdf.w - pdf.l_margin - pdf.r_margin, 5, f'  {text}', new_x="LMARGIN", new_y="NEXT", fill=True)
                pdf.set_fill_color(255, 255, 255)
                pdf.ln(2)
                in_code_block = False
                continue
            else:
                in_code_block = False
                i += 1
                continue

        # --- 빈 줄 ---
        if not stripped:
            i += 1
            continue

        # --- HTML 주석 스킵 ---
        if stripped.startswith('<!--'):
            while i < len(lines) and '-->' not in lines[i]:
                i += 1
            i += 1
            continue

        # --- 수평선 ---
        if re.match(r'^-{3,}$', stripped):
            pdf.ln(2)
            y = pdf.get_y()
            pdf.set_draw_color(200, 200, 200)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.set_draw_color(0, 0, 0)
            pdf.ln(4)
            i += 1
            continue

        # --- 헤더 ---
        h_match = re.match(r'^(#{1,4})\s+(.+)', stripped)
        if h_match:
            level = len(h_match.group(1))
            text = clean_md(h_match.group(2))

            if level == 1:
                if first_h1:
                    pdf.add_page()
                    pdf._header_text = text
                    first_h1 = False
                    pdf.set_font('Malgun', 'B', 18)
                    pdf.ln(10)
                    pdf.multi_cell(0, 10, text, align='C')
                    pdf.ln(8)
                else:
                    pdf.add_page()
                    pdf._header_text = text
                    pdf.set_font('Malgun', 'B', 16)
                    pdf.multi_cell(0, 9, text, align='L')
                    pdf.ln(4)
            elif level == 2:
                pdf.ln(4)
                pdf.set_font('Malgun', 'B', 13)
                pdf.set_fill_color(230, 240, 250)
                pdf.multi_cell(0, 8, text, fill=True)
                pdf.set_fill_color(255, 255, 255)
                pdf.ln(3)
            elif level == 3:
                pdf.ln(3)
                pdf.set_font('Malgun', 'B', 11)
                pdf.multi_cell(0, 7, text)
                pdf.ln(2)
            elif level == 4:
                pdf.ln(2)
                pdf.set_font('Malgun', 'B', 10)
                pdf.multi_cell(0, 6, text)
                pdf.ln(1)
            i += 1
            continue

        # --- 테이블 ---
        if stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            rows = parse_table(table_lines)
            render_table(pdf, rows)
            continue

        # --- 블록인용 ---
        if stripped.startswith('>'):
            pdf.set_font('Malgun', '', 9)
            pdf.set_text_color(60, 60, 60)
            quote_lines = []
            while i < len(lines) and (lines[i].strip().startswith('>') or (lines[i].strip() and quote_lines)):
                raw = lines[i].strip()
                if raw.startswith('>'):
                    raw = raw[1:].strip()
                    if raw.startswith('>'):
                        raw = raw[1:].strip()
                quote_lines.append(raw)
                i += 1
                # 빈줄이면 인용 종료
                if i < len(lines) and not lines[i].strip():
                    break

            # 인용 블록 렌더
            x_start = pdf.l_margin + 4
            pdf.set_draw_color(100, 150, 200)
            w_quote = pdf.w - pdf.r_margin - x_start
            if w_quote < 20:
                x_start = pdf.l_margin + 4
                w_quote = pdf.w - pdf.r_margin - x_start
            for ql in quote_lines:
                if not ql:
                    pdf.ln(2)
                    continue
                text = clean_md(ql)
                y = pdf.get_y()
                # 페이지 넘김 체크
                if y + 6 > pdf.h - pdf.b_margin:
                    pdf.add_page()
                    y = pdf.get_y()
                # 왼쪽 바
                pdf.line(pdf.l_margin + 1, y, pdf.l_margin + 1, y + 5)
                pdf.set_x(x_start)
                # 볼드 처리
                if text.startswith('**') or '**' in text[:20]:
                    pdf.set_font('Malgun', 'B', 9)
                else:
                    pdf.set_font('Malgun', '', 9)
                pdf.multi_cell(w_quote, 5, text)
                pdf.set_x(pdf.l_margin)

            pdf.set_draw_color(0, 0, 0)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
            continue

        # --- 리스트 항목 ---
        list_match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.+)', stripped)
        if list_match:
            indent = len(list_match.group(1)) // 2
            marker = list_match.group(2)
            text = clean_md(list_match.group(3))

            pdf.set_font('Malgun', '', 9)
            x_indent = pdf.l_margin + 4 + min(indent, 3) * 5
            w_avail = pdf.w - pdf.r_margin - x_indent
            if w_avail < 20:
                x_indent = pdf.l_margin + 4
                w_avail = pdf.w - pdf.r_margin - x_indent
            if re.match(r'\d+\.', marker):
                prefix = f'{marker} '
            else:
                prefix = '- '

            pdf.set_x(x_indent)
            pdf.multi_cell(w_avail, 5, f'{prefix}{text}')
            i += 1
            continue

        # --- 각주 정의 ---
        if stripped.startswith('[^'):
            pdf.set_font('Malgun', '', 7)
            pdf.set_text_color(100, 100, 100)
            pdf.set_x(pdf.l_margin)
            text = clean_md(stripped)
            fn_match = re.match(r'\[\^([^\]]+)\]:\s*(.*)', stripped)
            if fn_match:
                fn_id = fn_match.group(1)
                fn_text = clean_md(fn_match.group(2))
                pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 4, f'[{fn_id}] {fn_text}')
            else:
                pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 4, text)
            pdf.set_text_color(0, 0, 0)
            i += 1
            continue

        # --- 일반 텍스트 ---
        if not pdf.page:
            pdf.add_page()
        pdf.set_font('Malgun', '', 9)
        pdf.set_x(pdf.l_margin)
        text = clean_md(stripped)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 5, text)
        pdf.ln(1)
        i += 1

    pdf.output(output_path)
    return output_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python md_to_pdf.py <input.md> <output.pdf>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    result = render_md_to_pdf(md_text, output_path)
    print(f"PDF generated: {result}")


if __name__ == '__main__':
    main()
