# %% [markdown]
# # OCR Extract v2 — marker-pdf 기반 추출 전용 노트북 (전면 개정)
#
# 설계 원칙:
# - 추출 전용. 비교/검증은 별도 노트북.
# - 코랩이 끊겨도 Drive 의 progress.json 기반으로 이어서 작업.
# - 기존 마크다운을 수정하지 않고 `sync/_ocr_extracted/` 하위에 새로 저장.
# - 교재별 목차 오프셋(toc_offset) 자동 감지 + Drive 영속화.
# - **PDF 원본은 sync 가 아닌 과목 폴더에 있다.** 1.민사/, 2.형사/, 3.공법/, 4.선택법/.
# - 기존 sync/_교재원문/ 의 .md 와 PDF 를 매칭한 match_table.json 을 함께 생성.
#
# 셀 구성:
# - Cell 0a: 패키지 설치 + 자동 재시작
# - Cell 0b: import + Drive 마운트 + 경로 설정 (SOURCE_DIRS = 과목 폴더들)
# - Cell 1 : PDF 스캔(과목 폴더) + 기존 .md frontmatter 매칭 + offset_table·match_table 갱신
# - Cell 2 : marker-pdf 추출 (50p 청크, frontmatter 포함)
# - Cell 3 : 추출 결과 요약
# - Cell 4 : 수동 오프셋 수정 (선택)

# %% [markdown]
# # Cell 0pre: 배치 한계 환경변수 (필요 시 주석 해제)
#
# Colab 자동 재시작 후 환경변수가 모두 날아가므로 **매 실행마다 이 셀이 다시 돌아야** 합니다.
# (다행히 [런타임 > 모두 실행] 누르면 자동으로 다 돔.)
#
# Colab 무료 ~12GB RAM 기준 권장 설정. 더 보수적 / 더 공격적은 주석 참고.

# %%
import os

# === Colab 무료 12GB RAM 기준 권장 (안전 마진 3GB) ===
os.environ["OCR_MAX_RAM_GB"]    = "9"      # RSS 9GB 도달 시 즉시 종료 (가장 직접적 OOM 방어)
os.environ["OCR_RECYCLE_EVERY"] = "3"      # 3권마다 converter 재생성 → RAM ~5GB로 리셋
os.environ["OCR_SKIP_LARGE"]    = "500"    # 500p 초과 PDF 는 다음 배치로 미루기
os.environ["OCR_LARGE_PDF_THRESHOLD"] = "200"  # 200p 초과면 chunk 작게
os.environ["OCR_SMALL_CHUNK"]   = "20"

# === 추가 안전판 (선택) ===
# os.environ["OCR_MAX_BOOKS"]      = "30"   # 한 번에 30권만
# os.environ["OCR_MAX_TOTAL_PAGES"]= "500"  # 누적 500p 도달 시 종료
# os.environ["OCR_MAX_RUNTIME_MIN"]= "30"   # 30분 안전판
# os.environ["OCR_MAX_TOTAL_MB"]   = "100"  # 누적 100MB

print("[Cell 0pre] env 설정 완료:")
for k in sorted(os.environ):
    if k.startswith("OCR_"):
        print(f"  {k} = {os.environ[k]}")

# %% [markdown]
# # Cell 0a: 패키지 설치 + 자동 재시작
#
# 첫 실행: 설치 후 자동 재시작됩니다. 재시작 후 **[런타임 > 모두 실행]** 다시 누르세요.
# 두 번째 실행: 이미 설치되어 있으면 자동 스킵.
#
# 메모:
# - `marker-pdf` 는 PyTorch 기반이므로 PaddlePaddle 공식 인덱스를 쓰지 않는다.
# - `transformers>=4.57.1,<5.0` 으로 고정 — v5.x 에서 `surya` 가 import 단계에서 크래시.
# - 로컬(CPU) 도 동일 패키지 설치, GPU 가속은 자동 감지.

# %%
import os, subprocess, sys, tempfile

INSTALL_FLAG = os.path.join(tempfile.gettempdir(), "ocr_extract_v2_installed")
_IS_COLAB = "google.colab" in sys.modules or os.path.exists("/content")

PKGS = [
    "marker-pdf",
    "markdownify",
    "pymupdf",
    "tqdm",
    "psutil",
    "langchain-text-splitters",
    "transformers>=4.57.1,<5.0",
]

if not os.path.exists(INSTALL_FLAG):
    subprocess.check_call([sys.executable, "-m", "pip", "install", *PKGS])
    open(INSTALL_FLAG, "w").close()
    print("[Cell 0a] 설치 완료.")
    if _IS_COLAB:
        print("[Cell 0a] Colab: 런타임을 재시작합니다. 재시작 후 다시 [런타임 > 모두 실행].")
        import google.colab  # noqa: F401
        google.colab.runtime.restart_session()
    else:
        print("[Cell 0a] 로컬: 재시작 없이 다음 셀로 진행하세요.")
else:
    print("[Cell 0a] 패키지 이미 설치됨. 다음 셀로.")

# %% [markdown]
# # Cell 0b: import + Drive 마운트 + 경로 설정
#
# 핵심 변경:
# - SOURCE_DIR(단일) → SOURCE_DIRS(여러 과목 폴더) 로 확장.
# - 추출 대상: `1.민사/`, `2.형사/`, `3.공법/`, `4.선택법/` 의 모든 PDF (재귀).
# - 제외 폴더: `_trash`, `_원본보관`, `_원본보관소`, `5.기타`, `0.공유드라이브`,
#   `9.스터디 답안지`, `.agent`, `.auto-memory`, `__pycache__`.
# - 매칭 대상: `sync/_교재원문/` 하위의 기존 .md (1,485 개).
# - 환경변수 `OCR_SOURCE_DIRS` 콜론(`:` 또는 윈도우 `;`) 구분으로 덮어쓸 수 있음.

# %%
import os, sys, json, re, glob, shutil
from pathlib import Path
from datetime import datetime

# Drive 루트 자동 탐지 (Colab/Windows 로컬/WSL 모두 지원)
def _resolve_drive_root() -> str:
    env = os.environ.get("DRIVE_ROOT")
    if env and os.path.isdir(env):
        return env
    if os.path.isdir("/content/drive/MyDrive"):
        return "/content/drive/MyDrive"
    for cand in (r"H:\내 드라이브", r"H:/내 드라이브", "/mnt/h/내 드라이브"):
        if os.path.isdir(cand):
            return cand
    return "/content/drive/MyDrive"


_IS_COLAB = "google.colab" in sys.modules or os.path.exists("/content")
if _IS_COLAB:
    try:
        from google.colab import drive
        drive.mount("/content/drive", force_remount=True)
    except Exception as e:
        print(f"[경고] drive.mount 실패: {e}")

DRIVE_ROOT = _resolve_drive_root()
SYNC_ROOT = os.path.join(DRIVE_ROOT, "sync")

# === PDF 원본이 있는 과목 폴더들 (기본값) ===
DEFAULT_SOURCE_SUBDIRS = [
    "1.민사",
    "2.형사",
    "3.공법",
    "4.선택법",
]

# 환경변수로 덮어쓸 수 있다. 콜론(:) 또는 세미콜론(;) 구분.
_src_override = os.environ.get("OCR_SOURCE_DIRS")
if _src_override:
    parts = re.split(r"[;:]", _src_override)
    SOURCE_DIRS = [
        (p if os.path.isabs(p) else os.path.join(DRIVE_ROOT, p))
        for p in parts if p.strip()
    ]
