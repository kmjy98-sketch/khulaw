import argparse
import json
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

# 운영 루트(번호 폴더) + 레거시 루트를 모두 탐색 후보로 둔다.
TARGET_DIR_CANDIDATES = [
    "1.민사",
    "2.형사",
    "3.공법",
    "4.선택법",
    "민사",
    "형사",
    "공법",
    "선택법",
    "9.로스쿨입시",
]

SKIP_DIRS = {
    ".agent",
    ".gemini",
    "_trash",
    "_inbox",
    "_노트앱",
    "_원본보관",
    "0.공유드라이브",
    "공유드라이브",
    "System Volume Information",
    "_archive",
}

# 명명규칙 문서의 연도 예외(전사문/교정문/수업노트/수업정리/기출/질문답안) 반영
YEAR_EXEMPT_KEYWORDS = (
    "전사문",
    "교정문",
    "수업노트",
    "수업정리",
    "기출",
    "질문답안",
)

# 기존 검사에서 연도 강제를 제외하던 폴더군 유지
YEAR_EXEMPT_PATH_HINTS = (
    "개념",
    "참고",
    "보관",
    "기출",
    "내신",
    "전사",
    "전사문",
    "전사원본",
    "교정문",
    "교재_추출",
    "추출파일",
)

TRANSCRIPT_PATTERN = re.compile(r"_전사문_\d+(-\d+(\.\d+)?)?(_교정)?$")
CLASSNOTE_PATTERN = re.compile(r"_수업정리_\d+$")
LECTURE_NOTE_PATTERN = re.compile(r"_수업노트_\d+$")
YEAR_SUFFIX_PATTERN = re.compile(r"_(\d{2}|20\d{2})$")
YEAR_HINT_PATTERN = re.compile(r"(19|20)\d{2}")
PREP_YEAR_PATTERN = re.compile(r"(20\d{2})\s*년?\s*대비")
PUBLICATION_DATE_PATTERN = re.compile(r"(20\d{2})\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}\s*\.")
COPY_SUFFIX_PATTERN = re.compile(r"_(?:2\d|[3-9]\d|20\d{2})_[1-9]$")
COPY_WORD_PATTERN = re.compile(r"(?:^|_)복사(?:$|_)")
PART_SUFFIX_PATTERN = re.compile(r"(?i)(?:^|_)part[-_ ]?\d+(?:$|_)")
TRAILING_COPY_INDEX_PATTERN = re.compile(r"_[1-9]$")
PDF_FRONT_PAGES = 6
CONTENT_SCAN_PAGES = 3
MAX_MISFILE_REVIEW_PAGES = 80
EXAM_LIKE_KEYWORDS = (
    "모의고사",
    "채점평",
    "모의답안",
    "우수답안",
)
CASE_LIKE_KEYWORDS = (
    "주요사례",
    "사례형",
)
CHOICE_LIKE_KEYWORDS = (
    "선택형",
    "DT",
)
FILENAME_EXAM_HINTS = ("기출", "모의", "답안", "채점", "해설", "답지", "정답", "dt", "ox")
FILENAME_CHOICE_HINTS = ("선택", "객관식", "dt", "ox", "문제")
TEXTBOOK_STEM_HINTS = ("목차", "서론", "총론", "각론", "민법의맥", "사례연습", "민사법사례연습", "논점", "형법요론", "코어코드")


def parse_args():
    parser = argparse.ArgumentParser(description="파일명 명명규칙 검사")
    parser.add_argument(
        "--dir",
        dest="target_dirs",
        action="append",
        help="검사할 폴더(상대/절대경로). 여러 번 지정 가능",
    )
    return parser.parse_args()


def detect_base_dir() -> Path:
    """워크스페이스 루트(.agent 포함) 자동 탐지."""
    cwd = Path.cwd()
    if (cwd / ".agent").exists():
        return cwd

    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".agent").exists():
            return parent
    return cwd


BASE_DIR = detect_base_dir()


def iter_target_dirs(base_dir: Path, target_dirs=None):
    if target_dirs:
        seen = set()
        for raw in target_dirs:
            path = Path(raw)
            if not path.is_absolute():
                path = base_dir / raw
            if not path.exists() or not path.is_dir():
                continue
            real = str(path.resolve())
            if real in seen:
                continue
            seen.add(real)
            yield path
        return

    seen = set()
    for name in TARGET_DIR_CANDIDATES:
        path = base_dir / name
        if not path.exists() or not path.is_dir():
            continue
        real = str(path.resolve())
        if real in seen:
            continue
        seen.add(real)
        yield path


