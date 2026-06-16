import os, fitz

OUT = r"H:/내 드라이브/.agent/temp_pdf_extract/songpic"
manifest = os.path.join(OUT, "manifest2.tsv")

def render(path, tag, pages, zoom):
    try:
        doc = fitz.open(path)
    except Exception as e:
        print(f"OPEN_FAIL\t{tag}\t{e}")
        return
    n = doc.page_count
    for pi in pages:
        if pi >= n:
            continue
        page = doc.load_page(pi)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        outp = os.path.join(OUT, f"{tag}_z_p{pi+1}.png")
        pix.save(outp)
        print(f"OK\t{tag}\tpages={n}\t{outp}")
    doc.close()

with open(manifest, encoding="utf-8") as f:
    for line in f:
        line=line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        tag, fn = line.split("\t")
        render(fn, tag, pages=(0,1), zoom=2.0)

# re-render high-zoom for the text-only small ones
render(r"H:/내 드라이브/1.민사/30.송영곤_기본민법/교재/(1-1)[송영곤_변호사]_2026_논점민강(12판)_보충자료(1)-26.1.11.pdf","bochung1_1",(0,),2.2)
render(r"H:/내 드라이브/1.민사/30.송영곤_기본민법/교재/논점민법강의_12판_보충자료1_26.pdf","bochung_root",(0,),2.2)
render(r"H:/내 드라이브/1.민사/30.송영곤_기본민법/교재/민법_목차_송영곤_기본강의_26_2.pdf","mokcha_song",(0,),2.2)
render(r"H:/내 드라이브/1.민사/30.송영곤_기본민법/교재/논점민법강의_채권관계1_p001-050_26.pdf","chaegwan1_split",(0,),1.6)
print("DONE")
