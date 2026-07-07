# %% [markdown]
# # Cell 0a: 패키지 설치 + 자동 재시작
# 첫 실행: 설치 후 자동 재시작됩니다. 재시작 후 **[런타임 > 모두 실행]**을 다시 눌러주세요.
# 두 번째 실행: 이미 설치되어 있으므로 자동 스킵하고 다음 셀로 진행합니다.
#
# **PaddlePaddle 공식 인덱스에서 GPU 버전 설치** (2026-04 검증):
# - Colab 의 CUDA 는 12.5 → `cu126` wheel 이 호환된다.
# - `paddlepaddle-gpu` 는 PyPI 에 3.0.0 이상이 게시되지 않으므로 반드시 공식 인덱스
#   `https://www.paddlepaddle.org.cn/packages/stable/cu126/` 를 `-i` 로 지정해야 한다.
# - 버전은 `paddlepaddle-gpu==3.2.1` 사용 (3.0.0 에는 PaddleX 3.5 일부 보조모델 비호환,
#   3.3.x 에는 oneDNN-PIR 회귀 버그). 3.2.1 이 PaddleOCR/PaddleX 3.5 와 가장 안정적으로 동작.
# - `paddleocr==3.5.0` 은 `paddlex>=3.5.0,<3.6.0` 을 요구하므로 `paddlex[ocr]==3.5.1` 과 호환.
# - **설치 순서**: paddlepaddle-gpu 를 공식 인덱스로 먼저 → 그 다음 paddleocr/paddlex 등을
#   기본 PyPI 에서 설치. 한 명령에 두 인덱스를 섞으면 PyPI 패키지를 못 찾는다.
#
# 로컬(CPU): `pip install paddlepaddle==3.0.0 paddleocr==3.5.0 "paddlex[ocr]==3.5.1" langchain-text-splitters pymupdf pillow tqdm`

# %%
import os, subprocess, sys, tempfile

# Issue #C: Windows 호환을 위해 OS 별 임시 디렉터리 사용
INSTALL_FLAG = os.path.join(tempfile.gettempdir(), 'paddle_installed')
_IS_COLAB = 'google.colab' in sys.modules or os.path.exists('/content')

if not os.path.exists(INSTALL_FLAG):
    if _IS_COLAB:
        # 1) paddlepaddle-gpu 는 공식 인덱스에서 (PyPI 에 없는 버전)
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            'paddlepaddle-gpu==3.2.1',
            '-i', 'https://www.paddlepaddle.org.cn/packages/stable/cu126/',
        ])
        # 2) paddleocr + paddlex[ocr] + 보조 의존성은 평소처럼 PyPI 에서
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            'paddleocr==3.5.0',
            'paddlex[ocr]==3.5.1',
            'langchain-text-splitters',
            'pymupdf',
            'pillow',
            'tqdm',
        ])
    else:
        # 로컬 CPU 는 모두 PyPI 에 있음
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            'paddlepaddle==3.0.0',
            'paddleocr==3.5.0',
            'paddlex[ocr]==3.5.1',
            'langchain-text-splitters',
            'pymupdf',
            'pillow',
            'tqdm',
        ])
    open(INSTALL_FLAG, 'w').close()
    print("설치 완료.")
    if _IS_COLAB:
        print("Colab: 런타임을 재시작합니다. 재시작 후 다시 [런타임 > 모두 실행]을 눌러주세요.")
        import google.colab
        google.colab.runtime.restart_session()
    else:
        print("로컬: 재시작 없이 다음 셀로 진행하세요.")
else:
    print("패키지 이미 설치됨. 다음 셀로 진행합니다.")

# %% [markdown]
# # Cell 0b: import + Drive 마운트 + 경로 설정
# **런타임 재시작 후** 이 셀부터 실행하세요.

# %%
# === import (런타임 재시작 후 실행) ===
import os, json, re, glob, shutil, sys
from pathlib import Path
from datetime import datetime

