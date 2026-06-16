import sys, os, fitz

OUT = r"H:/내 드라이브/.agent/temp_pdf_extract/songpic"
os.makedirs(OUT, exist_ok=True)

def render(path, tag, pages=(0,1)):
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
        # modest zoom to keep image readable but small
        mat = fitz.Matrix(1.4, 1.4)
        pix = page.get_pixmap(matrix=mat)
        outp = os.path.join(OUT, f"{tag}_p{pi+1}.png")
        pix.save(outp)
        print(f"OK\t{tag}\tpages={n}\t{outp}")
    doc.close()

# tag -> filename
jobs = sys.argv[1:]
# jobs come as tag::::filename pairs via a manifest file
manifest = os.path.join(OUT, "manifest.tsv")
with open(manifest, encoding="utf-8") as f:
    for line in f:
        line=line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        tag, fn = line.split("\t")
        render(fn, tag)
print("DONE")
