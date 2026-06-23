#!/usr/bin/env python
"""OCR 추출 v3 — 엔진 교체형(easyocr / llamaparse), 2026-06-03

이관 설계: outputs/_OCR엔진이관연구.md 참조.
- 출력 md 계약은 local_easyocr_extract.py(v2)와 *동일* (프론트매터·`<!-- p.N -->`·파일명).
  따라서 다운스트림(교정·02-wiki·02-card)은 무변경.
- 엔진은 ENGINES 레지스트리에 함수로 등록. 새 엔진(upstage/gemini)은 함수 추가만.

엔진별 입력 단위:
- easyocr    : 페이지 이미지(page_image)  — 로컬, 무료, 자모혼동 있음(기준선)
- llamaparse : PDF(해당 페이지만 떼낸 임시 PDF 업로드) — 클라우드, 멀티모달

사용:
  python ocr_extract_v3.py --engine llamaparse --pdf <PDF> --out <DIR> --prefix <P> \
    --book "<책명>" --author "<저자>" --subject "<과목>" [--tier agentic] \
    [--chunk-size 30] [--start 1] [--end 0]

주의(#34): llamaparse 등 멀티모달은 흐릿한 사건번호/조문번호를 '그럴듯하게' 위조할 수 있음.
출력은 '미교정' 단계이며 korean-law-mcp 검증을 반드시 거친다.
"""
import os
import sys
import io
import time
import json
import argparse
import tempfile
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF — 렌더/이미지/페이지분리 전용 (텍스트레이어 사용 안 함)
from PIL import Image
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

try:  # .env 의 LLAMA_CLOUD_API_KEY 등 자동 로드
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(vp(".env"))
except Exception:
    pass


# ============================ 공통: 입력 어댑터 ============================

def page_image(page, doc, dpi=250):
    """페이지의 풀페이지 임베드 이미지(원해상도) 우선, 없으면 렌더. (v2와 동일)"""
    imgs = page.get_images(full=True)
    if imgs:
        big = max(imgs, key=lambda im: im[2] * im[3])
        if big[2] >= 1000 and big[3] >= 1400:
            base = doc.extract_image(big[0])
            return Image.open(io.BytesIO(base["image"])).convert("RGB")
    pix = page.get_pixmap(dpi=dpi)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def subset_pdf(doc, start, end) -> str:
    """start~end(1-based, 포함) 페이지만 떼낸 임시 PDF 경로 반환.
    클라우드 엔진에 전체 PDF를 올리지 않기 위함(크레딧 절약 + 페이지 매핑 단순화)."""
    nd = fitz.open()
    nd.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    nd.save(path)
    nd.close()
    return path


# ============================ 엔진: easyocr (기준선) ============================

_EASY_READER = None

def _easy_reader():
    global _EASY_READER
    if _EASY_READER is None:
        import easyocr
        print("[easyocr] 모델 로드(ko,en, CPU)...", flush=True)
        t0 = time.time()
        _EASY_READER = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
        print(f"[easyocr] 로드 완료 {time.time()-t0:.1f}s", flush=True)
    return _EASY_READER


def extract_easyocr(doc, start, end, **opt):
    """반환: [(page_no, text), ...]  (v2 readtext 경로 이식 — 기능 보존)"""
    reader = _easy_reader()
    out = []
    for i in range(start - 1, end):
        ts = time.time()
        img = page_image(doc[i], doc)
        res = reader.readtext(np.array(img), detail=0, paragraph=True)
        txt = "\n".join(res).strip()
        out.append((i + 1, txt))
        print(f"  p{i+1}: {len(txt)}자 {round(time.time()-ts,1)}s", flush=True)
    return out


# ============================ 엔진: llamaparse (클라우드) ============================

def extract_llamaparse(doc, start, end, tier="agentic", **opt):
    """LlamaParse v2 (llama-cloud SDK). 반환: [(page_no, markdown), ...]

    주의: 아래 SDK 호출/응답 구조는 공식 문서(getting_started, api-v2-guide) 패턴 기반이다.
    설치된 SDK 버전에 따라 result.markdown.pages 접근이 다를 수 있으므로 방어적으로 처리하고,
    --debug 시 raw 응답 타입을 출력한다(첫 실행에서 확정 권장)."""
    try:
        from llama_cloud import LlamaCloud
    except ImportError:
        raise SystemExit("llama-cloud 필요: pip install 'llama-cloud>=2.1'")
    api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise SystemExit("LLAMA_CLOUD_API_KEY 미설정 — .env 또는 환경변수에 키를 넣으세요.")

    sub = subset_pdf(doc, start, end)
    try:
        client = LlamaCloud(api_key=api_key)
        # parse()는 잡 생성+완료대기까지 수행하는 동기 메서드. upload_file로 직접 업로드.
        # tier: fast | cost_effective | agentic | agentic_plus
        parse_kwargs = dict(tier=tier, version="latest", expand=["markdown"])
        with open(sub, "rb") as fh:
            try:
                # 언어 힌트(processing_options 구조는 SDK 버전에 따라 다를 수 있어 실패 시 폴백)
                result = client.parsing.parse(
                    upload_file=fh,
                    processing_options={"ocr_parameters": {"languages": ["ko"]}},
                    **parse_kwargs,
                )
            except TypeError:
                fh.seek(0)
                result = client.parsing.parse(upload_file=fh, **parse_kwargs)
        if opt.get("debug"):
            print(f"[llamaparse:debug] result type={type(result)} "
                  f"attrs={[a for a in dir(result) if not a.startswith('_')][:25]}", flush=True)

        pages = _lp_pages(result)
        out = []
        for k, pg in enumerate(pages):
            md = _lp_page_md(pg)
            out.append((start + k, (md or "").strip()))
            print(f"  p{start+k}: {len(md or '')}자 (llamaparse)", flush=True)
        if not out:
            raise SystemExit("[llamaparse] 페이지 마크다운을 찾지 못함 — --debug 로 응답 구조 확인 필요.")
        return out
    finally:
        try:
            os.unlink(sub)
        except OSError:
            pass