# Issue #B: 모델 캐시를 Drive 로 매핑 → 13개 서브모델 재다운로드 방지
# (paddlex 의 캐시 경로는 환경변수 PADDLE_PDX_CACHE_HOME 로 지정 가능)
def _resolve_drive_root() -> str:
    # 1순위: 명시적 환경변수
    env = os.environ.get("DRIVE_ROOT")
    if env and os.path.isdir(env):
        return env
    # 2순위: Colab Drive 마운트 경로
    if os.path.isdir("/content/drive/MyDrive"):
        return "/content/drive/MyDrive"
    # 3순위: 로컬 Windows 의 'H:\내 드라이브' (구글 드라이브 데스크탑)
    for cand in (r"H:\내 드라이브", r"H:/내 드라이브", "/mnt/h/내 드라이브"):
        if os.path.isdir(cand):
            return cand
    return "/content/drive/MyDrive"


# Colab 이면 마운트, 아니면 로컬 경로 탐지
_IS_COLAB = 'google.colab' in sys.modules or os.path.exists('/content')
if _IS_COLAB:
    try:
        from google.colab import drive
        drive.mount("/content/drive", force_remount=True)
    except Exception as e:
        print(f"[경고] drive.mount 실패: {e}")
DRIVE_ROOT = _resolve_drive_root()
print(f"DRIVE_ROOT: {DRIVE_ROOT}")

# 모델 캐시 경로를 Drive 안으로 고정 (재실행 시 재다운로드 방지)
PADDLE_CACHE_DIR = os.environ.get(
    "PADDLE_PDX_CACHE_HOME",
    os.path.join(DRIVE_ROOT, ".auto-memory", "paddlex_cache"),
)
os.makedirs(PADDLE_CACHE_DIR, exist_ok=True)
os.environ["PADDLE_PDX_CACHE_HOME"] = PADDLE_CACHE_DIR
# paddlex 3.x 의 official_models 캐시도 같은 트리 안으로
os.environ.setdefault("HOME", os.path.dirname(PADDLE_CACHE_DIR) or PADDLE_CACHE_DIR)
print(f"PADDLE_PDX_CACHE_HOME: {PADDLE_CACHE_DIR}")

# paddlex 먼저 import (PDX 초기화 순서 보장)
import paddlex
print(f"PaddleX: {paddlex.__version__}")

from paddleocr import PaddleOCR
print("PaddleOCR import OK")

# 경로 설정
SYNC_ROOT       = os.path.join(DRIVE_ROOT, "sync", "_교재원문")
MEMORY_BASE     = os.path.join(DRIVE_ROOT, ".auto-memory")
CORRECTIONS_DIR = os.path.join(MEMORY_BASE, "corrections")
PROGRESS_FILE   = os.path.join(MEMORY_BASE, "ocr_progress.json")

# 자동 적용 confidence 임계값 (Haiku 교정 결과의 confidence 기준)
CONFIDENCE_AUTO = 0.85

os.makedirs(CORRECTIONS_DIR, exist_ok=True)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "last_run": None,
        "books": {},
        "pipeline_status": {},
    }


def save_progress(prog):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(prog, f, ensure_ascii=False, indent=2)


def corrections_file(book_id: str) -> str:
    return os.path.join(CORRECTIONS_DIR, f"{book_id}.jsonl")


progress = load_progress()
print(f"Progress loaded: {len(progress.get('books', {}))} books")
print(f"SYNC_ROOT: {SYNC_ROOT}")
print(f"CORRECTIONS_DIR: {CORRECTIONS_DIR}")
print("Setup OK!")

# %% [markdown]
# # Cell 1: 자동 매핑 (PDF ↔ MD chunk)

# %%
# ============================================================
PAGE_RANGE_RE  = re.compile(r'_p(\d+)-(\d+)\.(?:md|qmd)$')
SUBJECT_DIR_RE = re.compile(r'^\d+\.')