def should_skip_dir(name: str) -> bool:
    if name in SKIP_DIRS:
        return True
    if name.startswith("."):
        return True
    if name.startswith("backup_"):
        return True
    return False


def should_skip_file(filename: str, stem: str) -> bool:
    if stem.startswith("."):
        return True
    if filename.lower() == "desktop.ini":
        return True
    return False


def is_year_exempt(parts, stem: str) -> bool:
    top = parts[0] if parts else ""

    # 9.로스쿨입시는 강의연도 suffix(_YY) 강제 대상에서 제외
    if top == "9.로스쿨입시":
        return True

    if any(keyword in stem for keyword in YEAR_EXEMPT_KEYWORDS):
        return True

    for part in parts:
        if any(keyword in part for keyword in YEAR_EXEMPT_KEYWORDS):
            return True
        if any(hint in part for hint in YEAR_EXEMPT_PATH_HINTS):
            return True

    return False


def is_year_judgeable(parts, stem: str) -> bool:
    """파일명/경로에 연도 단서가 있을 때만 연도 suffix 강제."""
    if YEAR_SUFFIX_PATTERN.search(stem):
        return True
    if YEAR_HINT_PATTERN.search(stem):
        return True
    for part in parts:
        if YEAR_HINT_PATTERN.search(part):
            return True
    return False


def normalize_year_token(token: str) -> int:
    year = int(token)
    return year % 100 if year >= 100 else year


@lru_cache(maxsize=256)
def inspect_pdf_front_text(filepath_str: str, max_pages: int):
    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    filepath = Path(filepath_str)
    if filepath.suffix.lower() != ".pdf":
        return ""

    try:
        reader = PdfReader(str(filepath))
    except Exception:
        return ""

    texts = []
    for page in reader.pages[: min(max_pages, len(reader.pages))]:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text:
            texts.append(text)

    return "\n".join(texts)


@lru_cache(maxsize=256)
def inspect_pdf_page_count(filepath_str: str):
    try:
        from pypdf import PdfReader
    except Exception:
        return 0

    filepath = Path(filepath_str)
    if filepath.suffix.lower() != ".pdf":
        return 0

    try:
        reader = PdfReader(str(filepath))
    except Exception:
        return 0

    return len(reader.pages)


@lru_cache(maxsize=256)
def inspect_pdf_prep_and_publication_year(filepath_str: str):
    """교재 PDF 앞부분에서 `20XX 대비` 표기와 출판일을 함께 찾는다."""
    filepath = Path(filepath_str)
    if filepath.suffix.lower() != ".pdf":
        return None

    joined = inspect_pdf_front_text(filepath_str, PDF_FRONT_PAGES)
    if not joined:
        return None
    prep_match = PREP_YEAR_PATTERN.search(joined)
    publication_match = PUBLICATION_DATE_PATTERN.search(joined)
    if not prep_match or not publication_match:
        return None

    return int(prep_match.group(1)), int(publication_match.group(1))


def detect_content_folder_mismatch(filepath: Path, parts, stem: str):
    if filepath.suffix.lower() != ".pdf":
        return []

    needs_scan = "교재" in parts or "선택형" in parts or "목차" in stem
    if not needs_scan:
        return []

    text = inspect_pdf_front_text(str(filepath), CONTENT_SCAN_PAGES)
    if not text:
        return []

    errors = []
    has_exam_like = any(keyword in text for keyword in EXAM_LIKE_KEYWORDS)
    has_case_like = any(keyword in text for keyword in CASE_LIKE_KEYWORDS)
    has_choice_like = any(keyword in text for keyword in CHOICE_LIKE_KEYWORDS)
    stem_lower = stem.casefold()
    page_count = inspect_pdf_page_count(str(filepath))
    filename_exam_like = any(keyword in stem_lower for keyword in FILENAME_EXAM_HINTS)
    filename_choice_like = any(keyword in stem_lower for keyword in FILENAME_CHOICE_HINTS)
    filename_textbook_like = any(keyword in stem for keyword in TEXTBOOK_STEM_HINTS)

    if "교재" in parts and has_exam_like and filename_exam_like and not filename_textbook_like:
        if page_count == 0 or page_count <= MAX_MISFILE_REVIEW_PAGES:
            errors.append("교재 폴더에 기출/모의답안 성격 자료")
    if "목차" in stem and has_exam_like and filename_exam_like:
        errors.append("목차 파일명인데 실제 내용은 시험/채점평")
    if "선택형" in parts and has_case_like and not has_choice_like and not filename_choice_like:
        errors.append("선택형 폴더에 사례형 성격 자료")

    return errors