else:
    SOURCE_DIRS = [os.path.join(DRIVE_ROOT, sub) for sub in DEFAULT_SOURCE_SUBDIRS]

# === 제외 디렉터리(이름 단위 매칭) ===
EXCLUDE_DIR_NAMES = {
    "_trash", "_원본보관", "_원본보관소", "5.기타",
    "0.공유드라이브", "9.스터디 답안지",
    ".agent", ".auto-memory", ".claude", ".git",
    "__pycache__", "_dryrun_save",
}

# === 기존 .md 매칭 대상 ===
EXISTING_MD_DIR = os.path.join(SYNC_ROOT, "_교재원문")

# === 새 추출 결과 ===
OUTPUT_DIR = os.path.join(SYNC_ROOT, "_ocr_extracted")

STATE_DIR = os.path.join(DRIVE_ROOT, ".auto-memory", "ocr_state")
HF_CACHE = os.path.join(DRIVE_ROOT, ".auto-memory", "hf_cache")

for d in (OUTPUT_DIR, STATE_DIR, HF_CACHE):
    os.makedirs(d, exist_ok=True)

# 모델 캐시를 Drive 로 매핑 (재실행 시 다운로드 방지)
os.environ["HF_HUB_CACHE"] = HF_CACHE
os.environ.setdefault("HF_HOME", HF_CACHE)

# Torch device 자동 감지
try:
    import torch
    TORCH_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except Exception:
    TORCH_DEVICE = "cpu"
os.environ["TORCH_DEVICE"] = TORCH_DEVICE

OFFSET_TABLE_PATH = os.path.join(STATE_DIR, "offset_table.json")
MATCH_TABLE_PATH = os.path.join(STATE_DIR, "match_table.json")
PROGRESS_PATH = os.path.join(STATE_DIR, "progress.json")
AUDIT_RESULT_PATH = os.path.join(DRIVE_ROOT, "_md_pdf_audit_result.json")

print(f"[Cell 0b] DRIVE_ROOT       = {DRIVE_ROOT}        (exists={os.path.isdir(DRIVE_ROOT)})")
print(f"[Cell 0b] SYNC_ROOT        = {SYNC_ROOT}         (exists={os.path.isdir(SYNC_ROOT)})")
print(f"[Cell 0b] EXISTING_MD_DIR  = {EXISTING_MD_DIR}   (exists={os.path.isdir(EXISTING_MD_DIR)})")
print(f"[Cell 0b] OUTPUT_DIR       = {OUTPUT_DIR}        (exists={os.path.isdir(OUTPUT_DIR)})")
print(f"[Cell 0b] STATE_DIR        = {STATE_DIR}         (exists={os.path.isdir(STATE_DIR)})")
print(f"[Cell 0b] HF_CACHE         = {HF_CACHE}")
print(f"[Cell 0b] TORCH_DEVICE     = {TORCH_DEVICE}")
print(f"[Cell 0b] AUDIT_RESULT     = {AUDIT_RESULT_PATH}  (exists={os.path.exists(AUDIT_RESULT_PATH)})")
print(f"[Cell 0b] SOURCE_DIRS ({len(SOURCE_DIRS)}):")
for _sd in SOURCE_DIRS:
    print(f"  - {_sd}  (exists={os.path.isdir(_sd)})")

# 드라이브 마운트/경로 정합성 강제 점검 — 여기서 막아야 Cell 1·2 가 빈 테이블로 조용히 끝나는 사고를 막는다.
if not os.path.isdir(DRIVE_ROOT):
    raise RuntimeError(
        f"[Cell 0b] DRIVE_ROOT 존재하지 않음: {DRIVE_ROOT}. "
        "Colab 이라면 drive.mount 실패 가능 — 셀 다시 실행하고 인증을 확인하세요."
    )
_existing_sources = [d for d in SOURCE_DIRS if os.path.isdir(d)]
if not _existing_sources:
    raise RuntimeError(
        f"[Cell 0b] SOURCE_DIRS 중 존재하는 폴더가 하나도 없음. "
        f"기본값={DEFAULT_SOURCE_SUBDIRS}, 실제={SOURCE_DIRS}. "
        "OCR_SOURCE_DIRS 환경변수로 덮어쓰거나 폴더를 확인하세요."
    )
if len(_existing_sources) < len(SOURCE_DIRS):
    _missing = [d for d in SOURCE_DIRS if not os.path.isdir(d)]
    print(f"[Cell 0b] (주의) 일부 SOURCE_DIRS 누락: {_missing}")

# %% [markdown]
# # Cell 1: PDF 스캔 + 기존 .md 매칭 + offset_table·match_table 갱신
#
# ## 단계
# 1. SOURCE_DIRS 전체에서 PDF 재귀 스캔 (EXCLUDE_DIR_NAMES 제외).
# 2. EXISTING_MD_DIR 의 .md 스캔, frontmatter 파싱 (느슨한 YAML).
# 3. md ↔ PDF 매칭:
#    - frontmatter 의 `pdf_원본` 명시 경로
#    - 같은 폴더(sibling) PDF 중 토큰 겹침 (≥2)
#    - 전역 PDF 인덱스에서 stem 정확 매칭
#    - 전역 토큰 매칭(≥3 토큰 겹침)
#    - 실패 → unmatched
# 4. 교재별 toc_offset 자동 감지 (페이지 번호 패턴: 로마자→아라비아 전환점).
# 5. `offset_table.json`, `match_table.json` 저장.
#
# ## 식별자(`book_name`)
# DRIVE_ROOT 기준 상대경로의 디렉터리 부분을 `__` 로 합치고 파일 stem 을 붙임.
# 예: `1.민사/30.송영곤_기본민법/민법_송영곤_기본민법.pdf`
#  → `1민사__30송영곤_기본민법__민법_송영곤_기본민법`
# 점(.) 은 폴더 번호 표기에서 충돌이 잦으므로 제거.

# %%
import fitz  # pymupdf

# ----- 1) 페이지 번호 패턴 분석 (toc_offset 감지) -----
_ROMAN_RE = re.compile(r"^\s*([ivxlcdm]{1,5})\s*$", re.IGNORECASE)
_ARABIC_RE = re.compile(r"^\s*(\d{1,4})\s*$")
_ROMAN_VALID = {
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
    "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi", "xxvii", "xxviii", "xxix", "xxx",
}


def _classify_pagenum(page_text: str) -> str:
    """페이지 번호 영역 분류: 'roman' | 'arabic' | 'none'."""
    if not page_text:
        return "none"
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    tail = lines[-8:]
    for ln in reversed(tail):
        m = _ARABIC_RE.match(ln)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 1500:
                return "arabic"
        m = _ROMAN_RE.match(ln)
        if m and m.group(1).lower() in _ROMAN_VALID:
            return "roman"
    return "none"