def scan_pdfs(drive_root):
    books = {}
    for d in sorted(Path(drive_root).iterdir()):
        if not d.is_dir() or not SUBJECT_DIR_RE.match(d.name):
            continue
        for pdf in sorted(d.rglob("*.pdf")):
            book_id = pdf.stem
            if book_id in books:
                book_id = f"{book_id}__{pdf.parent.name}"
            books[book_id] = {
                "pdf_path": str(pdf),
                "subject": d.name,
                "status": "pending",
                "pages_done": [],
                "in_progress_chunk": 0,
                "paddle_dir": None,
                "md_chunks": [],
            }
    return books


def scan_md_chunks(sync_root):
    md_map = {}
    root = Path(sync_root)
    if not root.exists():
        return md_map
    for md in sorted(root.rglob("*.md")):
        m = PAGE_RANGE_RE.search(md.name)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            stem = PAGE_RANGE_RE.sub('', md.name)
            md_map.setdefault(stem, []).append(
                {"path": str(md), "start": start, "end": end}
            )
    return md_map


def match_books(books, md_map):
    for book_id, info in books.items():
        if book_id in md_map:
            info["md_chunks"] = sorted(md_map[book_id], key=lambda x: x["start"])
            continue
        book_tokens = set(book_id.lower().split("_"))
        best_stem, best_score = None, 0
        for stem in md_map:
            overlap = len(book_tokens & set(stem.lower().split("_")))
            if overlap > best_score and overlap >= 2:
                best_score, best_stem = overlap, stem
        if best_stem:
            info["md_chunks"] = sorted(md_map[best_stem], key=lambda x: x["start"])
            info["md_stem_matched"] = best_stem
    return books


book_map = scan_pdfs(DRIVE_ROOT)
md_map   = scan_md_chunks(SYNC_ROOT)
book_map = match_books(book_map, md_map)

for book_id, info in book_map.items():
    if book_id not in progress["books"]:
        progress["books"][book_id] = info
    elif progress["books"][book_id]["status"] == "in_progress":
        chunk_idx = progress["books"][book_id].get("in_progress_chunk", 0)
        print(f"[재시작] {book_id}: chunk {chunk_idx}부터")

save_progress(progress)
pending = [b for b, v in progress["books"].items() if v["status"] == "pending"]
print(f"등록: {len(progress['books'])}권 / 미처리: {len(pending)}권")

# %% [markdown]
# # Cell 2: PP-StructureV3 추출
# 레이아웃 감지 + 표 인식 + 텍스트 OCR 통합 (PP-OCRv5 내부 포함)

# %%
# ============================================================
import fitz
from PIL import Image
import io
import numpy as np
import gc
from tqdm import tqdm

# Issue #D: PP-StructureV3 의 predict() 결과는 LayoutParsingResultV2 객체이며
# JSON 스키마는 result_v2.py 기준 다음과 같다 (paddlex 3.5.x 확인):
#   {
#     "input_path": str, "page_index": int, "page_count": int,
#     "width": int, "height": int, "model_settings": dict,
#     "parsing_res_list": [
#       {"block_label": str, "block_content": str, "block_bbox": [x1,y1,x2,y2],
#        "block_id": int, "block_order": int}, ...
#     ],
#     "doc_preprocessor_res": dict, "layout_det_res": dict,
#     "overall_ocr_res": dict, "table_res_list": [...], ...
#   }
# block_label 값은 markdown_format_funcs.build_handle_funcs_dict 에 정의됨:
#   text/ocr/vertical_text, paragraph_title/doc_title/abstract_title/...,
#   table, image/header_image/footer_image, formula/display_formula/inline_formula,
#   chart, seal, algorithm, footnote, header, footer, aside_text 등.

# 라벨 → 우리 노트가 쓰는 좁은 타입 4종으로 정규화
_LABEL_TYPE = {
    "table": "table",
    "image": "figure", "header_image": "figure", "footer_image": "figure",
    "chart": "figure", "seal": "figure",
    "formula": "formula", "display_formula": "formula", "inline_formula": "formula",
}
_TITLE_LABELS = {
    "paragraph_title", "doc_title", "abstract_title", "reference_title",
    "content_title", "table_title", "figure_title", "chart_title",
}


