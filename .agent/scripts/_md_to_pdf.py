"""민법1 중간 압축본 마크다운 → PDF 변환 스크립트"""
import re
from fpdf import FPDF

FONT_DIR = "C:/Windows/Fonts"
INPUT = "H:/내 드라이브/sync/1-1_중간/민법1_중간_압축본.md"
OUTPUT = "H:/내 드라이브/sync/1-1_중간/민법1_중간_압축본.pdf"


class MarkdownPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.add_font("malgun", "", f"{FONT_DIR}/malgun.ttf", uni=True)
        self.add_font("malgun", "B", f"{FONT_DIR}/malgunbd.ttf", uni=True)
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_margins(15, 15, 15)

    def header(self):
        pass

    def footer(self):
        self.set_y(-10)
        self.set_font("malgun", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"- {self.page_no()} -", align="C")

    def write_rich(self, text, size=9, bold=False, indent=0):
        """Write text with **bold** markdown support."""
        if indent:
            self.set_x(self.l_margin + indent)
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                self.set_font("malgun", "B", size)
                self.write(4.5, part[2:-2])
            else:
                if bold:
                    self.set_font("malgun", "B", size)
                else:
                    self.set_font("malgun", "", size)
                self.write(4.5, part)

    def add_heading(self, text, level):
        sizes = {1: 16, 2: 13, 3: 11}
        size = sizes.get(level, 10)
        self.ln(3 if level >= 3 else 5)
        self.set_font("malgun", "B", size)
        self.set_text_color(0, 0, 0)
        # strip markdown bold markers from headings
        clean = text.replace("**", "")
        self.multi_cell(0, size * 0.55, clean)
        if level <= 2:
            self.set_draw_color(80, 80, 80)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def add_table(self, rows):
        """Render a markdown table."""
        if len(rows) < 2:
            return
        header = rows[0]
        data_rows = rows[2:]  # skip separator row

        col_count = len(header)
        usable = self.w - self.l_margin - self.r_margin
        col_w = usable / col_count

        # Calculate column widths based on content
        col_widths = []
        for i in range(col_count):
            max_len = len(header[i].strip())
            for row in data_rows:
                if i < len(row):
                    cell_text = row[i].strip().replace("**", "")
                    max_len = max(max_len, len(cell_text))
            col_widths.append(max_len)

        total = sum(col_widths) if sum(col_widths) > 0 else 1
        col_widths = [w / total * usable for w in col_widths]
        # Cap any column at 60% of usable width
        for i in range(len(col_widths)):
            col_widths[i] = min(col_widths[i], usable * 0.6)
        # Redistribute
        remaining = usable - sum(col_widths)
        if remaining > 0:
            for i in range(len(col_widths)):
                col_widths[i] += remaining / len(col_widths)

        self.set_font("malgun", "B", 8)
        self.set_fill_color(230, 230, 230)
        self.set_draw_color(180, 180, 180)

        # Check if table fits on page
        estimated_height = (len(data_rows) + 1) * 6
        if self.get_y() + estimated_height > self.h - 20:
            self.add_page()

        # Header
        x_start = self.l_margin
        for i, cell in enumerate(header):
            w = col_widths[i] if i < len(col_widths) else col_w
            cell_text = cell.strip().replace("**", "")
            self.set_xy(x_start + sum(col_widths[:i]), self.get_y())
            self.cell(w, 6, cell_text, border=1, fill=True, align="C")
        self.ln()

        # Data rows
        self.set_font("malgun", "", 8)
        self.set_fill_color(255, 255, 255)
        for row in data_rows:
            row_y = self.get_y()
            if row_y + 6 > self.h - 20:
                self.add_page()
                row_y = self.get_y()

            max_h = 6
            cell_texts = []
            for i in range(col_count):
                cell_text = row[i].strip().replace("**", "") if i < len(row) else ""
                cell_texts.append(cell_text)
                # Estimate needed height
                w = col_widths[i] if i < len(col_widths) else col_w
                lines_needed = max(1, len(cell_text) * 2.2 / w + 1)
                needed_h = lines_needed * 4.2
                max_h = max(max_h, needed_h)
            max_h = min(max_h, 30)  # cap

            for i, cell_text in enumerate(cell_texts):
                w = col_widths[i] if i < len(col_widths) else col_w
                self.set_xy(x_start + sum(col_widths[:i]), row_y)
                # Check if bold markers in original
                orig = row[i].strip() if i < len(row) else ""
                if orig.startswith("**") and orig.endswith("**"):
                    self.set_font("malgun", "B", 8)
                else:
                    self.set_font("malgun", "", 8)
                self.multi_cell(w, 4.2, cell_text, border=1, align="L")
                bottom = self.get_y()
                # draw remaining border if multi_cell was shorter
            self.set_y(max(self.get_y(), row_y + 6))
        self.ln(2)

    def add_bullet(self, text, level=0):
        indent = 4 + level * 4
        self.set_x(self.l_margin + indent)
        self.set_font("malgun", "", 9)
        self.set_text_color(0, 0, 0)
        bullet = "\u2022 " if level == 0 else "\u25e6 "
        self.write(4.5, bullet)
        self.write_rich(text, size=9)
        self.ln(4.5)

    def add_blockquote(self, text):
        self.set_x(self.l_margin + 4)
        self.set_text_color(60, 60, 60)
        self.set_font("malgun", "", 8)
        # Draw left bar
        y = self.get_y()
        self.set_draw_color(180, 180, 200)
        self.set_line_width(0.5)
        self.line(self.l_margin + 2, y, self.l_margin + 2, y + 4)
        self.set_x(self.l_margin + 6)
        self.write_rich(text, size=8)
        self.ln(4.2)
        self.set_text_color(0, 0, 0)

    def add_plain_bold(self, text):
        """Bold line without bullet (e.g., **공방**: ...)"""
        self.set_font("malgun", "", 9)
        self.set_text_color(0, 0, 0)
        self.write_rich(text, size=9)
        self.ln(5)


