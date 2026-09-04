"""HUFS 주간 메뉴 HTML(부분 응답 2개) → 통합 마크다운 + standalone HTML."""
from __future__ import annotations
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
PARTS = [ROOT / "_hufs_apr.html", ROOT / "_hufs_may.html"]
OUT_MD = ROOT / "hufs-인문관.md"
OUT_HTML = ROOT / "hufs-인문관.html"

WEEK_LABEL = ["(일)", "(월)", "(화)", "(수)", "(목)", "(금)", "(토)"]


def strip_html(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
           .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return s.strip()


def parse_cell(cell_html: str) -> str:
    if re.search(r"\bno-menu\b", cell_html, re.I):
        return "—"
    items = []
    for m in re.finditer(r"<li\b[^>]*>([\s\S]*?)</li>", cell_html, re.I):
        t = strip_html(m.group(1)).strip()
        if t and t.strip() != "":
            items.append(t)
    cal = re.search(r'<p[^>]*\bclass="calorie"[^>]*>([\s\S]*?)</p>', cell_html, re.I)
    pay = re.search(r'<p[^>]*\bclass="pay"[^>]*>([\s\S]*?)</p>', cell_html, re.I)
    extras = []
    if cal:
        extras.append(f"[{strip_html(cal.group(1))}]")
    if pay:
        extras.append(strip_html(pay.group(1)))
    body = "\n".join(items)
    if extras:
        body = (body + ("\n" if body else "") + "\n".join(extras)).strip()
    return body or "—"


def parse_part(html: str):
    """Return (dates, {meal_label: {date_iso: cell_text}})."""
    h = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    dates = []
    for m in re.finditer(r'<span[^>]*\bclass="date"[^>]*\bid="date_(\d{4}-\d{2}-\d{2})"', h):
        dates.append(m.group(1))
    meals = {}
    for tr in re.finditer(r"<tr\b[^>]*>([\s\S]*?)</tr>", h, re.I):
        row = tr.group(1)
        if "<th" not in row:
            continue
        th = re.search(r"<th\b[^>]*>([\s\S]*?)</th>", row, re.I)
        if not th:
            continue
        meal_raw = strip_html(th.group(1))
        # "조식\n(08:00\n ~ \n10:00)" → "조식 (08:00~10:00)"
        meal = re.sub(r"\s+", " ", meal_raw).strip()
        meal = re.sub(r"\(\s*(\d{1,2}:\d{2})\s*~\s*(\d{1,2}:\d{2})\s*\)", r"(\1~\2)", meal)
        if not re.search(r"조식|중식|석식|점심|저녁|아침|간식", meal):
            continue
        cells = []
        for td in re.finditer(r"<td\b[^>]*>([\s\S]*?)</td>", row, re.I):
            cells.append(parse_cell(td.group(1)))
        if len(cells) == len(dates):
            meals[meal] = {d: cells[i] for i, d in enumerate(dates)}
        else:
            # 길이 mismatch — 보수적으로 0번째부터 채움
            slot = {}
            for i, d in enumerate(dates):
                slot[d] = cells[i] if i < len(cells) else "—"
            meals[meal] = slot
    return dates, meals


def merge_parts(parts):
    all_dates = []
    seen = set()
    merged_meals: dict[str, dict[str, str]] = {}
    meal_order: list[str] = []
    for dates, meals in parts:
        for d in dates:
            if d not in seen:
                seen.add(d)
                all_dates.append(d)
        for meal, cells in meals.items():
            if meal not in merged_meals:
                merged_meals[meal] = {}
                meal_order.append(meal)
            merged_meals[meal].update(cells)
    all_dates.sort()
    return all_dates, meal_order, merged_meals


def date_header(iso: str) -> str:
    y, mo, d = (int(x) for x in iso.split("-"))
    dow = WEEK_LABEL[date(y, mo, d).weekday() if False else date(y, mo, d).isoweekday() % 7]
    # Python isoweekday: Mon=1..Sun=7; we want Sun=0..Sat=6
    return f"{mo:02d}/{d:02d} {dow}"


def to_markdown(dates, meal_order, meals) -> str:
    headers = ["요일/메뉴"] + [date_header(d) for d in dates]
    lines = ["# 한국외대 인문관 식당 주간 메뉴",
             f"기간: {dates[0]} ~ {dates[-1]}",
             "출처: https://www.hufs.ac.kr/hufs/11318/subview.do",
             "",
             "| " + " | ".join(headers) + " |",
             "|" + "|".join([" --- "] * len(headers)) + "|"]
    for meal in meal_order:
        cells = [meal]
        for d in dates:
            raw = meals[meal].get(d, "—")
            # 표 셀에 줄바꿈을 <br>로
            cell = raw.replace("|", "\\|").replace("\n", "<br>")
            cells.append(cell or "—")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def to_html(dates, meal_order, meals) -> str:
    headers = ["요일/메뉴"] + [date_header(d) for d in dates]
    rows_html = []
    for meal in meal_order:
        tds = [f"<th class='meal'>{meal}</th>"]
        for d in dates:
            raw = meals[meal].get(d, "—")
            cell = (raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                       .replace("\n", "<br>"))
            tds.append(f"<td>{cell}</td>")
        rows_html.append("<tr>" + "".join(tds) + "</tr>")
    th_row = "".join(f"<th>{h}</th>" for h in headers)
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>한국외대 인문관 식당 주간 메뉴 ({dates[0]} ~ {dates[-1]})</title>
<style>
body {{ font-family: 'Malgun Gothic','Apple SD Gothic Neo',sans-serif; padding: 20px; color:#222; }}
h1 {{ font-size: 18pt; margin-bottom: 4px; }}
.meta {{ color:#666; margin-bottom: 16px; font-size: 10pt; }}
table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
th, td {{ border: 1px solid #ccc; padding: 8px 10px; vertical-align: top; font-size: 10pt; line-height: 1.45; }}
thead th {{ background:#fde68a; }}
th.meal {{ background:#fff7ed; width: 110px; text-align:center; }}
td {{ word-break: keep-all; }}
</style></head><body>
<h1>한국외대 인문관 식당 주간 메뉴</h1>
<div class="meta">기간: {dates[0]} ~ {dates[-1]}<br>출처: https://www.hufs.ac.kr/hufs/11318/subview.do</div>
<table><thead><tr>{th_row}</tr></thead><tbody>
{chr(10).join(rows_html)}
</tbody></table>
</body></html>
"""


def main():
    parts = []
    for p in PARTS:
        if not p.exists():
            continue
        parts.append(parse_part(p.read_text(encoding="utf-8")))
    dates, meal_order, meals = merge_parts(parts)
    OUT_MD.write_text(to_markdown(dates, meal_order, meals), encoding="utf-8")
    OUT_HTML.write_text(to_html(dates, meal_order, meals), encoding="utf-8")
    print(f"dates: {dates}")
    print(f"meals: {meal_order}")
    print(f"wrote: {OUT_MD.name}, {OUT_HTML.name}")


if __name__ == "__main__":
    main()