def _classify(block_label: str) -> str:
    if block_label in _LABEL_TYPE:
        return _LABEL_TYPE[block_label]
    if block_label in _TITLE_LABELS:
        return "title"
    return "text"


# PP-StructureV3 는 paddleocr 의 공식 wrapper 클래스로 로드한다.
# 내부적으로 paddlex.create_pipeline("PP-StructureV3") 를 호출하지만, ergonomic kwargs
# (use_*_recognition 등) 를 __init__ 에서 직접 받을 수 있고, paddleocr 3.5+ 의 공식 API.
try:
    from paddleocr import PPStructureV3
    _ppstruct = PPStructureV3(
        # 메모리 절약: seal/formula/chart 는 init 단계에서 끄면 모델 자체가 로드되지 않음
        use_seal_recognition=False,
        use_formula_recognition=False,
        use_chart_recognition=False,
    )
    _HAS_PADDLEX = True
    print("PP-StructureV3 (paddleocr wrapper) 파이프라인 로드 완료")
except Exception as e:
    _ppstruct_fallback = PaddleOCR(
        use_textline_orientation=True, lang="korean"
    )
    _HAS_PADDLEX = False
    print(f"[경고] PP-StructureV3 미설치 - PaddleOCR 폴백 모드: {e}")


def pdf_page_to_image(pdf_path, page_num, dpi=150):
    """PDF 한 페이지를 PIL.Image 로 변환.
    dpi=150 이 CPU 박스에서 메모리/속도 균형이 가장 좋다 (200은 OOM 위험)."""
    doc = fitz.open(pdf_path)
    pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()
    return img


def _paddlex_predict(img_array) -> list:
    """PP-StructureV3로 블록 리스트 반환 (parsing_res_list 기준).
    use_* 토글은 이미 __init__ 에서 끈 상태이지만, predict 단계에서도 다시 명시해
    Colab 에서 메모리 폭주를 방지한다."""
    blocks: list = []
    try:
        for res in _ppstruct.predict(
            img_array,
            use_seal_recognition=False,
            use_formula_recognition=False,
            use_chart_recognition=False,
        ):
            res_json = res.json
            res_json = res_json() if callable(res_json) else res_json
            # paddlex 가 가끔 {"res": {...}} 한 겹 더 감쌈 → 풀어주기
            if isinstance(res_json, dict) and "res" in res_json and "parsing_res_list" not in res_json:
                res_json = res_json["res"]
            parsing = res_json.get("parsing_res_list", []) if isinstance(res_json, dict) else []
            for entry in parsing:
                label = (entry.get("block_label") or "text").lower()
                blocks.append({
                    "block_type": _classify(label),
                    "label": label,
                    "content": entry.get("block_content", "") or "",
                    "bbox": entry.get("block_bbox", [0, 0, 0, 0]),
                    "order": entry.get("block_order", entry.get("block_id", 0)),
                })
            # block_order 가 있으면 그 순서대로 정렬
            blocks.sort(key=lambda b: b.get("order", 0))
    except Exception as e:
        print(f"  [경고] PP-StructureV3 예측 오류: {type(e).__name__}: {e}")
    if not blocks:
        h, w = img_array.shape[:2]
        blocks = [{"block_type": "text", "label": "text", "content": "",
                   "bbox": [0, 0, w, h], "order": 0}]
    return blocks


def _fallback_predict(img_array) -> list:
    """PaddleOCR 폴백 - 전체 이미지를 단일 텍스트 블록으로 (3.x predict API)."""
    result = _ppstruct_fallback.predict(img_array)
    if not result:
        return []
    lines = []
    for res in result:
        res_dict = res.json if hasattr(res, "json") and isinstance(res.json, dict) else (
            res.json() if hasattr(res, "json") and callable(res.json) else res
        )
        rec_texts = (
            res_dict.get("rec_texts")
            if isinstance(res_dict, dict)
            else getattr(res, "rec_texts", None)
        )
        if rec_texts:
            lines.extend(rec_texts)
    text = "\n".join(lines)
    return [{"block_type": "text", "label": "text", "content": text,
             "bbox": [0, 0, 0, 0], "order": 0}]


