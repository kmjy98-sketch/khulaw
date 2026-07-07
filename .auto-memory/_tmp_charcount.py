import re
p = r"H:/내 드라이브/outputs/01_ocr_llamaparse/김준호민총_llamaparse_p271-300.md"
txt = open(p, encoding="utf-8").read()
m = re.match(r"^---\n.*?\n---\n", txt, flags=re.S)
body = txt[m.end():] if m else txt
body = re.sub(r"<!--\s*p\.\d+\s*-->", "", body)

BACK = chr(92)  # backslash

def is_junk(s):
    return len(s) > 400 and s.count(BACK) > 30

def repl_junk(mtch):
    s = mtch.group(0)
    return " 제5조2항10조이하 " if is_junk(s) else s
body2 = re.sub(r"[$]{1,2}.*?[$]{1,2}", repl_junk, body, flags=re.S)

def latex_to_text(mm):
    s = mm.group(0).strip("$")
    s = re.sub(BACK + r"[a-zA-Z]+", " ", s)
    s = s.replace("{", " ").replace("}", " ").replace(BACK, " ")
    return s
body3 = re.sub(r"[$].*?[$]", latex_to_text, body2, flags=re.S)
body3 = re.sub(r"<[^>]+>", "", body3)

def cc(s): return len(re.sub(r"\s+", "", s))
print("LaTeX->text, junk-removed, HTML-stripped (no ws):", cc(body3))

body_floor = re.sub(r"[$]{1,2}.*?[$]{1,2}", "", body, flags=re.S)
body_floor = re.sub(r"<[^>]+>", "", body_floor)
print("conservative floor (all LaTeX removed):", cc(body_floor))

# raw, only HTML+page stripped, LaTeX kept as-is
raw = re.sub(r"<[^>]+>", "", body)
print("raw (LaTeX kept literally):", cc(raw))