def detect_prep_year_mismatch(filepath: Path, parts, stem: str):
    """
    `20XX 대비` 교재에서 파일명 연도를 대비연도로 오기입했는지 검사.
    별도 강의연도 근거가 없으면 출판연도를 따라야 한다.
    """
    if filepath.suffix.lower() != ".pdf":
        return None
    if "교재" not in parts:
        return None

    year_match = YEAR_SUFFIX_PATTERN.search(stem)
    if not year_match:
        return None

    inspected = inspect_pdf_prep_and_publication_year(str(filepath))
    if not inspected:
        return None

    prep_year, publication_year = inspected
    file_year = normalize_year_token(year_match.group(1))
    if file_year == prep_year % 100 and file_year != publication_year % 100:
        return (
            f"대비연도 {prep_year}를 파일명 연도로 사용함; "
            f"출판연도 {publication_year} 확인됨"
        )
    return None


def check_file(filepath: Path, base_dir: Path):
    filename = filepath.name
    stem = filepath.stem
    rel_path = filepath.relative_to(base_dir)
    parts = rel_path.parts
    errors = []

    if should_skip_file(filename, stem):
        return []

    # 1) 금지 문자
    if re.search(r"[()]", filename):
        errors.append("파일명에 괄호() 포함됨")
    if " " in filename:
        errors.append("파일명에 공백 포함됨")

    # 2) 전사문/수업노트 패턴
    if "전사문" in stem and not TRANSCRIPT_PATTERN.search(stem):
        errors.append(f"전사문 명명규칙 위반: {stem}")
    if "수업정리" in stem and not CLASSNOTE_PATTERN.search(stem):
        errors.append(f"수업정리 명명규칙 위반: {stem}")
    if "수업노트" in stem and not LECTURE_NOTE_PATTERN.search(stem):
        errors.append(f"수업노트 명명규칙 위반: {stem}")

    # 3) 연도 suffix(_YY / _YYYY) 점검
    if not is_year_exempt(parts, stem):
        if is_year_judgeable(parts, stem) and not YEAR_SUFFIX_PATTERN.search(stem):
            errors.append("연도 표기(_YY) 누락")

    # 4) `20XX 대비` 교재의 대비연도/출판연도 혼동 점검
    prep_year_error = detect_prep_year_mismatch(filepath, parts, stem)
    if prep_year_error:
        errors.append(prep_year_error)

    # 5) 사본/임시 표기 잔존 점검
    if COPY_SUFFIX_PATTERN.search(stem):
        errors.append("사본/임시 suffix(_2 등) 잔존")
    if COPY_WORD_PATTERN.search(stem):
        errors.append("사본 표기(복사) 잔존")
    if PART_SUFFIX_PATTERN.search(stem):
        errors.append("분철 임시 표기(part-숫자) 잔존")
    if TRAILING_COPY_INDEX_PATTERN.search(stem):
        errors.append("사본/임시 suffix(_1 등) 잔존")

    # 6) 내용-폴더/파일명 불일치 점검
    errors.extend(detect_content_folder_mismatch(filepath, parts, stem))

    return errors


args = parse_args()
issues = []

for target_dir in iter_target_dirs(BASE_DIR, args.target_dirs):
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for file in files:
            filepath = Path(root) / file
            errs = check_file(filepath, BASE_DIR)
            if errs:
                issues.append({"path": str(filepath.relative_to(BASE_DIR)), "errors": errs})

issues.sort(key=lambda x: x["path"])

out_path = BASE_DIR / ".agent" / "state" / "naming_issues.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding="utf-8")

error_counter = Counter()
for item in issues:
    for error in item["errors"]:
        error_counter[error] += 1

print(f"Total files with issues: {len(issues)}")
for error, count in error_counter.most_common():
    print(f"- {error}: {count}")
