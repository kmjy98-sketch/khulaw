# %% [markdown]
# # OCR Compare v2 — 기존 md vs marker-pdf 추출 md 비교 + corrections.jsonl 생성
#
# 설계 원칙:
# - 비교/교정 후보 생성 전용. 추출은 ocr_extract_v2.ipynb 가 담당.
# - 기존 md(`sync/_교재원문/`) 와 새 추출 md(`sync/_ocr_extracted/`) 를 paired diff.
# - diff 항목을 3-Class 로 분류 → corrections.jsonl 로 저장.
# - 코랩이 끊겨도 Drive 의 progress 기반으로 재진입 안전.
#
# 셀 구성:
# - Cell 0a: 패키지 설치 + 자동 재시작
# - Cell 0b: import + Drive 마운트 + 경로 설정
# - Cell 1 : 파일 매칭 (offset_table.source_pdf + 토큰 fallback) → match_table.json
# - Cell 2 : Diff + 3-Class 분류 + corrections.jsonl 생성
# - Cell 3 : 비교 결과 요약 (CER, Class 분포, 표 채택 건수)
# - Cell 4 : 조문/판례 번호 검증 대상 추출 → verification_targets.json
#
# 3-Class 정의 (legal_regex.is_anchor_line 기반):
#   Class 1 (text)    : 일반 텍스트 — LLM 교정 대상
#   Class 2 (anchor)  : 조문(§/제X조), 사건번호, 한자 — LLM 제외, 별도 검증
#   Class 3 (orphan)  : 한쪽에만 존재 (정보 부족)

# %% [markdown]
# # Cell 0a: 패키지 설치 + 자동 재시작
#
# 첫 실행: 설치 후 Colab 자동 재시작. 재시작 후 **[런타임 > 모두 실행]** 다시 누르세요.
# 두 번째 실행: 이미 설치되어 있으면 스킵.
#
# 메모:
# - `dinglehopper` 는 OCR CER 평가 표준 라이브러리. (https://github.com/qurator-spk/dinglehopper)
# - `markdownify` 는 표 비교 시 HTML 표 정규화에 사용 (Cell 2).
# - marker-pdf / transformers 는 추출 노트북 전용 — 이 노트북은 설치하지 않는다.

# %%
import os, subprocess, sys, tempfile

INSTALL_FLAG = os.path.join(tempfile.gettempdir(), "ocr_compare_v2_installed")
_IS_COLAB = "google.colab" in sys.modules or os.path.exists("/content")