def parse_table_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def is_separator(line):
    return bool(re.match(r'^\|[\s\-:|]+\|$', line.strip()))


def convert(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    pdf = MarkdownPDF()
    pdf.set_text_color(0, 0, 0)

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if stripped == "---":
            pdf.ln(2)
            i += 1
            continue

        # Headings
        m = re.match(r'^(#{1,3})\s+(.*)', stripped)
        if m:
            level = len(m.group(1))
            pdf.add_heading(m.group(2), level)
            i += 1
            continue

        # Table detection
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_line = lines[i].strip()
                if is_separator(row_line):
                    table_rows.append(None)  # separator marker
                else:
                    table_rows.append(parse_table_row(row_line))
                i += 1
            # Filter: keep header, separator marker, data
            clean_rows = []
            for r in table_rows:
                if r is None:
                    clean_rows.append("SEP")
                else:
                    clean_rows.append(r)
            # Reconstruct for add_table: [header, "SEP", data...]
            if len(clean_rows) >= 2:
                pdf.add_table(clean_rows)
            continue

        # Blockquote lines (> ...)
        if stripped.startswith(">"):
            text = stripped.lstrip(">").strip()
            if not text:
                i += 1
                continue
            pdf.add_blockquote(text)
            i += 1
            continue

        # Bullet points
        m = re.match(r'^(\s*)[-*]\s+(.*)', line)
        if m:
            indent_len = len(m.group(1))
            level = 1 if indent_len >= 2 else 0
            pdf.add_bullet(m.group(2), level)
            i += 1
            continue

        # Bold standalone line (like **공방**: ...)
        if stripped.startswith("**") or stripped.startswith("§"):
            pdf.add_plain_bold(stripped)
            i += 1
            continue

        # Regular text
        pdf.set_font("malgun", "", 9)
        pdf.write_rich(stripped, size=9)
        pdf.ln(5)
        i += 1

    pdf.output(output_path)
    print(f"PDF saved: {output_path}")
    print(f"Pages: {pdf.pages_count}")


if __name__ == "__main__":
    convert(INPUT, OUTPUT)