def process_page(pdf_path, page_num) -> list:
    img = pdf_page_to_image(pdf_path, page_num)
    arr = np.array(img)
    del img
    raw = _paddlex_predict(arr) if _HAS_PADDLEX else _fallback_predict(arr)
    del arr
    gc.collect()
    return [
        {
            "block_id": f"p{page_num + 1}-b{b_idx:02d}",
            "block_type": b["block_type"],
            "label": b.get("label", b["block_type"]),
            "content": b["content"],
            "bbox": b["bbox"],
        }
        for b_idx, b in enumerate(raw)
    ]


def blocks_to_markdown(blocks: list) -> str:
    parts = []
    for block in blocks:
        parts.append(
            f"<!-- block: {block['block_id']} type: {block['block_type']} bbox: {block['bbox']} -->"
        )
        parts.append(block["content"])
        parts.append("")
    return "\n".join(parts)


def process_book(book_id, book_info, progress):
    pdf_path = book_info["pdf_path"]
    if not os.path.exists(pdf_path):
        print(f"  [SKIP] PDF 없음: {pdf_path}")
        return

    doc = fitz.open(pdf_path)
    total = len(doc)
    doc.close()

    paddle_dir = os.path.join(SYNC_ROOT, book_id, "_paddle")
    os.makedirs(paddle_dir, exist_ok=True)
    progress["books"][book_id]["paddle_dir"] = paddle_dir
    progress["books"][book_id]["status"] = "in_progress"
    start = book_info.get("in_progress_chunk", 0)

    for page_num in tqdm(range(start, total), desc=book_id):
        out_md = os.path.join(paddle_dir, f"p{page_num + 1:04d}.md")
        out_json = os.path.join(paddle_dir, f"p{page_num + 1:04d}.blocks.json")
        if os.path.exists(out_md):
            continue
        blocks = process_page(pdf_path, page_num)
        md = blocks_to_markdown(blocks)
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(f"<!-- page: {page_num + 1} source: {book_id} -->\n{md}")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(blocks, f, ensure_ascii=False, indent=2)
        progress["books"][book_id]["pages_done"].append(page_num + 1)
        progress["books"][book_id]["in_progress_chunk"] = page_num + 1
        if page_num % 10 == 0:
            save_progress(progress)

    progress["books"][book_id]["status"] = "ocr_done"
    save_progress(progress)
    print(f"  [{book_id}] OCR 완료: {total}페이지")


TARGET_BOOKS = [
    b for b, v in progress["books"].items()
    if v["status"] in ("pending", "in_progress")
]
print(f"처리 대상: {len(TARGET_BOOKS)}권")

for book_id in TARGET_BOOKS:
    print(f"\n처리 중: {book_id}")
    process_book(book_id, progress["books"][book_id], progress)

# %% [markdown]
# # Cell 3: 표 교체 + 텍스트 라인 diff
# - table 블록: PaddleOCR 결과로 직접 교체 (마크다운 표 위치 탐색)
# - text 블록: 라인 단위 diff → conflict 리스트
# - corrections 저장: CORRECTIONS_DIR/{book_id}.jsonl

# %%
# ============================================================
import difflib

_BLOCK_HDR = re.compile(r'<!--\s*block:\s*(p\d+-b\d+)\s+type:\s*(\w+)')
_TABLE_SEP = re.compile(r'^\|[-:| ]+\|$')


def _parse_blocks_from_md(md_text: str) -> list:
    blocks, cur = [], None
    for line in md_text.splitlines():
        m = _BLOCK_HDR.match(line)
        if m:
            if cur is not None:
                blocks.append(cur)
            cur = {"block_id": m.group(1), "block_type": m.group(2), "lines": []}
        elif cur is not None:
            cur["lines"].append(line)
    if cur is not None:
        blocks.append(cur)
    return blocks