def detect_toc_offset(pdf_path: str, max_scan: int = 50) -> tuple[int, str]:
    """목차 오프셋 자동 감지. (toc_offset, method)."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  [경고] open 실패: {pdf_path} → {e}")
        return 0, "fallback"
    try:
        n_scan = min(max_scan, doc.page_count)
        labels: list[str] = []
        for i in range(n_scan):
            try:
                txt = doc.load_page(i).get_text("text")
            except Exception:
                txt = ""
            labels.append(_classify_pagenum(txt))
        has_roman = any(l == "roman" for l in labels)
        if has_roman:
            last_roman = max(i for i, l in enumerate(labels) if l == "roman")
            for j in range(last_roman + 1, len(labels)):
                if labels[j] == "arabic":
                    return j, "auto"
            return 0, "fallback"
        return 0, "fallback"
    finally:
        doc.close()


# ----- 2) 디렉터리 워킹 (제외 규칙) -----
def _walk_pdfs(root: str) -> list[str]:
    """root 아래 모든 PDF 를 EXCLUDE_DIR_NAMES 를 피해 재귀 수집."""
    out: list[str] = []
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        # 제외 디렉터리는 더 이상 내려가지 않음 (in-place 수정).
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
        for fn in filenames:
            if fn.lower().endswith(".pdf"):
                out.append(os.path.join(dirpath, fn))
    return out


def _book_name_from_pdf(pdf_path: str) -> str:
    """DRIVE_ROOT 기준 상대경로를 안전한 식별자로 변환.

    예) 1.민사/30.송영곤_기본민법/민법_송영곤_기본민법.pdf
     →  1민사__30송영곤_기본민법__민법_송영곤_기본민법
    """
    rel = os.path.relpath(pdf_path, DRIVE_ROOT).replace("\\", "/")
    parts = rel.split("/")
    parts[-1] = os.path.splitext(parts[-1])[0]
    cleaned = []
    for p in parts:
        # 폴더 번호 표기(.) 제거. 공백은 _ 로.
        p = p.replace(".", "").replace(" ", "_")
        cleaned.append(p)
    return "__".join(cleaned)


# ----- 3) frontmatter 파서 (audit 스크립트 포팅, 느슨 YAML) -----
_KEY_RE = re.compile(r"([가-힣A-Za-z_][가-힣A-Za-z0-9_]*)\s*:\s*")
_PAGE_RANGE_NUM_RE = re.compile(r"(\d+)\s*[-–~]\s*(\d+)")


def _split_frontmatter(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    return text[3:end].strip()


def _parse_loose_yaml(block: str) -> dict:
    """`A: 1 B: 2 C: [x, y]` 같은 한 줄 다중키도 파싱."""
    fm: dict = {}
    if not block:
        return fm
    text = block.replace("\r", "")
    key_positions = [
        (m.start(), m.end(), m.group(1)) for m in _KEY_RE.finditer(text)
    ]
    for i, (s, e, k) in enumerate(key_positions):
        next_s = key_positions[i + 1][0] if i + 1 < len(key_positions) else len(text)
        raw_val = text[e:next_s].strip().rstrip(",").strip()
        fm[k] = raw_val
    return fm


def _claim_last_page(fm: dict) -> int | None:
    p = fm.get("포함_페이지")
    if p:
        nums = re.findall(r"\d+", str(p))
        if nums:
            return max(int(x) for x in nums)
    for key in ("페이지", "pdf_pages", "교재_pages"):
        p = fm.get(key)
        if p:
            m = _PAGE_RANGE_NUM_RE.search(str(p))
            if m:
                return int(m.group(2))
    return None


def _normalize_md_stem(md_stem: str) -> str:
    """`_p0001-0030` 같은 청크 접미사 제거 후 소문자."""
    return re.sub(r"_p\d+-\d+$", "", md_stem).lower()


def _resolve_pdf_for_md(md_path: str, fm: dict, pdf_index: dict[str, list[str]]) -> tuple[str | None, str]:
    """MD → PDF 매칭. (pdf_abs_path or None, source_label)."""
    # ① 명시적 pdf_원본
    pdf_orig = (fm.get("pdf_원본") or "").strip().strip("'\"")
    if pdf_orig and not pdf_orig.startswith("미확인"):
        # 줄바꿈/긴 본문이 섞여 들어왔으면 첫 줄만.
        pdf_orig_clean = pdf_orig.split("\n")[0].strip()
        cand = os.path.join(DRIVE_ROOT, pdf_orig_clean.replace("/", os.sep))
        if os.path.exists(cand) and cand.lower().endswith(".pdf"):
            return cand, "explicit_pdf_원본"
        # 명시는 있는데 못 찾음 → 토큰 매칭으로 폴백.

    # 토큰 추출
    md_stem = os.path.splitext(os.path.basename(md_path))[0]
    md_stem_norm = _normalize_md_stem(md_stem)
    md_tokens = set(re.split(r"[_\-\s]+", md_stem_norm))
    md_tokens.discard("")

    # ② 같은 폴더 PDF (sibling)
    md_dir = os.path.dirname(md_path)
    siblings = [
        os.path.join(md_dir, f) for f in os.listdir(md_dir)
        if f.lower().endswith(".pdf")
    ] if os.path.isdir(md_dir) else []
    best_sib, best_score = None, 0
    for sib in siblings:
        sib_stem = os.path.splitext(os.path.basename(sib))[0].lower()
        sib_tokens = set(re.split(r"[_\-\s]+", sib_stem))
        score = len(md_tokens & sib_tokens)
        if score > best_score:
            best_sib, best_score = sib, score
    if best_sib and best_score >= 2:
        return best_sib, "sibling_token_match"
    if best_sib and best_score == 1 and len(siblings) == 1:
        return best_sib, "sibling_only_pdf"

    # ③ 전역 PDF 인덱스에서 stem 정확 매칭
    if md_stem_norm in pdf_index:
        return pdf_index[md_stem_norm][0], "global_stem_exact"

    # ④ 전역 토큰 매칭(엄격)
    if len(md_tokens) >= 2:
        best_p, best_score = None, 0
        for stem, paths in pdf_index.items():
            sib_tokens = set(re.split(r"[_\-\s]+", stem))
            score = len(md_tokens & sib_tokens)
            if score > best_score:
                best_score, best_p = score, paths[0]
        if best_p and best_score >= 3:
            return best_p, f"global_token_match(score={best_score})"

    return None, "no_pdf_found"


# ----- 4) state I/O -----
def _load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[경고] {os.path.basename(path)} 로드 실패, 기본값 사용: {e}")
    return default


def _save_json_atomic(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_offset_table() -> dict:
    return _load_json(OFFSET_TABLE_PATH, {})


def save_offset_table(table: dict) -> None:
    _save_json_atomic(OFFSET_TABLE_PATH, table)


def load_match_table() -> dict:
    return _load_json(MATCH_TABLE_PATH, {})


def save_match_table(table: dict) -> None:
    _save_json_atomic(MATCH_TABLE_PATH, table)


# ----- 5) 메인 스캔 함수 -----
def scan_pdfs() -> list[str]:
    """SOURCE_DIRS 의 모든 PDF 를 수집 (제외 규칙 적용)."""
    pdfs: list[str] = []
    for root in SOURCE_DIRS:
        cnt_before = len(pdfs)
        pdfs.extend(_walk_pdfs(root))
        cnt_after = len(pdfs)
        print(f"  [{os.path.basename(root)}] PDF {cnt_after - cnt_before} 개  (누적 {cnt_after})")
    return sorted(set(pdfs))


def build_pdf_index(pdfs: list[str]) -> dict[str, list[str]]:
    """stem(소문자) → 절대경로 리스트."""
    idx: dict[str, list[str]] = {}
    for p in pdfs:
        stem = os.path.splitext(os.path.basename(p))[0].lower()
        idx.setdefault(stem, []).append(p)
    return idx


def scan_existing_mds() -> list[str]:
    if not os.path.isdir(EXISTING_MD_DIR):
        print(f"  [정보] EXISTING_MD_DIR 없음: {EXISTING_MD_DIR}")
        return []
    return sorted(glob.glob(os.path.join(EXISTING_MD_DIR, "**", "*.md"), recursive=True))


def build_match_and_offset_tables(
    pdfs: list[str],
    pdf_index: dict[str, list[str]],
    mds: list[str],
    *,
    skip_offset_for_existing: bool = True,
) -> tuple[dict, dict]:
    """PDF 별 entry 생성 + MD 매칭 결과 결합.

    반환:
        offset_table: { book_name: {pdf_path, total_pages, toc_offset, method, detected_at} }
        match_table : { book_name: {pdf_path, matched_mds, status} }
    """
    today = datetime.now().strftime("%Y-%m-%d")
    offset_table = load_offset_table()
    match_table: dict = {}

    # 1) MD 별로 PDF 후보 결정 → pdf_abs → md 리스트
    pdf_to_mds: dict[str, list[dict]] = {}
    md_resolutions: list[dict] = []
    n_no_fm = 0
    n_no_match = 0

    for i, md in enumerate(mds, 1):
        if i % 200 == 0:
            print(f"  [MD 매칭] {i}/{len(mds)}")
        try:
            with open(md, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception:
            continue
        block = _split_frontmatter(text)
        fm = _parse_loose_yaml(block) if block else {}
        if not block:
            n_no_fm += 1
        last_p = _claim_last_page(fm)
        pdf_abs, src = _resolve_pdf_for_md(md, fm, pdf_index)
        rel_md = os.path.relpath(md, DRIVE_ROOT).replace("\\", "/")
        if pdf_abs is None:
            n_no_match += 1
            md_resolutions.append({"md": rel_md, "pdf": None, "via": src, "last_page": last_p})
            continue
        md_resolutions.append({
            "md": rel_md,
            "pdf": os.path.relpath(pdf_abs, DRIVE_ROOT).replace("\\", "/"),
            "via": src,
            "last_page": last_p,
        })
        pdf_to_mds.setdefault(pdf_abs, []).append({
            "md": rel_md, "via": src, "last_page": last_p,
        })

    print(f"  [MD 매칭] 완료: 매칭={len(mds) - n_no_match}, 미매칭={n_no_match}, frontmatter 없음={n_no_fm}")

    # 2) PDF 별 entry — offset 자동 감지는 캐시. 이미 알려진 PDF 는 건드리지 않음.
    n_new_offset = 0
    n_skip_offset = 0
    for j, pdf in enumerate(pdfs, 1):
        if j % 100 == 0:
            print(f"  [PDF 처리] {j}/{len(pdfs)}")
        name = _book_name_from_pdf(pdf)
        rel = os.path.relpath(pdf, DRIVE_ROOT).replace("\\", "/")
        # 매칭 결과
        matched = pdf_to_mds.get(pdf, [])
        match_table[name] = {
            "pdf_path": rel,
            "matched_mds": [m["md"] for m in matched],
            "match_details": matched,
            "status": "matched" if matched else "unmatched",
        }
        # offset table — 기존에 등록되어 있고 같은 pdf_path 면 재감지 스킵.
        prev = offset_table.get(name)
        if skip_offset_for_existing and prev and prev.get("pdf_path") == rel:
            n_skip_offset += 1
            continue
        try:
            doc = fitz.open(pdf)
            total_pages = doc.page_count
            doc.close()
        except Exception as e:
            print(f"  [skip-pdf] 열기 실패: {pdf} → {e}")
            continue
        offset, method = detect_toc_offset(pdf)
        offset_table[name] = {
            "pdf_path": rel,
            "total_pages": total_pages,
            "toc_offset": offset,
            "detected_at": today,
            "method": method,
        }
        n_new_offset += 1

    print(f"  [PDF offset] 신규/갱신 {n_new_offset}, 캐시 스킵 {n_skip_offset}")

    save_offset_table(offset_table)
    save_match_table(match_table)
    print(f"  [저장] {OFFSET_TABLE_PATH}")
    print(f"  [저장] {MATCH_TABLE_PATH}")

    # 디버깅용 부속 결과물
    diag_path = os.path.join(STATE_DIR, "md_resolutions.json")
    _save_json_atomic(diag_path, md_resolutions)
    print(f"  [저장] {diag_path}  (MD 단위 매칭 진단)")

    return offset_table, match_table


def run_cell1(skip_offset_for_existing: bool = True) -> tuple[dict, dict]:
    """Cell 1 메인 함수. 반환=(offset_table, match_table)."""
    print("=" * 60)
    print("[Cell 1] PDF 스캔 시작")
    print("=" * 60)
    pdfs = scan_pdfs()
    print(f"\n[Cell 1] 총 PDF: {len(pdfs)}")
    if not pdfs:
        raise RuntimeError(
            "[Cell 1] PDF 가 한 개도 없습니다. SOURCE_DIRS 와 EXCLUDE_DIR_NAMES 를 확인하세요."
        )

    pdf_index = build_pdf_index(pdfs)
    print(f"[Cell 1] 고유 stem: {len(pdf_index)}")

    mds = scan_existing_mds()
    print(f"[Cell 1] 기존 .md: {len(mds)}")

    print(f"\n[Cell 1] (참고) 감사 결과 파일:")
    if os.path.exists(AUDIT_RESULT_PATH):
        try:
            with open(AUDIT_RESULT_PATH, "r", encoding="utf-8") as f:
                audit = json.load(f)
            s = audit.get("summary", {})
            print(f"  {AUDIT_RESULT_PATH}")
            for k, v in s.items():
                print(f"    {k}: {v}")
        except Exception as e:
            print(f"  [경고] audit 결과 로드 실패: {e}")
    else:
        print(f"  (없음) {AUDIT_RESULT_PATH}")

    print()
    offset_table, match_table = build_match_and_offset_tables(
        pdfs, pdf_index, mds, skip_offset_for_existing=skip_offset_for_existing,
    )

    # 결과 요약
    n_matched = sum(1 for v in match_table.values() if v["status"] == "matched")
    n_unmatched = sum(1 for v in match_table.values() if v["status"] == "unmatched")
    n_fallback = sum(1 for v in offset_table.values() if v.get("method") == "fallback")
    print(f"\n[Cell 1] 요약")
    print(f"  PDF 총 {len(offset_table)}  매칭(MD≥1) {n_matched}  미매칭 {n_unmatched}")
    print(f"  toc_offset auto {len(offset_table) - n_fallback}  fallback {n_fallback}")

    # 미매칭 PDF 일부 표시 (첫 10 개)
    unmatched_books = [k for k, v in match_table.items() if v["status"] == "unmatched"]
    if unmatched_books:
        print(f"\n[Cell 1] 미매칭 PDF 샘플 ({len(unmatched_books)} 개 중 앞 10):")
        for n in unmatched_books[:10]:
            print(f"  - {n}")

    return offset_table, match_table


# === Cell 1 실행 ===
offset_table, match_table = run_cell1()

# %% [markdown]
# # Cell 2: marker-pdf 추출 (OOM 방지 패치 적용)
#
# - 교재별로 청크 단위로 처리. 큰 PDF 는 자동으로 작은 청크 사용.
# - 결과 파일명: `{OUTPUT_DIR}/{교재명}/{교재명}_p{시작}-{끝}.md`
# - frontmatter 에 toc_offset 적용된 본문 페이지 범위, 매칭된 기존 .md 목록 기록.
# - `progress.json` 에 청크 단위로 완료 기록 → 재실행 시 이어서.
#
# ## OOM 방지
# - **converter 주기적 재생성**: `OCR_RECYCLE_EVERY` (기본 10권) 마다 converter 폐기·재생성.
# - **OOM 자동 회복**: 청크 실패 시 converter 재생성 후 1회 재시도.
# - **대용량 PDF 자동 스킵**: `OCR_SKIP_LARGE` (기본 1500p) 초과 PDF 는 별도 패스로 미루기.
# - **큰 PDF 청크 축소**: `OCR_LARGE_PDF_THRESHOLD` (기본 300p) 초과면 chunk_size=20.
# - **gc.collect() + torch 캐시 비우기**: 청크/교재 단위.
#
# ## 환경변수 (단권 단위 제한)
# - `OCR_SKIP_LARGE=1500`         : N 페이지 초과 PDF 스킵
# - `OCR_LARGE_PDF_THRESHOLD=300` : 이 이상이면 chunk_size 축소
# - `OCR_CHUNK_SIZE=50`           : 기본 청크 크기
# - `OCR_SMALL_CHUNK=20`          : 큰 PDF 용 청크 크기
# - `OCR_RECYCLE_EVERY=10`        : 몇 권마다 converter 재생성
#
# ## 환경변수 (배치 단위 제한 — 도달하면 깔끔히 종료, 다음 실행 때 이어서)
# - `OCR_MAX_BOOKS=N`              : 한 번에 처리할 교재 수
# - `OCR_MAX_TOTAL_PAGES=N`        : 누적 처리 페이지 합계
# - `OCR_MAX_TOTAL_MB=N`           : 누적 처리 PDF 용량(MB) 합계
# - `OCR_MAX_RUNTIME_MIN=N`        : 추출 루프 최대 실행 시간(분)
# - `OCR_MAX_RAM_GB=9`             : RSS 가 이 GB 도달 시 즉시 종료 (가장 직접적 OOM 방어, 권장)

# %%
def load_progress() -> dict:
    return _load_json(PROGRESS_PATH, {})


def save_progress(progress: dict) -> None:
    _save_json_atomic(PROGRESS_PATH, progress)


def _content_page(physical_page: int, toc_offset: int) -> int:
    """1-based 물리 페이지 → 본문 페이지. 목차 영역(<= offset)이면 음수/0 가능."""
    return physical_page - toc_offset


def _html_tables_to_markdown(md_text: str) -> str:
    """marker-pdf 가 표를 `<table>` HTML 로 내놓는 경우 markdownify 로 변환."""
    if "<table" not in md_text.lower():
        return md_text
    try:
        from markdownify import markdownify as md_convert
    except Exception:
        return md_text
    return md_convert(md_text, heading_style="ATX")


def _build_converter(page_range_str=None):
    """marker-pdf PdfConverter — page_range는 ConfigParser로 주입."""
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.config.parser import ConfigParser

    # artifact_dict는 한 번만 생성해서 함수 속성으로 캐시 (모델 재사용)
    if not hasattr(_build_converter, "_artifact_dict"):
        _build_converter._artifact_dict = create_model_dict()

    config_dict = {}
    if page_range_str:
        config_dict["page_range"] = page_range_str

    config_parser = ConfigParser(config_dict)
    return PdfConverter(
        config=config_parser.generate_config_dict(),
        artifact_dict=_build_converter._artifact_dict,
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),
    )


def _get_ram_gb() -> float:
    """현재 프로세스 RSS(GB). psutil 없으면 0.0 (체크 무력화)."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 ** 3)
    except Exception:
        return 0.0


