"""찌라시(8.*) 폴더의 hwp/hwpx 전부 → PDF (한컴 Office COM). 원위치에 .pdf 동반 생성.
"""
import sys
from pathlib import Path
import win32com.client as wc

sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"H:\내 드라이브")
base = next((p for p in R.iterdir() if p.is_dir() and p.name.startswith("8") and "찌라시" in p.name or (p.is_dir() and p.name.startswith("8") and any(x.suffix.lower() in (".hwp", ".hwpx") for x in p.rglob("*") if x.is_file()))), None)
if base is None:
    print("8.* 찌라시 폴더 못찾음"); sys.exit(1)
hwps = sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in (".hwp", ".hwpx"))
print(f"[{base.name}] hwp/hwpx {len(hwps)}개 변환 시작")

hwp = wc.gencache.EnsureDispatch("HWPFrame.HwpObject")
try:
    hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
except Exception as e:
    print("  (보안모듈 등록 실패, 계속):", e)

ok, skip, fail = 0, 0, []
for f in hwps:
    pdf = f.with_suffix(".pdf")
    if pdf.exists():
        skip += 1; continue
    try:
        hwp.Open(str(f), "", "forceopen:true")
        hwp.SaveAs(str(pdf), "PDF")
        hwp.Clear(1)
        ok += 1
        print("  [OK]", f.name)
    except Exception as e:
        fail.append(f.name)
        print("  [FAIL]", f.name, str(e)[:80])
try:
    hwp.Quit()
except Exception:
    pass
print(f"완료: 변환 {ok} / 스킵 {skip} / 실패 {len(fail)}")
if fail:
    print("실패목록:", fail)