def _find_table_positions(orig_lines: list) -> list:
    """원본 MD에서 마크다운 표 블록의 시작/끝 라인 인덱스 반환"""
    positions, in_table, start = [], False, -1
    for i, line in enumerate(orig_lines):
        stripped = line.strip()
        is_table_line = stripped.startswith("|") and "|" in stripped[1:]
        if is_table_line:
            if not in_table:
                in_table, start = True, i
        else:
            if in_table:
                positions.append((start, i - 1))
                in_table = False
    if in_table:
        positions.append((start, len(orig_lines) - 1))
    return positions


def compare_and_diff(book_id, book_info):
    stats = {"tables_found": 0, "conflicts": 0, "matches": 0}
    paddle_dir = book_info.get("paddle_dir")
    if not paddle_dir or not os.path.exists(paddle_dir):
        return stats

    corr_path = corrections_file(book_id)
    corrections = []

    for chunk in book_info.get("md_chunks", []):
        orig_path = chunk["path"]
        if not os.path.exists(orig_path):
            continue
        with open(orig_path, "r", encoding="utf-8") as f:
            orig_lines = f.readlines()

        paddle_blocks = []
        for page_num in range(chunk["start"], chunk["end"] + 1):
            pf = os.path.join(paddle_dir, f"p{page_num:04d}.md")
            if os.path.exists(pf):
                with open(pf, "r", encoding="utf-8") as f:
                    paddle_blocks.extend(_parse_blocks_from_md(f.read()))

        table_blocks = [b for b in paddle_blocks if b["block_type"] == "table"]
        # text-like 블록: text + title (제목) 모두 라인 diff 대상
        text_blocks  = [b for b in paddle_blocks if b["block_type"] in ("text", "title")]

        # --- 표 블록: 원본 표 위치 탐색 후 직접 교체 ---
        orig_table_positions = _find_table_positions(orig_lines)
        for idx, p_blk in enumerate(table_blocks):
            paddle_table = "\n".join(p_blk["lines"]).strip()
            if not paddle_table:
                continue
            stats["tables_found"] += 1
            orig_pos = (
                orig_table_positions[idx]
                if idx < len(orig_table_positions)
                else None
            )
            original_content = ""
            if orig_pos:
                original_content = "".join(orig_lines[orig_pos[0]:orig_pos[1] + 1])
            corrections.append({
                "type": "table_adopt",
                "book_id": book_id,
                "chunk_path": orig_path,
                "pages": [chunk["start"], chunk["end"]],
                "block_id": p_blk["block_id"],
                "paddle_content": paddle_table,
                "original_content": original_content,
                "table_position": list(orig_pos) if orig_pos else None,
                "confidence": 0.95,
                "sonnet_reviewed": False,
                "status": "pending_apply",
                "reason": "PP-StructureV3 table block detected",
            })

        # --- 텍스트 블록: 라인 단위 diff ---
        # 원본 표 영역은 paddle 측에선 별도 table 블록으로 분리되므로
        # 텍스트 diff 입력에서 제외 (false conflict 방지)
        excluded = set()
        for s, e in orig_table_positions:
            for k in range(s, e + 1):
                excluded.add(k)
        orig_text_lines = [
            ln for k, ln in enumerate(orig_lines) if k not in excluded
        ]
        paddle_text = "\n".join(
            "\n".join(b["lines"]) for b in text_blocks
        ).strip()
        orig_text = "".join(orig_text_lines).strip()

        if not paddle_text:
            continue

        sm = difflib.SequenceMatcher(
            None, orig_text.splitlines(), paddle_text.splitlines()
        )
        ratio = sm.ratio()
        if ratio >= 0.90:
            stats["matches"] += 1
            continue

        orig_lines_list = orig_text.splitlines()
        paddle_lines_list = paddle_text.splitlines()

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag not in ("replace", "insert", "delete"):
                continue
            for i in range(i1, i2):
                ol = orig_lines_list[i].strip() if i < len(orig_lines_list) else ""
                j = j1 + (i - i1)
                pl = paddle_lines_list[j].strip() if j < len(paddle_lines_list) else ""
                if ol or pl:
                    stats["conflicts"] += 1
                    corrections.append({
                        "type": "text_conflict",
                        "book_id": book_id,
                        "chunk_path": orig_path,
                        "block_type": "text",
                        "line_idx": i,
                        "original": ol,
                        "paddle": pl,
                        "confidence": None,
                        "sonnet_reviewed": False,
                        "status": "pending_haiku",
                    })

    with open(corr_path, "a", encoding="utf-8") as f:
        for c in corrections:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    return stats