def _free_memory(verbose: bool = False) -> float:
    """gc + torch 캐시 비우기. CPU 환경에서도 fragmentation 완화. 반환=현재 RSS(GB)."""
    import gc
    n = gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    rss_gb = _get_ram_gb()
    if verbose:
        print(f"  [mem] gc 회수={n}  RSS={rss_gb:.2f} GB")
    return rss_gb


def _recycle_converter(old_converter):
    """converter 폐기 + 메모리 비우기 + 새 converter 생성."""
    print(f"  [recycle] converter 재생성 시작 ...")
    t0 = datetime.now()
    try:
        del old_converter
    except Exception:
        pass
    _free_memory(verbose=True)
    new_conv = _build_converter()
    _free_memory(verbose=True)
    print(f"  [recycle] 완료 ({(datetime.now() - t0).total_seconds():.1f}s)")
    return new_conv


def _save_chunk(book_name: str, start_phys: int, end_phys: int, md_text: str,
                pdf_rel: str, toc_offset: int, matched_mds: list[str]) -> str:
    out_dir = os.path.join(OUTPUT_DIR, book_name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{book_name}_p{start_phys:04d}-{end_phys:04d}.md")
    cstart = _content_page(start_phys, toc_offset)
    cend = _content_page(end_phys, toc_offset)
    matched_yaml = "[]" if not matched_mds else "[" + ", ".join(f'"{m}"' for m in matched_mds[:20]) + "]"
    fm = (
        "---\n"
        f"source_pdf: \"{pdf_rel}\"\n"
        f"book_name: \"{book_name}\"\n"
        f"pdf_pages: \"{start_phys}-{end_phys}\"\n"
        f"content_pages: \"{cstart}-{cend}\"\n"
        f"toc_offset: {toc_offset}\n"
        f"matched_existing_mds: {matched_yaml}\n"
        f"extracted_at: \"{datetime.now().isoformat(timespec='seconds')}\"\n"
        "engine: \"marker-pdf\"\n"
        "---\n\n"
    )
    body = _html_tables_to_markdown(md_text)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(fm + body)
    os.replace(tmp, out_path)
    return out_path


_OOM_HINTS = ("out of memory", "cuda out of memory", "memoryerror", "killed", "cannot allocate")


def _is_oom_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return isinstance(exc, MemoryError) or any(h in msg for h in _OOM_HINTS)


def _convert_chunk(pdf_abs: str, start: int, end: int) -> str:
    """단일 청크 변환. 청크별 PdfConverter 새로 만들고 page_range는 ConfigParser로 주입.
    filepath만 전달 (page_range 키워드 인자 폐기). md_text 반환. 실패 시 예외 전파.
    """
    page_range_str = f"{start - 1}-{end - 1}"  # 0-based, 양 끝 포함
    converter = _build_converter(page_range_str=page_range_str)
    rendered = converter(pdf_abs)
    md_text = getattr(rendered, "markdown", None)
    if md_text is None and hasattr(rendered, "text_content"):
        md_text = rendered.text_content
    if md_text is None:
        md_text = str(rendered)
    return md_text


def extract_one_book(
    book_name: str,
    info: dict,
    converter_holder: list,
    *,
    chunk_size: int = 50,
    progress: dict | None = None,
    matched_mds: list[str] | None = None,
    free_after_chunks: int = 5,
    max_ram_gb: float | None = None,
    ram_state: dict | None = None,
) -> int:
    """단일 교재 추출. 반환=이번 실행에서 새로 저장한 청크 수.

    max_ram_gb 도달 시 청크 루프를 즉시 break하고 ram_state['hit'] = True 로 표시.
    호출 측이 사후 검사 후 main 루프도 break.
    """
    import traceback
    pdf_abs = os.path.join(DRIVE_ROOT, info["pdf_path"])
    if not os.path.exists(pdf_abs):
        print(f"  [skip] PDF 없음: {pdf_abs}")
        return 0
    total = int(info.get("total_pages", 0))
    if total <= 0:
        print(f"  [skip] total_pages=0: {book_name}")
        return 0
    toc = int(info.get("toc_offset", 0))
    pdf_rel = info["pdf_path"]
    matched_mds = matched_mds or []

    progress = progress if progress is not None else load_progress()
    book_state = progress.setdefault(book_name, {"completed_chunks": [], "updated_at": None})
    done = set(tuple(c) for c in book_state.get("completed_chunks", []))

    from tqdm.auto import tqdm
    chunks = []
    for start in range(1, total + 1, chunk_size):
        end = min(total, start + chunk_size - 1)
        chunks.append((start, end))
    todo = [c for c in chunks if c not in done]
    print(f"  PDF       : {pdf_abs}")
    print(f"  total_pages={total}  toc_offset={toc}  chunk_size={chunk_size}")
    print(f"  matched_md={len(matched_mds)}  chunks 전체 {len(chunks)} 완료 {len(done)} 남은 {len(todo)}")
    if not todo:
        print(f"  [skip] 모든 청크 이미 완료됨 ({book_name}).")
        return 0

    n_saved = 0
    for idx, (start, end) in enumerate(tqdm(todo, desc=f"{book_name}", leave=False), 1):
        print(f"  [{idx}/{len(todo)}] p{start}-{end} 처리 시작 ...")
        md_text = None
        try:
            md_text = _convert_chunk(pdf_abs, start, end)
        except Exception as e:
            if _is_oom_error(e):
                print(f"  [OOM] {book_name} p{start}-{end}: {type(e).__name__}: {e}")
                print(f"  [OOM] artifact_dict 캐시 비우고 재시도 ...")
                try:
                    if hasattr(_build_converter, "_artifact_dict"):
                        del _build_converter._artifact_dict
                    _free_memory(verbose=True)
                    md_text = _convert_chunk(pdf_abs, start, end)
                except Exception as e2:
                    print(f"  [OOM] 재시도 실패: {type(e2).__name__}: {e2}")
                    traceback.print_exc()
                    continue
            else:
                print(f"  [실패] {book_name} p{start}-{end}: {type(e).__name__}: {e}")
                traceback.print_exc()
                continue
        if md_text is None:
            continue
        out_path = _save_chunk(book_name, start, end, md_text, pdf_rel, toc, matched_mds)
        book_state["completed_chunks"].append([start, end])
        book_state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_progress(progress)
        n_saved += 1
        print(f"  [ok] p{start}-{end} → {os.path.relpath(out_path, DRIVE_ROOT)}  (md {len(md_text):,} chars)")
        # 일정 청크마다 부드럽게 메모리 회수 + RAM 체크.
        if idx % free_after_chunks == 0:
            rss = _free_memory()
            if max_ram_gb and rss >= max_ram_gb:
                print(f"  [ram-stop] RSS {rss:.2f}GB ≥ {max_ram_gb}GB → 권 도중 안전 종료")
                if ram_state is not None:
                    ram_state["hit"] = True
                    ram_state["rss"] = rss
                break
        elif max_ram_gb:
            # 매 청크마다 가벼운 체크 (gc 없이)
            rss = _get_ram_gb()
            if rss >= max_ram_gb:
                print(f"  [ram-stop] RSS {rss:.2f}GB ≥ {max_ram_gb}GB → 권 도중 안전 종료")
                if ram_state is not None:
                    ram_state["hit"] = True
                    ram_state["rss"] = rss
                break
    # 교재 끝마다 한 번 더 회수.
    _free_memory()
    return n_saved


def _env_int(name: str, default: int | None) -> int | None:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def run_extraction(
    offset_table: dict | None = None,
    match_table: dict | None = None,
    *,
    chunk_size: int | None = None,
    max_books: int | None = None,
    skip_large_pages: int | None = None,
    recycle_every: int | None = None,
    large_pdf_threshold: int | None = None,
    small_chunk: int | None = None,
    max_total_pages: int | None = None,
    max_total_mb: int | None = None,
    max_runtime_min: int | None = None,
    max_ram_gb: float | None = None,
) -> None:
    """offset_table 의 모든 교재를 추출. 재진입 안전 (progress.json 기반).

    OOM 방지 / 배치 한계:
      - skip_large_pages   : 이 페이지수 초과 PDF 는 건너뜀 (기본 1500).
      - large_pdf_threshold: 이 페이지수 초과면 chunk_size=small_chunk (기본 300/20).
      - recycle_every      : 이 권 수마다 converter 재생성 (기본 10).
      - max_books          : 한 번에 처리할 최대 권 수.
      - max_total_pages    : 누적 처리 페이지 합계 한계 (도달 시 깔끔히 종료).
      - max_total_mb       : 누적 처리 PDF 용량 합계(MB) 한계.
      - max_runtime_min    : 추출 루프 최대 실행 시간(분).
      - max_ram_gb         : 프로세스 RSS 가 이 GB 도달 시 즉시 종료 (가장 직접적 OOM 방어).
    """
    if offset_table is None:
        offset_table = load_offset_table()
    if match_table is None:
        match_table = load_match_table()
    print(f"[run_extraction] offset_table 항목 수: {len(offset_table)}")
    if not offset_table:
        print("[run_extraction] 빈 테이블 → Cell 1 의 run_cell1() 출력 확인.")
        return

    # 환경변수 → 인자 → 기본값 우선순위
    chunk_size = chunk_size if chunk_size is not None else _env_int("OCR_CHUNK_SIZE", 50)
    small_chunk = small_chunk if small_chunk is not None else _env_int("OCR_SMALL_CHUNK", 20)
    large_pdf_threshold = (large_pdf_threshold
                           if large_pdf_threshold is not None
                           else _env_int("OCR_LARGE_PDF_THRESHOLD", 300))
    recycle_every = recycle_every if recycle_every is not None else _env_int("OCR_RECYCLE_EVERY", 10)
    if max_books is None:
        max_books = _env_int("OCR_MAX_BOOKS", None)
    if skip_large_pages is None:
        skip_large_pages = _env_int("OCR_SKIP_LARGE", 1500)
    if max_total_pages is None:
        max_total_pages = _env_int("OCR_MAX_TOTAL_PAGES", None)
    if max_total_mb is None:
        max_total_mb = _env_int("OCR_MAX_TOTAL_MB", None)
    if max_runtime_min is None:
        max_runtime_min = _env_int("OCR_MAX_RUNTIME_MIN", None)
    if max_ram_gb is None:
        v = os.environ.get("OCR_MAX_RAM_GB")
        if v:
            try: max_ram_gb = float(v)
            except: max_ram_gb = None

    print(f"[run_extraction] 배치 한계 설정")
    print(f"  chunk_size={chunk_size}  small_chunk={small_chunk}  large_threshold={large_pdf_threshold}p")
    print(f"  skip_large_pages={skip_large_pages}p  recycle_every={recycle_every} 권")
    print(f"  max_books={max_books}  max_total_pages={max_total_pages}p"
          f"  max_total_mb={max_total_mb}MB  max_runtime_min={max_runtime_min}min"
          f"  max_ram_gb={max_ram_gb}GB")

    # 우선순위: 매칭된 PDF 먼저, 그 다음 미매칭. 같은 그룹 내 작은 페이지 먼저.
    items = list(offset_table.items())
    items.sort(key=lambda kv: (
        0 if match_table.get(kv[0], {}).get("matched_mds") else 1,
        int(kv[1].get("total_pages", 0) or 0),
        kv[0],
    ))
    if max_books:
        items = items[:max_books]
        print(f"[run_extraction] max_books={max_books} 적용 → 처리 대상 {len(items)} 권")

    print("[run_extraction] marker-pdf 모델 로딩 중 (CPU 면 수 분 소요)...")
    t0_model = datetime.now()
    converter_holder = [_build_converter()]
    print(f"[run_extraction] 모델 로딩 완료 ({(datetime.now() - t0_model).total_seconds():.1f}s).")
    _free_memory(verbose=True)

    progress = load_progress()
    t0_loop = datetime.now()
    n_total_saved = 0
    n_skipped_large = 0
    n_skipped_done = 0
    n_processed = 0
    sum_pages = 0
    sum_bytes = 0
    stop_reason: str | None = None

    def _runtime_min() -> float:
        return (datetime.now() - t0_loop).total_seconds() / 60.0

    for i, (name, info) in enumerate(items, 1):
        total_pages = int(info.get("total_pages", 0) or 0)

        # === 배치 한계 사전 체크 (다음 권 들어가기 전) ===
        if max_total_pages and sum_pages >= max_total_pages:
            stop_reason = f"누적 페이지 {sum_pages}p ≥ {max_total_pages}p"
            break
        if max_total_mb and sum_bytes / (1024 * 1024) >= max_total_mb:
            stop_reason = f"누적 용량 {sum_bytes / (1024 * 1024):.1f}MB ≥ {max_total_mb}MB"
            break
        if max_runtime_min and _runtime_min() >= max_runtime_min:
            stop_reason = f"누적 시간 {_runtime_min():.1f}min ≥ {max_runtime_min}min"
            break
        if max_ram_gb:
            rss = _get_ram_gb()
            if rss >= max_ram_gb:
                stop_reason = f"RSS {rss:.2f}GB ≥ {max_ram_gb}GB (다음 권 진입 전)"
                break

        # === 단권 보호 ===
        if skip_large_pages and total_pages > skip_large_pages:
            print(f"\n=== [{i}/{len(items)}] {name} === (skip: {total_pages}p > {skip_large_pages})")
            n_skipped_large += 1
            continue
        # 이미 모든 청크 완료된 권은 빠른 스킵 (모델 로딩 후 루프 첫 권부터 즉시 진행 위해)
        existing_done = set(tuple(c) for c in progress.get(name, {}).get("completed_chunks", []))
        expected_chunks = []
        eff_chunk_pre = small_chunk if (large_pdf_threshold and total_pages > large_pdf_threshold) else chunk_size
        for s in range(1, total_pages + 1, eff_chunk_pre):
            e = min(total_pages, s + eff_chunk_pre - 1)
            expected_chunks.append((s, e))
        if expected_chunks and all(c in existing_done for c in expected_chunks):
            n_skipped_done += 1
            continue

        # 큰 PDF 면 chunk_size 축소.
        eff_chunk = eff_chunk_pre
        print(f"\n=== [{i}/{len(items)}] {name} === ({total_pages}p, chunk={eff_chunk})")
        print(f"  누계 진행: 권 {n_processed} / 페이지 {sum_pages} / 용량 {sum_bytes/(1024*1024):.1f}MB"
              f" / 시간 {_runtime_min():.1f}min")
        matched = match_table.get(name, {}).get("matched_mds", [])
        # PDF 용량 측정 (가능하면 사전에)
        try:
            pdf_abs = os.path.join(DRIVE_ROOT, info["pdf_path"])
            pdf_size = os.path.getsize(pdf_abs) if os.path.exists(pdf_abs) else 0
        except Exception:
            pdf_size = 0
        ram_state = {"hit": False, "rss": 0.0}
        try:
            n = extract_one_book(
                name, info, converter_holder,
                chunk_size=eff_chunk, progress=progress,
                matched_mds=matched,
                max_ram_gb=max_ram_gb, ram_state=ram_state,
            )
        except Exception as e:
            print(f"  [book-fail] {type(e).__name__}: {e}")
            if _is_oom_error(e):
                print(f"  [book-fail] OOM 감지 → converter 재생성 후 다음 교재로 진행.")
                converter_holder[0] = _recycle_converter(converter_holder[0])
            n = 0
        n_total_saved += n
        n_processed += 1
        sum_pages += total_pages
        sum_bytes += pdf_size

        # 권 도중 RAM 한계 도달했으면 main 루프도 즉시 종료.
        if ram_state.get("hit"):
            stop_reason = f"권 도중 RAM 한계: RSS {ram_state['rss']:.2f}GB ≥ {max_ram_gb}GB"
            break

        # 권 끝 사후 RAM 체크 — 한 권 마치고 한계 근접이면 다음 권 안 시작.
        if max_ram_gb:
            rss = _get_ram_gb()
            if rss >= max_ram_gb:
                stop_reason = f"권 종료 후 RSS {rss:.2f}GB ≥ {max_ram_gb}GB"
                break

        if i == 1:
            book_dir = os.path.join(OUTPUT_DIR, name)
            n_files = len(glob.glob(os.path.join(book_dir, "*.md"))) if os.path.isdir(book_dir) else 0
            print(f"\n[중간 점검] 첫 교재 완료. 새로 저장 {n} 청크 / 누적 .md {n_files} 개.")
            print(f"          출력 위치: {book_dir}")

        # 주기적 converter 재생성 (메모리 leak 누적 방지).
        if recycle_every and n_processed % recycle_every == 0:
            print(f"\n[run_extraction] {n_processed} 권 처리 → 정기 converter 재생성")
            converter_holder[0] = _recycle_converter(converter_holder[0])

    print(f"\n[run_extraction] 추출 종료.")
    if stop_reason:
        print(f"  사유    : 배치 한계 도달 — {stop_reason}")
    print(f"  새 청크 : {n_total_saved}")
    print(f"  처리 권 : {n_processed}  (대용량 스킵 {n_skipped_large}, 이미 완료 {n_skipped_done})")
    print(f"  누적    : 페이지 {sum_pages}p / 용량 {sum_bytes/(1024*1024):.1f}MB"
          f" / 시간 {_runtime_min():.1f}min")


# === Cell 2 실행 ===
print("=" * 60)
print("[Cell 2] 추출 시작")
print("=" * 60)
print(f"[Cell 2] DRIVE_ROOT       = {DRIVE_ROOT}")
print(f"[Cell 2] OUTPUT_DIR       = {OUTPUT_DIR}        (exists={os.path.isdir(OUTPUT_DIR)})")
print(f"[Cell 2] OFFSET_TABLE_PATH= {OFFSET_TABLE_PATH}  (exists={os.path.exists(OFFSET_TABLE_PATH)})")
print(f"[Cell 2] MATCH_TABLE_PATH = {MATCH_TABLE_PATH}   (exists={os.path.exists(MATCH_TABLE_PATH)})")
print(f"[Cell 2] PROGRESS_PATH    = {PROGRESS_PATH}      (exists={os.path.exists(PROGRESS_PATH)})")
print(f"[Cell 2] TORCH_DEVICE     = {TORCH_DEVICE}")

_pre_offset = load_offset_table()
_pre_match = load_match_table()
print(f"[Cell 2] offset_table 항목 수: {len(_pre_offset)}")
print(f"[Cell 2] match_table  항목 수: {len(_pre_match)}")
for _k, _info in list(_pre_offset.items())[:5]:
    _abs = os.path.join(DRIVE_ROOT, _info.get("pdf_path", ""))
    _matched = len(_pre_match.get(_k, {}).get("matched_mds", []))
    print(f"  - {_k}  pages={_info.get('total_pages')}  matched_md={_matched}  PDF exists={os.path.exists(_abs)}")
if len(_pre_offset) > 5:
    print(f"  ... (총 {len(_pre_offset)} 개, 앞 5 개만 표시)")

if not _pre_offset:
    raise RuntimeError(
        "[Cell 2] offset_table 이 비어 있습니다. Cell 1 (run_cell1) 출력에서 "
        "PDF 미발견 메시지가 있었는지 확인하세요."
    )

run_extraction(_pre_offset, _pre_match)
print("\n[Cell 2] === 종료 ===")

# %% [markdown]
# # Cell 3: 추출 결과 요약
#
# - 교재별 진행률 표.
# - 누락된 청크 목록.
# - fallback(목차 감지 실패) 교재 → Cell 4 에서 수동 보정 안내.
# - MD 매칭 상태(매칭된 .md 개수)도 함께 표시.

# %%
def summarize(top_n: int = 50) -> None:
    table = load_offset_table()
    match = load_match_table()
    progress = load_progress()
    if not table:
        print("[Cell 3] offset_table 이 비어 있음.")
        return

    rows = []
    fallback_books: list[str] = []
    for name, info in table.items():
        total = int(info.get("total_pages", 0))
        toc = int(info.get("toc_offset", 0))
        method = info.get("method", "?")
        if method == "fallback":
            fallback_books.append(name)
        completed = progress.get(name, {}).get("completed_chunks", [])
        done_pages = sum((e - s + 1) for (s, e) in completed)
        pct = (100.0 * done_pages / total) if total else 0.0
        n_md = len(match.get(name, {}).get("matched_mds", []))
        # 누락 청크 = 50p 단위로 기대했지만 progress 에 없는 범위.
        expected = []
        for s in range(1, total + 1, 50):
            e = min(total, s + 49)
            expected.append((s, e))
        done_set = set(tuple(c) for c in completed)
        missing = [f"{s}-{e}" for (s, e) in expected if (s, e) not in done_set]
        miss_str = ",".join(missing[:3]) + (f"...(+{len(missing)-3})" if len(missing) > 3 else "")
        rows.append((pct, n_md, name, total, toc, method, miss_str))

    # 진행률 낮은 순으로 정렬, 상위 top_n 만 출력 (큰 데이터셋 대비).
    rows.sort()
    print(f"{'교재':50s}  {'pages':>6s}  {'offset':>6s}  {'method':>9s}  {'mds':>4s}  {'done%':>6s}  missing")
    print("-" * 120)
    for pct, n_md, name, total, toc, method, miss_str in rows[:top_n]:
        print(f"{name[:50]:50s}  {total:6d}  {toc:6d}  {method:>9s}  {n_md:4d}  {pct:6.1f}  {miss_str}")
    if len(rows) > top_n:
        print(f"... (총 {len(rows)} 권 중 진행률 낮은 {top_n} 만 표시)")

    if fallback_books:
        print(f"\n[안내] 목차 오프셋 자동 감지 실패 교재: {len(fallback_books)} 권")
        print(f"  Cell 4 에서 update_offset 으로 수정 가능. 앞 10:")
        for n in fallback_books[:10]:
            print(f"  - {n}  (현재 offset={table[n]['toc_offset']})")


summarize()

# %% [markdown]
# # Cell 4: 수동 오프셋 수정 (선택)
#
# 사용 예:
# ```python
# update_offset("1민사__30송영곤_기본민법__민법_송영곤_기본민법", toc_offset=22)
# ```
# 수정 후, 이미 추출된 해당 교재의 마크다운 frontmatter 의 `toc_offset` 과
# `content_pages` 값을 일괄 갱신한다 (본문 내용은 건드리지 않음).

# %%
_FM_TOC_RE = re.compile(r"^toc_offset:\s*-?\d+\s*$", re.MULTILINE)
_FM_CPAGES_RE = re.compile(r"^content_pages:\s*\"[^\"]*\"\s*$", re.MULTILINE)
_FM_PPAGES_RE = re.compile(r"^pdf_pages:\s*\"(\d+)-(\d+)\"\s*$", re.MULTILINE)


def _rewrite_frontmatter(md_path: str, new_offset: int) -> bool:
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return False
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---\n", 4)
    if end < 0:
        return False
    head = text[: end + 5]
    body = text[end + 5 :]
    m = _FM_PPAGES_RE.search(head)
    if not m:
        return False
    s, e = int(m.group(1)), int(m.group(2))
    cs, ce = s - new_offset, e - new_offset
    head = _FM_TOC_RE.sub(f"toc_offset: {new_offset}", head)
    head = _FM_CPAGES_RE.sub(f"content_pages: \"{cs}-{ce}\"", head)
    tmp = md_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(head + body)
    os.replace(tmp, md_path)
    return True


def update_offset(book_name: str, *, toc_offset: int) -> None:
    table = load_offset_table()
    if book_name not in table:
        print(f"[Cell 4] 교재 없음: {book_name}")
        print("  사용 가능한 교재 목록(앞 30):")
        for n in list(table.keys())[:30]:
            print(f"    - {n}")
        return
    table[book_name]["toc_offset"] = int(toc_offset)
    table[book_name]["method"] = "manual"
    table[book_name]["detected_at"] = datetime.now().strftime("%Y-%m-%d")
    save_offset_table(table)
    print(f"[Cell 4] offset_table 갱신: {book_name} → toc_offset={toc_offset}")

    book_dir = os.path.join(OUTPUT_DIR, book_name)
    if not os.path.isdir(book_dir):
        print("  (아직 추출된 파일 없음 — frontmatter 재작성 스킵)")
        return
    n_ok = 0
    for md in sorted(glob.glob(os.path.join(book_dir, "*.md"))):
        if _rewrite_frontmatter(md, toc_offset):
            n_ok += 1
    print(f"  frontmatter 재작성 완료: {n_ok} 파일")


# 실행 예시는 주석으로:
# update_offset("1민사__30송영곤_기본민법__민법_송영곤_기본민법", toc_offset=22)
print("[Cell 4] update_offset(book_name, toc_offset=N) 으로 수동 보정 가능.")