def _lp_pages(result):
    """응답에서 페이지 리스트를 방어적으로 추출."""
    md = getattr(result, "markdown", None)
    if md is not None:
        pages = getattr(md, "pages", None)
        if pages is not None:
            return pages
        if isinstance(md, dict) and "pages" in md:
            return md["pages"]
    if isinstance(result, dict):
        return (result.get("markdown") or {}).get("pages") or result.get("pages") or []
    return getattr(result, "pages", []) or []


def _lp_page_md(pg):
    """페이지 객체에서 markdown 텍스트를 방어적으로 추출."""
    for attr in ("markdown", "md", "text"):
        v = getattr(pg, attr, None)
        if v:
            return v
    if isinstance(pg, dict):
        for key in ("markdown", "md", "text"):
            if pg.get(key):
                return pg[key]
    return ""


# ============================ 엔진 레지스트리 + 메타 ============================

ENGINES = {
    "easyocr": extract_easyocr,
    "llamaparse": extract_llamaparse,
}

def engine_meta(engine: str, tier: str = "agentic"):
    """프론트매터용 (추출엔진 라벨, 교정상태 주의문구)."""
    if engine == "easyocr":
        return ("easyocr-CPU(ko,en) [이미지 OCR]",
                "미교정 — 자모혼동(를/름·는/눈·을/올·훼/웨)·조문띄어쓰기 가능")
    if engine == "llamaparse":
        return (f"LlamaParse-v2(tier={tier}, lang=ko) [클라우드 멀티모달]",
                "미교정 — 멀티모달 OCR, anchor(사건·조문번호) 위조 가능성 주의(#34)")
    return (engine, "미교정")


# ============================ 공통: 출력 writer (v2 계약 동일) ============================

def write_chunk(out_path, engine, tier, book, author, subject, src_name, start, end, pages):
    label, caveat = engine_meta(engine, tier)
    body = "\n\n".join(f"<!-- p.{n} -->\n\n{t}" for n, t in pages)
    fm = (
        "---\n"
        f"tags: [교재원문, {subject}, {author}_{book}]\n"
        f"교재: 《{book}》 ({author})\n"
        f"과목: {subject}\n"
        f"포함_페이지: {start}-{end}\n"
        f"저자: {author}\n"
        f"출처: {src_name}\n"
        f"추출일: {datetime.now():%Y-%m-%d}\n"
        f"추출엔진: {label}\n"
        f"교정상태: {caveat}, Claude 교정+korean-law-mcp 검증 필요\n"
        "---\n"
    )
    title = f"# {book} ({author}) — p.{start}-{end} [{engine} 미교정]\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(fm + "\n" + title + "\n" + body + "\n")


# ============================ CLI ============================

def main():
    ap = argparse.ArgumentParser(description="OCR 추출 v3 (엔진 교체형)")
    ap.add_argument("--engine", required=True, choices=list(ENGINES))
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--book", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--subject", default="")
    ap.add_argument("--tier", default="agentic", help="llamaparse: fast|cost_effective|agentic")
    ap.add_argument("--chunk-size", type=int, default=30)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=0)  # 0 = 마지막
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    extract = ENGINES[a.engine]

    doc = fitz.open(a.pdf)
    total = doc.page_count
    end = a.end or total
    src_name = os.path.basename(a.pdf)
    print(f"[v3:{a.engine}] {src_name} 총 {total}p, 처리 {a.start}-{end}", flush=True)

    log = []
    page = a.start
    while page <= end:
        ce = min(page + a.chunk_size - 1, end)
        out_path = os.path.join(a.out, f"{a.prefix}_p{page:03d}-{ce:03d}.md")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 200:
            print(f"[SKIP 존재] {out_path}", flush=True)
            page = ce + 1
            continue

        t0 = time.time()
        pages = extract(doc, page, ce, tier=a.tier, debug=a.debug)
        write_chunk(out_path, a.engine, a.tier, a.book, a.author, a.subject,
                    src_name, page, ce, pages)
        for n, t in pages:
            log.append({"page": n, "chars": len(t)})
        print(f"[WROTE] {out_path}  ({round(time.time()-t0,1)}s)", flush=True)
        page = ce + 1

    json.dump(log, open(os.path.join(a.out, f"{a.prefix}_ocrlog.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"DONE {len(log)}p", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