total_stats = {"tables_found": 0, "conflicts": 0, "matches": 0}
for book_id, book_info in progress["books"].items():
    if book_info["status"] not in ("ocr_done", "comparing"):
        continue
    progress["books"][book_id]["status"] = "comparing"
    s = compare_and_diff(book_id, book_info)
    for k in total_stats:
        total_stats[k] += s[k]
    progress["books"][book_id]["status"] = "compared"

save_progress(progress)
print("=== 표 교체 + 라인 diff 결과 ===")
print(
    f"  표 채택: {total_stats['tables_found']} / "
    f"충돌: {total_stats['conflicts']} / "
    f"일치: {total_stats['matches']}"
)

# %% [markdown]
# ## Cell 4: Haiku 교정 - Claude Code에서 실행
#
# 이 단계는 Colab이 아닌 **Claude Code**에서 실행합니다.
# Claude Max 구독에 포함되므로 추가 비용 없음.
#
# ```bash
# # Claude Code 터미널에서:
# cd "H:\내 드라이브"
# python .agent/scripts/sonnet_review.py     # corrections.jsonl 읽고 교정
# python .agent/scripts/apply_corrections.py # 교정 결과 적용
# ```
#
# 또는 Cowork에서 "OCR 교정 진행해줘"라고 요청하면 자동 실행.

# %% [markdown]
# # Cell 5: 요약 + progress 갱신

# %%
# ============================================================
for book_id, book_info in progress["books"].items():
    if book_info["status"] == "compared":
        progress["books"][book_id]["status"] = "correction_ready"

progress["last_run"] = datetime.now().isoformat()
save_progress(progress)

# 전체 corrections 통계 (교재별 파일 합산)
all_c = []
for jf in glob.glob(os.path.join(CORRECTIONS_DIR, "*.jsonl")):
    with open(jf, "r", encoding="utf-8") as f:
        all_c.extend(json.loads(l) for l in f if l.strip())

t_tables   = sum(1 for c in all_c if c.get("type") == "table_adopt")
t_conflict = sum(1 for c in all_c if c.get("type") == "text_conflict")
t_auto     = sum(
    1 for c in all_c
    if c.get("status") == "haiku_done"
    and c.get("confidence", 0) >= CONFIDENCE_AUTO
    and c.get("correction", {}).get("changed")
)
t_sonnet   = sum(1 for c in all_c if c.get("status") == "low_confidence")
t_reject   = sum(1 for c in all_c if c.get("status") == "rejected")

print("=" * 50)
print("OCR 파이프라인 완료")
print("=" * 50)
print(f"표 채택(PP-StructureV3): {t_tables}건")
print(f"텍스트 충돌:             {t_conflict}건")
print(f"자동 적용(>={CONFIDENCE_AUTO}):     {t_auto}건")
print(f"Sonnet 대기(<{CONFIDENCE_AUTO}):     {t_sonnet}건")
print(f"거부:                    {t_reject}건")
print(f"\nCorrections: {CORRECTIONS_DIR}/{{book_id}}.jsonl")
print(f"Progress:    {PROGRESS_FILE}")
print("다음 단계: sonnet_review.py -> apply_corrections.py")