PKGS = [
    "dinglehopper",
    "markdownify",
    "tqdm",
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

# %%
import os, sys, json, re, glob, difflib
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict


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

DRIVE_ROOT       = _resolve_drive_root()
SYNC_ROOT        = os.path.join(DRIVE_ROOT, "sync")
SOURCE_DIR       = os.path.join(SYNC_ROOT, "_교재원문")
OUTPUT_DIR       = os.path.join(SYNC_ROOT, "_ocr_extracted")
STATE_DIR        = os.path.join(DRIVE_ROOT, ".auto-memory", "ocr_state")
CORRECTIONS_DIR  = os.path.join(STATE_DIR, "corrections")

os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(CORRECTIONS_DIR, exist_ok=True)

OFFSET_TABLE_PATH      = os.path.join(STATE_DIR, "offset_table.json")
PROGRESS_PATH          = os.path.join(STATE_DIR, "progress.json")
MATCH_TABLE_PATH       = os.path.join(STATE_DIR, "match_table.json")
VERIFICATION_TARGETS   = os.path.join(STATE_DIR, "verification_targets.json")
COMPARE_PROGRESS_PATH  = os.path.join(STATE_DIR, "compare_progress.json")


def _load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[경고] 로드 실패 {path}: {e}")
    return default


def _save_json(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


offset_table     = _load_json(OFFSET_TABLE_PATH, {})
extract_progress = _load_json(PROGRESS_PATH, {})

print(f"[Cell 0b] DRIVE_ROOT       = {DRIVE_ROOT}")
print(f"[Cell 0b] SOURCE_DIR       = {SOURCE_DIR}")
print(f"[Cell 0b] OUTPUT_DIR       = {OUTPUT_DIR}")
print(f"[Cell 0b] STATE_DIR        = {STATE_DIR}")
print(f"[Cell 0b] CORRECTIONS_DIR  = {CORRECTIONS_DIR}")
print(f"[Cell 0b] offset_table     교재 수: {len(offset_table)}")
print(f"[Cell 0b] extract_progress 교재 수: {len(extract_progress)}")

# legal_regex 임포트 (anchor 분류용). 코랩에서는 Drive 경로를 PYTHONPATH 에 추가.
_LIB_DIR = os.path.join(DRIVE_ROOT, ".agent", "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)
try:
    from legal_regex import (
        is_anchor_line,
        LAW_ARTICLE,
        SUPREME_COURT,
        CONSTITUTIONAL,
        HANJA_BLOCK,
        CASE_CODE_WHITELIST,
    )
    print("[Cell 0b] legal_regex 임포트 OK")
except Exception as e:
    print(f"[경고] legal_regex 임포트 실패: {e} — 인라인 fallback 사용.")
    _LAW_ARTICLE         = re.compile(r'제\d+조(?:의\d+)?|§\d{2,}')
    _SUPREME_COURT       = re.compile(
        r'대판\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}'
        r'|대법원\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}'
        r'|\b\d{2,4}\s*다\s*[가-힣]{0,5}\d{1,8}\b'
        r'|\b\d{2,4}\s*[가-힣]{1,4}\s*\d{1,8}\b'
    )
    _CONSTITUTIONAL      = re.compile(
        r'헌재\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}'
        r'|\d{4}\s*헌\s*[마바사아자]\s*\d{1,5}'
    )
    _HANJA_BLOCK         = re.compile(r'[一-鿿㐀-䶿豈-﫿]+')
    _CASE_CODE_WHITELIST = re.compile(
        r'\d{2,4}(?:다|카|노|고|합|단|마|바|사|아|자|차|타|파|하)[가-힣]{0,3}\d{1,8}'
    )
    LAW_ARTICLE         = _LAW_ARTICLE
    SUPREME_COURT       = _SUPREME_COURT
    CONSTITUTIONAL      = _CONSTITUTIONAL
    HANJA_BLOCK         = _HANJA_BLOCK
    CASE_CODE_WHITELIST = _CASE_CODE_WHITELIST
    _ALL_ANCHORS = [LAW_ARTICLE, SUPREME_COURT, CONSTITUTIONAL,
                    HANJA_BLOCK, CASE_CODE_WHITELIST]
    def is_anchor_line(text: str) -> bool:
        return any(p.search(text) for p in _ALL_ANCHORS)


# %% [markdown]
# # Cell 1: 파일 매칭 + match_table.json
#
# 매칭 전략:
# 1. 새 추출 md(`OUTPUT_DIR/{book_name}/{book_name}_pSSSS-EEEE.md`) 의 frontmatter
#    → `source_pdf` 추출 → 같은 PDF 에서 추출된 기존 md 후보를 우선 매칭.
# 2. fallback: 파일명 토큰(언더바 분해, 길이≥2 토큰) 교집합이 3 이상이면 매칭.
# 3. 페이지 범위(`pdf_pages: SSSS-EEEE`) 가 동일하면 1:1 pair, 아니면 중첩 비율로 매칭.
#
# 결과: `match_table.json` (book 단위 — 새 추출 chunk → 기존 md 경로 리스트).

# %%
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_PAGE_RANGE_RE  = re.compile(r"_p(\d+)-(\d+)\.(?:md|qmd)$")
_TOKEN_RE       = re.compile(r"[A-Za-z0-9가-힣]{2,}")


def _read_frontmatter(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(4096)
    except Exception:
        return {}
    m = _FRONTMATTER_RE.match(head)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        fm[k] = v
    return fm


def _strip_frontmatter(text: str) -> str:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return text
    return text[m.end():]


def _stem_tokens(stem: str) -> set:
    s = stem.lower()
    s = re.sub(r"_p\d+-\d+$", "", s)  # 페이지 범위 토큰 제거
    return set(t for t in _TOKEN_RE.findall(s) if len(t) >= 2)


def _parse_page_range(filename: str) -> tuple:
    m = _PAGE_RANGE_RE.search(filename)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def _scan_existing_md() -> list:
    """sync/_교재원문/ 하위 모든 .md 를 읽어 (path, frontmatter, page_range, tokens) 튜플 리스트로 반환."""
    out = []
    if not os.path.isdir(SOURCE_DIR):
        return out
    for md in sorted(glob.glob(os.path.join(SOURCE_DIR, "**", "*.md"), recursive=True)):
        # 백업/trash 폴더 제외 (CLAUDE.md #16, handoff_ocr_cleanup_2026-04-21 동일)
        rel = os.path.relpath(md, DRIVE_ROOT).replace("\\", "/")
        if any(p in rel for p in ("/_trash/", "/_backup", "/_재추출", "/_재추출본",
                                  "/_raw/", "/_src/", "/_orig/")):
            continue
        fm = _read_frontmatter(md)
        pr = _parse_page_range(os.path.basename(md))
        if pr is None:
            # frontmatter 의 pdf_pages 를 fallback 으로 사용
            ppages = fm.get("pdf_pages", "")
            mm = re.match(r"(\d+)-(\d+)", ppages)
            if mm:
                pr = (int(mm.group(1)), int(mm.group(2)))
        toks = _stem_tokens(os.path.basename(md))
        out.append({
            "path": md,
            "rel": rel,
            "fm": fm,
            "page_range": pr,
            "tokens": toks,
        })
    return out


def _scan_new_md() -> list:
    out = []
    if not os.path.isdir(OUTPUT_DIR):
        return out
    for md in sorted(glob.glob(os.path.join(OUTPUT_DIR, "**", "*.md"), recursive=True)):
        fm = _read_frontmatter(md)
        pr = _parse_page_range(os.path.basename(md))
        if pr is None:
            ppages = fm.get("pdf_pages", "")
            mm = re.match(r"(\d+)-(\d+)", ppages)
            if mm:
                pr = (int(mm.group(1)), int(mm.group(2)))
        # 책 식별자: 부모 폴더명 == book_name 가정 (ocr_extract_v2 규칙)
        book_name = os.path.basename(os.path.dirname(md))
        toks = _stem_tokens(book_name)
        out.append({
            "path": md,
            "rel": os.path.relpath(md, DRIVE_ROOT).replace("\\", "/"),
            "book": book_name,
            "fm": fm,
            "page_range": pr,
            "tokens": toks,
        })
    return out


def _overlap_pages(a: tuple, b: tuple) -> int:
    if a is None or b is None:
        return 0
    s = max(a[0], b[0])
    e = min(a[1], b[1])
    return max(0, e - s + 1)


def build_match_table() -> dict:
    new_files      = _scan_new_md()
    existing_files = _scan_existing_md()
    print(f"[Cell 1] 새 추출 md  : {len(new_files)}")
    print(f"[Cell 1] 기존 md     : {len(existing_files)}")

    # 1차 인덱스: source_pdf basename → 기존 md
    by_source_pdf = defaultdict(list)
    for ex in existing_files:
        sp = ex["fm"].get("source_pdf") or ex["fm"].get("pdf_path") or ""
        if sp:
            by_source_pdf[os.path.basename(sp)].append(ex)

    matches = {}                # book → list of (new_path, [existing_path,...], reason)
    n_pdf, n_token, n_none = 0, 0, 0
    for nf in new_files:
        new_src = (nf["fm"].get("source_pdf") or "").strip()
        new_basename = os.path.basename(new_src) if new_src else ""

        candidates = []
        reason = None

        # 1) source_pdf 직매칭
        if new_basename and new_basename in by_source_pdf:
            candidates = by_source_pdf[new_basename]
            reason = "source_pdf"

        # 2) offset_table 의 pdf_path 비교 (basename)
        if not candidates and nf["book"] in offset_table:
            tbl_pdf = offset_table[nf["book"]].get("pdf_path", "")
            tbl_basename = os.path.basename(tbl_pdf)
            if tbl_basename and tbl_basename in by_source_pdf:
                candidates = by_source_pdf[tbl_basename]
                reason = "offset_table.pdf_path"

        # 3) 토큰 fallback (>=3 토큰 겹침)
        if not candidates:
            best, best_score = None, 0
            for ex in existing_files:
                ov = len(nf["tokens"] & ex["tokens"])
                if ov > best_score and ov >= 3:
                    best_score, best = ov, ex
            if best is not None:
                # 같은 폴더의 다른 청크들도 함께 묶는다.
                folder = os.path.dirname(best["path"])
                candidates = [ex for ex in existing_files
                              if os.path.dirname(ex["path"]) == folder
                              and len(nf["tokens"] & ex["tokens"]) >= 3]
                reason = f"token_overlap={best_score}"

        # 페이지 범위가 잡히면 페어 단위로 좁힌다.
        pair_paths = []
        if nf["page_range"] is not None:
            for ex in candidates:
                if _overlap_pages(nf["page_range"], ex["page_range"]) > 0:
                    pair_paths.append(ex["path"])
        # 페이지 좁힘이 비어 있으면 후보 전체를 그대로 (전체 길이 비교용).
        if not pair_paths:
            pair_paths = [ex["path"] for ex in candidates]

        bucket = matches.setdefault(nf["book"], [])
        bucket.append({
            "new_path": nf["path"],
            "new_rel": nf["rel"],
            "page_range": nf["page_range"],
            "existing_paths": pair_paths,
            "match_reason": reason or "none",
        })
        if reason and reason.startswith("source_pdf"):
            n_pdf += 1
        elif reason and "token" in reason:
            n_token += 1
        elif reason and reason.startswith("offset_table"):
            n_pdf += 1
        else:
            n_none += 1

    table = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "stats": {
            "new_md_total"   : len(new_files),
            "matched_pdf"    : n_pdf,
            "matched_token"  : n_token,
            "unmatched"      : n_none,
        },
        "books": matches,
    }
    _save_json(MATCH_TABLE_PATH, table)
    print(f"[Cell 1] 매칭: source_pdf={n_pdf}  token_fallback={n_token}  unmatched={n_none}")
    print(f"[Cell 1] 저장: {os.path.relpath(MATCH_TABLE_PATH, DRIVE_ROOT)}")
    return table


print("[Cell 1] 시작 — 파일 매칭")
# 사전 점검: 새 추출 / 기존 md 폴더 존재 여부
if not os.path.isdir(SOURCE_DIR):
    print(f"[Cell 1] [경고] SOURCE_DIR 없음: {SOURCE_DIR} — 기존 md 가 없으면 비교 불가.")
if not os.path.isdir(OUTPUT_DIR):
    print(f"[Cell 1] [경고] OUTPUT_DIR 없음: {OUTPUT_DIR} — ocr_extract_v2.ipynb 를 먼저 실행하세요.")
match_table = build_match_table()
_n_books = len(match_table.get("books", {}))
_n_pairs = sum(len(v) for v in match_table.get("books", {}).values())
print(f"[Cell 1] 종료 — 교재 {_n_books}개, 페어 후보 {_n_pairs}개. (다음: Cell 2)")

# %% [markdown]
# # Cell 2: Diff + corrections.jsonl 생성
#
# 처리 단위: book (`match_table.books[book]`).
# 청크 단위로 진행:
# 1. 새 추출 md 본문 / 기존 md 본문 로드 → frontmatter 제거.
# 2. 표(`|...|...|`) 블록과 일반 텍스트 블록을 분리.
# 3. 표: 행/열 개수 비교 → 불일치 시 `class=2_table` 로 통째 채택 후보 등록.
# 4. 일반 텍스트: `difflib.SequenceMatcher` 의 `get_opcodes()` 로 라인 정렬 → 라인별 diff.
# 5. 각 diff 라인을 3-Class 분류:
#    Class 1 (text)   — anchor 없음 → LLM 교정 대상
#    Class 2 (anchor) — 조문/판례번호/한자 포함 → LLM 제외, 별도 검증
#    Class 3 (orphan) — replace/insert/delete 중 한쪽이 빈 라인
# 6. CER (Character Error Rate) 계산 — dinglehopper 가 있으면 사용, 없으면 levenshtein/길이.
#
# 출력: `CORRECTIONS_DIR/{book}.jsonl` — 한 줄당 한 diff 항목.
# 진행 상태: `compare_progress.json` (book 단위 페이지/CER 누적).

# %%
try:
    from dinglehopper.character_error_rate import character_error_rate
    _HAS_DINGLE = True
except Exception:
    _HAS_DINGLE = False


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    m, n = len(a), len(b)
    if m < n:
        a, b = b, a
        m, n = n, m
    prev = list(range(n + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * n
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur[j] = min(ins, dele, sub)
        prev = cur
    return prev[n]


def cer(a: str, b: str) -> float:
    if not a and not b:
        return 0.0
    if _HAS_DINGLE:
        try:
            return float(character_error_rate(a, b))
        except Exception:
            pass
    base = max(len(a), 1)
    return _levenshtein(a, b) / base


# 표 라인: `| ... |` 시작이거나 `|---|---|` 구분자.
_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE  = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def _split_blocks(lines: list) -> list:
    """라인 시퀀스를 (kind, start_idx, end_idx, lines) 블록으로 나눈다.

    kind ∈ {"text", "table"}. table 은 연속된 `_TABLE_LINE_RE` 라인 묶음.
    """
    blocks = []
    i, n = 0, len(lines)
    while i < n:
        if _TABLE_LINE_RE.match(lines[i]):
            j = i
            while j < n and _TABLE_LINE_RE.match(lines[j]):
                j += 1
            blocks.append(("table", i, j - 1, lines[i:j]))
            i = j
        else:
            j = i
            while j < n and not _TABLE_LINE_RE.match(lines[j]):
                j += 1
            blocks.append(("text", i, j - 1, lines[i:j]))
            i = j
    return blocks


def _table_shape(block_lines: list) -> tuple:
    """(rows, cols) — 구분자 라인은 제외."""
    rows = [l for l in block_lines if not _TABLE_SEP_RE.match(l)]
    if not rows:
        return (0, 0)
    cols = max(l.count("|") - 1 for l in rows) if rows else 0
    return (len(rows), max(0, cols))


def _classify_diff_line(old: str, new: str) -> tuple:
    """
    Returns (cls, anchor_count)
        cls ∈ {1, 2, 3}
        anchor_count: anchor 패턴 hit 수 (LAW_ARTICLE + SUPREME_COURT + CONSTITUTIONAL + HANJA_BLOCK)
    """
    if not old.strip() or not new.strip():
        return (3, 0)
    a_count = (
        len(LAW_ARTICLE.findall(old)) + len(LAW_ARTICLE.findall(new)) +
        len(SUPREME_COURT.findall(old)) + len(SUPREME_COURT.findall(new)) +
        len(CONSTITUTIONAL.findall(old)) + len(CONSTITUTIONAL.findall(new)) +
        len(HANJA_BLOCK.findall(old)) + len(HANJA_BLOCK.findall(new))
    )
    if is_anchor_line(old) or is_anchor_line(new):
        return (2, a_count)
    return (1, 0)


_ANCHOR_MASK_OPEN  = "<<ANCHOR>>"
_ANCHOR_MASK_CLOSE = "<</ANCHOR>>"


def _mask_anchors(text: str) -> str:
    """anchor 패턴을 LLM 교정 대상에서 보호하기 위해 토큰화. 반환은 마스킹된 라인."""
    masked = text
    for pat in (LAW_ARTICLE, SUPREME_COURT, CONSTITUTIONAL, HANJA_BLOCK,
                CASE_CODE_WHITELIST):
        masked = pat.sub(lambda m: f"{_ANCHOR_MASK_OPEN}{m.group(0)}{_ANCHOR_MASK_CLOSE}", masked)
    return masked


def _confidence(cls: int, c: float, anchor_n: int) -> float:
    """간이 신뢰도. text 는 (1-CER) 기반, anchor 는 보존(=1.0), orphan 은 0.5."""
    if cls == 3:
        return 0.5
    if cls == 2:
        return 1.0 if anchor_n > 0 else 0.9
    # text: CER 0.0 → 1.0, CER ≥ 0.5 → 0.5
    return max(0.5, min(1.0, 1.0 - c))


def _diff_text_block(old_lines: list, new_lines: list,
                     old_offset: int, new_offset: int,
                     old_path: str, page: int) -> list:
    items = []
    sm = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            length = max(i2 - i1, j2 - j1)
            for k in range(length):
                old_ln = old_lines[i1 + k] if i1 + k < i2 else ""
                new_ln = new_lines[j1 + k] if j1 + k < j2 else ""
                cls, a_count = _classify_diff_line(old_ln, new_ln)
                c = cer(old_ln, new_ln) if (old_ln and new_ln) else (1.0 if not old_ln or not new_ln else 0.0)
                items.append({
                    "file"        : old_path,
                    "page"        : page,
                    "line"        : old_offset + i1 + k,
                    "new_line"    : new_offset + j1 + k,
                    "class"       : cls,
                    "kind"        : "text",
                    "old"         : old_ln,
                    "new"         : new_ln,
                    "old_masked"  : _mask_anchors(old_ln) if cls == 2 else None,
                    "new_masked"  : _mask_anchors(new_ln) if cls == 2 else None,
                    "cer"         : round(c, 4),
                    "confidence"  : round(_confidence(cls, c, a_count), 4),
                    "anchor_count": a_count,
                    "diff_size"   : abs(len(old_ln) - len(new_ln)),
                    "op"          : tag,
                    "status"      : "pending",
                    "verified"    : None,
                })
        elif tag in ("insert", "delete"):
            if tag == "insert":
                src_lines, src_off, side = new_lines[j1:j2], new_offset + j1, "new_only"
            else:
                src_lines, src_off, side = old_lines[i1:i2], old_offset + i1, "old_only"
            for k, ln in enumerate(src_lines):
                a_count = (
                    len(LAW_ARTICLE.findall(ln)) +
                    len(SUPREME_COURT.findall(ln)) +
                    len(CONSTITUTIONAL.findall(ln)) +
                    len(HANJA_BLOCK.findall(ln))
                )
                items.append({
                    "file"        : old_path,
                    "page"        : page,
                    "line"        : src_off + k,
                    "class"       : 3,
                    "kind"        : "orphan",
                    "side"        : side,
                    "old"         : ln if side == "old_only" else "",
                    "new"         : ln if side == "new_only" else "",
                    "cer"         : 1.0,
                    "confidence"  : 0.5,
                    "anchor_count": a_count,
                    "diff_size"   : len(ln),
                    "op"          : tag,
                    "status"      : "pending",
                    "verified"    : None,
                })
    return items


def _diff_table_block(old_block: list, new_block: list,
                      old_offset: int, new_offset: int,
                      old_path: str, page: int) -> list:
    """표 비교: 행/열 shape 비교 → 불일치 시 통째 채택 후보 1건. 일치 시 행 단위 텍스트 diff 위임."""
    o_rows, o_cols = _table_shape(old_block)
    n_rows, n_cols = _table_shape(new_block)
    if (o_rows, o_cols) == (n_rows, n_cols) and old_block == new_block:
        return []
    if (o_rows, o_cols) != (n_rows, n_cols):
        return [{
            "file"        : old_path,
            "page"        : page,
            "line"        : old_offset,
            "class"       : 2,
            "kind"        : "table_adopt",
            "old"         : "\n".join(old_block),
            "new"         : "\n".join(new_block),
            "old_shape"   : list((o_rows, o_cols)),
            "new_shape"   : list((n_rows, n_cols)),
            "cer"         : cer("\n".join(old_block), "\n".join(new_block)),
            "confidence"  : 0.95,
            "anchor_count": 0,
            "diff_size"   : abs(sum(len(l) for l in old_block) -
                                sum(len(l) for l in new_block)),
            "op"          : "table_replace",
            "status"      : "pending",
            "verified"    : None,
        }]
    # shape 동일이지만 내용 차이 → 라인 단위 diff (text 처리와 동일)
    return _diff_text_block(old_block, new_block, old_offset, new_offset, old_path, page)


def _page_from_frontmatter(fm: dict) -> int:
    pp = fm.get("pdf_pages", "")
    m = re.match(r"(\d+)", pp)
    return int(m.group(1)) if m else 0


def _frontmatter_line_count(text: str) -> int:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return 0
    return text[:m.end()].count("\n")


def diff_pair(new_md: str, old_md: str) -> list:
    """한 쌍의 md 파일을 비교하고 corrections 항목 리스트를 반환.

    `line` / `new_line` 은 **파일 전체** 기준 0-based 인덱스 (frontmatter 포함).
    apply_corrections.py 가 라인 단위로 직접 접근할 수 있게 하기 위함.
    """
    try:
        with open(new_md, "r", encoding="utf-8") as f:
            new_text = f.read()
        with open(old_md, "r", encoding="utf-8") as f:
            old_text = f.read()
    except Exception as e:
        print(f"  [경고] 읽기 실패: {e}")
        return []

    new_fm  = _read_frontmatter(new_md) or {}
    page    = _page_from_frontmatter(new_fm)

    old_fm_lines = _frontmatter_line_count(old_text)
    new_fm_lines = _frontmatter_line_count(new_text)
    new_body = _strip_frontmatter(new_text).splitlines()
    old_body = _strip_frontmatter(old_text).splitlines()

    new_blocks = _split_blocks(new_body)
    old_blocks = _split_blocks(old_body)

    items = []
    # 블록을 순서대로 페어링 (kind 같은 것끼리 묶고, 부족하면 빈 블록과 비교).
    # 파일 전체 라인 인덱스 = frontmatter_lines + body_offset
    bi, bj = 0, 0
    while bi < len(old_blocks) or bj < len(new_blocks):
        ob = old_blocks[bi] if bi < len(old_blocks) else None
        nb = new_blocks[bj] if bj < len(new_blocks) else None
        if ob is None:
            items.extend(_diff_text_block(
                [], nb[3], old_fm_lines, new_fm_lines + nb[1], old_md, page))
            bj += 1
            continue
        if nb is None:
            items.extend(_diff_text_block(
                ob[3], [], old_fm_lines + ob[1], new_fm_lines, old_md, page))
            bi += 1
            continue
        if ob[0] == "table" and nb[0] == "table":
            items.extend(_diff_table_block(
                ob[3], nb[3],
                old_fm_lines + ob[1], new_fm_lines + nb[1],
                old_md, page))
            bi += 1; bj += 1
        elif ob[0] == "text" and nb[0] == "text":
            items.extend(_diff_text_block(
                ob[3], nb[3],
                old_fm_lines + ob[1], new_fm_lines + nb[1],
                old_md, page))
            bi += 1; bj += 1
        else:
            # 종류 불일치 → 한쪽을 비교 대상으로 두고 진행
            if ob[0] == "table":
                items.extend(_diff_table_block(
                    ob[3], [], old_fm_lines + ob[1], new_fm_lines, old_md, page))
                bi += 1
            else:
                items.extend(_diff_table_block(
                    [], nb[3], old_fm_lines, new_fm_lines + nb[1], old_md, page))
                bj += 1
    return items


def run_compare(only_books: list = None) -> dict:
    """match_table 의 모든(또는 지정) book 을 비교하고 corrections.jsonl 갱신."""
    table = _load_json(MATCH_TABLE_PATH, {"books": {}})
    progress = _load_json(COMPARE_PROGRESS_PATH, {})
    summary = {}

    books = table.get("books", {})
    if only_books:
        books = {k: v for k, v in books.items() if k in only_books}

    try:
        from tqdm.auto import tqdm
    except Exception:
        def tqdm(x, **k): return x

    for book, pairs in books.items():
        out_jsonl = os.path.join(CORRECTIONS_DIR, f"{book}.jsonl")
        # 신규 라인만 append: 기존 corrections 가 있으면 (file,line,kind) 키로 dedup.
        existing_keys = set()
        if os.path.exists(out_jsonl):
            with open(out_jsonl, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                    except Exception:
                        continue
                    existing_keys.add((e.get("file"), e.get("line"),
                                       e.get("kind"), e.get("op")))

        book_items = []
        cer_samples = []
        n_class = Counter()
        n_table_adopt = 0
        for pair in tqdm(pairs, desc=book[:30], leave=False):
            new_md = pair["new_path"]
            for old_md in pair.get("existing_paths", []):
                items = diff_pair(new_md, old_md)
                for it in items:
                    key = (it.get("file"), it.get("line"),
                           it.get("kind"), it.get("op"))
                    if key in existing_keys:
                        continue
                    existing_keys.add(key)
                    book_items.append(it)
                    n_class[it["class"]] += 1
                    if it["kind"] == "table_adopt":
                        n_table_adopt += 1
                    if it.get("cer") is not None and it["kind"] == "text":
                        cer_samples.append(it["cer"])

        if book_items:
            os.makedirs(os.path.dirname(out_jsonl), exist_ok=True)
            with open(out_jsonl, "a", encoding="utf-8") as f:
                for it in book_items:
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")

        avg_cer = sum(cer_samples) / len(cer_samples) if cer_samples else 0.0
        summary[book] = {
            "diffs"            : len(book_items),
            "class_1_text"     : n_class[1],
            "class_2_anchor"   : n_class[2],
            "class_3_orphan"   : n_class[3],
            "table_adopt"      : n_table_adopt,
            "avg_cer_text"     : round(avg_cer, 4),
            "n_cer_samples"    : len(cer_samples),
            "out_path"         : os.path.relpath(out_jsonl, DRIVE_ROOT).replace("\\", "/"),
            "updated_at"       : datetime.now().isoformat(timespec="seconds"),
        }
        progress[book] = summary[book]
        _save_json(COMPARE_PROGRESS_PATH, progress)

    print(f"[Cell 2] 비교 완료: {len(summary)} 교재")
    return summary


print("[Cell 2] 시작 — Diff + corrections.jsonl 생성")
# 사전 점검: match_table.json 가 있어야 비교 가능
if not os.path.exists(MATCH_TABLE_PATH):
    print(f"[Cell 2] [중단] match_table.json 없음: {MATCH_TABLE_PATH}")
    print("[Cell 2] → Cell 1 (build_match_table) 을 먼저 실행하세요.")
    compare_summary = {}
else:
    _table = _load_json(MATCH_TABLE_PATH, {"books": {}})
    if not _table.get("books"):
        print("[Cell 2] [중단] match_table.books 가 비어 있음 — Cell 1 결과를 확인하세요.")
        compare_summary = {}
    else:
        # 특정 교재만 비교하려면 only_books 파라미터 사용:
        #   compare_summary = run_compare(only_books=["송영곤_논점민법_본책__송영곤_논점민법_본책"])
        compare_summary = run_compare()
print(f"[Cell 2] 종료 — 교재 {len(compare_summary)}개 처리. (다음: Cell 3)")

# %% [markdown]
# # Cell 3: 비교 결과 요약
#
# - 교재별 CER 평균/표준편차
# - Class 1/2/3 건수
# - 표 채택 건수
# - 교정 필요 건수 (Class 1 + Class 2 anchor changed)

# %%
def _stdev(xs: list) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return var ** 0.5


def summarize_compare() -> None:
    if not os.path.isdir(CORRECTIONS_DIR):
        print(f"[Cell 3] [중단] CORRECTIONS_DIR 없음: {CORRECTIONS_DIR}")
        print("[Cell 3] → Cell 2 (run_compare) 를 먼저 실행하세요.")
        return

    files = sorted(glob.glob(os.path.join(CORRECTIONS_DIR, "*.jsonl")))
    if not files:
        print(f"[Cell 3] [중단] corrections.jsonl 없음: {CORRECTIONS_DIR}/*.jsonl")
        print("[Cell 3] → Cell 2 (run_compare) 를 먼저 실행하세요.")
        return
    print(f"[Cell 3] corrections.jsonl 파일 수: {len(files)}")

    print(f"{'교재':40s} {'diffs':>6} {'C1':>5} {'C2':>5} {'C3':>5} "
          f"{'table':>5} {'cerμ':>6} {'cerσ':>6}")
    print("-" * 100)

    total = Counter()
    for jf in files:
        items = []
        with open(jf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    continue
        cers = [i.get("cer", 0.0) for i in items if i.get("kind") == "text"]
        cerμ = sum(cers) / len(cers) if cers else 0.0
        cerσ = _stdev(cers)
        n1 = sum(1 for i in items if i.get("class") == 1)
        n2 = sum(1 for i in items if i.get("class") == 2)
        n3 = sum(1 for i in items if i.get("class") == 3)
        nt = sum(1 for i in items if i.get("kind") == "table_adopt")
        total["diffs"]  += len(items)
        total["c1"]     += n1
        total["c2"]     += n2
        total["c3"]     += n3
        total["table"]  += nt
        book = os.path.basename(jf).replace(".jsonl", "")
        print(f"{book[:40]:40s} {len(items):6d} {n1:5d} {n2:5d} {n3:5d} "
              f"{nt:5d} {cerμ:6.3f} {cerσ:6.3f}")

    print("-" * 100)
    print(f"{'TOTAL':40s} {total['diffs']:6d} {total['c1']:5d} {total['c2']:5d} "
          f"{total['c3']:5d} {total['table']:5d}")
    print(f"\n교정 필요(C1) : {total['c1']}건  → haiku_ocr_correct.py 대상")
    print(f"검증 필요(C2) : {total['c2']}건  → Cell 4 에서 verification_targets.json 추출")
    print(f"고아 라인(C3) : {total['c3']}건  → 수동 확인 필요")
    print(f"표 채택       : {total['table']}건 → apply_corrections.py table_adopt")


print("[Cell 3] 시작 — 비교 결과 요약")
summarize_compare()
print("[Cell 3] 종료. (다음: Cell 4)")

# %% [markdown]
# # Cell 4: 조문/판례 번호 검증 대상 추출 (verification_targets.json)
#
# - corrections.jsonl 에서 `class == 2` 항목을 추출.
# - 조문(LAW_ARTICLE) / 판례(SUPREME_COURT, CONSTITUTIONAL, CASE_CODE_WHITELIST) 토큰을 분리 수집.
# - 코랩에서는 korean-law-mcp 직접 호출이 불안정 → 검증 대상 목록을 JSON 으로만 저장한다.
# - Claude Code 측에서 korean-law-mcp 로 실제 검증 후, 결과를 corrections.jsonl 의 `verified` 필드에 채운다.
#
# 출력 스키마:
# ```
# {
#   "generated_at": "...",
#   "law_articles" : [{"text": "제105조", "books": [...], "files": [...], "lines": [...]}, ...],
#   "case_numbers" : [{"text": "2023다12345", ...}, ...],
#   "constitutional": [{"text": "2020헌마1234", ...}, ...]
# }
# ```

# %%
def collect_verification_targets() -> dict:
    if not os.path.isdir(CORRECTIONS_DIR):
        print(f"[Cell 4] [중단] CORRECTIONS_DIR 없음: {CORRECTIONS_DIR}")
        print("[Cell 4] → Cell 2 (run_compare) 를 먼저 실행하세요.")
        return {}
    files = sorted(glob.glob(os.path.join(CORRECTIONS_DIR, "*.jsonl")))
    if not files:
        print(f"[Cell 4] [중단] corrections.jsonl 없음: {CORRECTIONS_DIR}/*.jsonl")
        print("[Cell 4] → Cell 2 (run_compare) 를 먼저 실행하세요.")
        return {}
    print(f"[Cell 4] 스캔 대상 corrections.jsonl: {len(files)}개")

    law_map  = defaultdict(lambda: {"books": set(), "files": set(), "lines": []})
    case_map = defaultdict(lambda: {"books": set(), "files": set(), "lines": []})
    const_map= defaultdict(lambda: {"books": set(), "files": set(), "lines": []})

    for jf in files:
        book = os.path.basename(jf).replace(".jsonl", "")
        with open(jf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    it = json.loads(line)
                except Exception:
                    continue
                if it.get("class") != 2:
                    continue
                blob = (it.get("new") or "") + " " + (it.get("old") or "")
                for m in LAW_ARTICLE.finditer(blob):
                    k = m.group(0)
                    law_map[k]["books"].add(book)
                    law_map[k]["files"].add(it.get("file", ""))
                    law_map[k]["lines"].append(it.get("line", -1))
                for m in SUPREME_COURT.finditer(blob):
                    k = m.group(0).strip()
                    case_map[k]["books"].add(book)
                    case_map[k]["files"].add(it.get("file", ""))
                    case_map[k]["lines"].append(it.get("line", -1))
                for m in CASE_CODE_WHITELIST.finditer(blob):
                    k = m.group(0).strip()
                    case_map[k]["books"].add(book)
                    case_map[k]["files"].add(it.get("file", ""))
                    case_map[k]["lines"].append(it.get("line", -1))
                for m in CONSTITUTIONAL.finditer(blob):
                    k = m.group(0).strip()
                    const_map[k]["books"].add(book)
                    const_map[k]["files"].add(it.get("file", ""))
                    const_map[k]["lines"].append(it.get("line", -1))

    def _flatten(d):
        out = []
        for k, v in d.items():
            out.append({
                "text"     : k,
                "books"    : sorted(v["books"]),
                "files"    : sorted(v["files"]),
                "lines"    : v["lines"][:50],
                "occurrences": len(v["lines"]),
                "verified" : None,
                "source"   : None,
            })
        return sorted(out, key=lambda x: -x["occurrences"])

    targets = {
        "generated_at"  : datetime.now().isoformat(timespec="seconds"),
        "law_articles"  : _flatten(law_map),
        "case_numbers"  : _flatten(case_map),
        "constitutional": _flatten(const_map),
        "instructions"  : (
            "Claude Code 에서 korean-law-mcp 스킬로 verified 필드를 채운 뒤, "
            "각 corrections.jsonl 의 해당 항목 verified 를 동일하게 갱신하세요."
        ),
    }
    _save_json(VERIFICATION_TARGETS, targets)
    print(f"[Cell 4] 조문 후보  : {len(targets['law_articles'])}")
    print(f"[Cell 4] 대법원 후보: {len(targets['case_numbers'])}")
    print(f"[Cell 4] 헌재 후보  : {len(targets['constitutional'])}")
    print(f"[Cell 4] 저장: {os.path.relpath(VERIFICATION_TARGETS, DRIVE_ROOT)}")
    return targets


print("[Cell 4] 시작 — 조문/판례 번호 검증 대상 추출")
verification_targets = collect_verification_targets()
_n_law   = len(verification_targets.get("law_articles", []))   if verification_targets else 0
_n_case  = len(verification_targets.get("case_numbers", []))   if verification_targets else 0
_n_const = len(verification_targets.get("constitutional", [])) if verification_targets else 0
print(f"[Cell 4] 종료 — 조문 {_n_law} / 대법원 {_n_case} / 헌재 {_n_const} 후보. "
      f"Claude Code 에서 korean-law-mcp 로 후속 검증.")
