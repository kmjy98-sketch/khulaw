# -*- coding: utf-8 -*-
"""
_extract_godongseong_2026-06-12.py (일회성)
고동성/ 폴더의 수기(hwpx) + 찌라시(hwp/hwpx) → 텍스트 md 추출.
- .hwpx: zip+OWPML XML 파싱 (<hp:t> 단락 단위)
- .hwp:  hwp5txt(pyhwp) subprocess 폴백
출력: 고동성/_추출/{원본명}.md  (#15 원본 보존, 추출본만 신설)
"""
import re
import sys
import zlib
import zipfile
from pathlib import Path

import olefile

ROOT = Path("H:/내 드라이브/고동성")
OUT = ROOT / "_추출"
# .hwp 표 셀 텍스트는 hwp5txt가 누락 → HWP5 바이너리 PARA_TEXT 직접 파싱
CTRL_EXT = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}

ENT = {"&lt;": "<", "&gt;": ">", "&amp;": "&", "&quot;": '"', "&apos;": "'"}


def unescape(s: str) -> str:
    for k, v in ENT.items():
        s = s.replace(k, v)
    return s


def hwpx_text(path: Path) -> str:
    out = []
    with zipfile.ZipFile(path) as z:
        secs = sorted(n for n in z.namelist() if re.match(r"Contents/section\d+\.xml", n))
        if not secs:
            secs = sorted(n for n in z.namelist() if n.endswith(".xml") and "section" in n.lower())
        for n in secs:
            xml = z.read(n).decode("utf-8", "replace")
            for para in re.split(r"</hp:p>", xml):
                ts = re.findall(r"<hp:t[^>]*>(.*?)</hp:t>", para, re.S)
                if ts:
                    line = "".join(re.sub(r"<[^>]+>", "", t) for t in ts)
                    line = unescape(line).strip()
                    if line:
                        out.append(line)
    return "\n".join(out)


def _decode_para(b: bytes) -> str:
    out = []
    j = 0
    while j + 2 <= len(b):
        wc = int.from_bytes(b[j:j + 2], "little")
        if wc >= 32:
            out.append(chr(wc)); j += 2
        elif wc in (10, 13):
            out.append("\n"); j += 2
        elif wc in CTRL_EXT:
            j += 16  # 인라인 확장 컨트롤 = 8 WCHAR
        else:
            j += 2
    return "".join(out)


def _parse_section(data: bytes) -> str:
    t = []
    i, n = 0, len(data)
    while i + 4 <= n:
        h = int.from_bytes(data[i:i + 4], "little")
        tag = h & 0x3FF
        size = (h >> 20) & 0xFFF
        i += 4
        if size == 0xFFF:
            size = int.from_bytes(data[i:i + 4], "little"); i += 4
        p = data[i:i + size]
        i += size
        if tag == 67:  # HWPTAG_PARA_TEXT (표 셀 포함 모든 단락)
            t.append(_decode_para(p))
    return "\n".join(x for x in t if x.strip())


def hwp_text(path: Path) -> str:
    try:
        o = olefile.OleFileIO(str(path))
        hdr = o.openstream("FileHeader").read()
        comp = bool(hdr[36] & 1)
        secs = sorted(
            [e for e in o.listdir() if e and e[0] == "BodyText"],
            key=lambda e: int(re.sub(r"[^0-9]", "", e[-1]) or 0),
        )
        out = []
        for e in secs:
            raw = o.openstream(e).read()
            data = zlib.decompress(raw, -15) if comp else raw
            out.append(_parse_section(data))
        o.close()
        txt = "\n".join(out)
        return txt if txt.strip() else "__HWP_EMPTY__"
    except Exception as e:
        return f"__HWP_ERR__ {e}"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    files = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p.parent == OUT:
            continue
        if p.suffix.lower() in (".hwp", ".hwpx"):
            if only and only not in p.name:
                continue
            files.append(p)
    for p in files:
        try:
            txt = hwpx_text(p) if p.suffix.lower() == ".hwpx" else hwp_text(p)
        except Exception as e:
            txt = f"__EXTRACT_ERR__ {e}"
        status = "OK" if not txt.startswith("__") else txt[:40]
        n_ch = len(txt) if status == "OK" else 0
        if status == "OK":
            (OUT / (p.stem + ".md")).write_text(txt, encoding="utf-8")
        print(f"[{status:>18}] {n_ch:>7}자  {p.name}")
        if only and status == "OK":
            print("--- 샘플 (앞 600자) ---")
            print(txt[:600])


if __name__ == "__main__":
    main()
