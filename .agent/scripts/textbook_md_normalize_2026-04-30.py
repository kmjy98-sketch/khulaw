"""교재원문 마크다운 정규화·교정 (2026-04-30 batch).

영역:
- 대상: sync/_교재원문/{과목}/{저자}/**/*.md
- 제외: 김기용_레인보우OX/*, _재추출/* (다른 task 영역)

점검·교정 항목:
1. YAML frontmatter 정규화
   - 1줄 압축형 ("--- tags: [...] 교재: ... 과목: ... ---") → multi-line 표준
   - 필수 필드 누락 시 추가는 하지 않고 missing_fields[] 에 기록 (보수적)
2. 페이지 마커 정리 (옵션 — 기본 비활성)
3. 한자 → 한글 (기존 fix_ocr_hanja.py 의 로직 재사용 가능, 본 script 에서는
   별도 적용 안 함; 별도 단계로 호출)
4. 명백한 OCR 띄어쓰기 분리 — '대 판' → '대판', '2 0 1 7' → '2017' 등
   매우 보수적 패턴만
5. 중복 헤더 정리 — 동일 제목의 # 헤더가 연속되면 첫 항목만 유지

운영:
- dry-run: --dry-run (변경 미적용, JSON 리포트만)
- apply: 기본
- 백업: _백업/2026-04-30/{원본 상대경로}.bak
- author 단위 batch 처리 (50파일 단위)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

WORKSPACE_ROOT = Path(VAULT_ROOT)
DEFAULT_ROOT = WORKSPACE_ROOT / "sync" / "_교재원문"
BACKUP_ROOT = WORKSPACE_ROOT / "_백업" / "2026-04-30"

# ─────────────────────────────────────────────────────────────
# 제외 패턴
EXCLUDE_PATH_PATTERNS = [
    "김기용_레인보우OX",  # task local_7f2669f8 영역
    "_재추출",  # task local_5d410738 영역 (재OCR 진행 중)
    "_백업",
    "_trash",
    "_orig",
    "_raw",
    "_src",
]

# ─────────────────────────────────────────────────────────────
# 1줄 압축형 frontmatter 정규화
# 패턴: 1) "--- tags: [...]" 같은 형태로 --- 와 첫 키가 같은 줄
#       2) 키: 값 키: 값 키: 값 한 줄에 다수
#       3) "키: 값 ---" 같은 형태로 마지막 키와 닫는 ---가 같은 줄

COMPRESSED_FM_OPEN = re.compile(r"^---\s+(\w[\w가-힣]*\s*:\s*.+)$")
COMPRESSED_FM_CLOSE = re.compile(r"^(.+?)\s+---\s*$")
# multiple key:value pairs on same line (key: value key2: value2 ...)
INLINE_KV = re.compile(r"(?:^|\s+)(\w[\w가-힣]*)\s*:\s*")


def _split_inline_kvs(line: str) -> list[str]:
    """`교재: A 판: 8 과목: 민법` → ['교재: A', '판: 8', '과목: 민법']"""
    matches = list(INLINE_KV.finditer(line))
    if len(matches) <= 1:
        return [line]
    parts: list[str] = []
    for i, m in enumerate(matches):
        # m starts with optional whitespace; key starts at m.start(1)
        key_start = m.start(1)
        next_key_start = matches[i + 1].start(1) if i + 1 < len(matches) else len(line)
        chunk = line[key_start:next_key_start].rstrip()
        if chunk:
            parts.append(chunk)
    return parts


def normalize_frontmatter(text: str) -> tuple[str, dict]:
    """1줄/압축형 frontmatter 를 multi-line 표준으로 변환.

    Returns:
        (new_text, info) — info 는 {changed: bool, fm_present: bool}
    """
    info = {"fm_present": False, "fm_changed": False, "fm_compressed": False}
    if not text.startswith("---"):
        return text, info

    lines = text.splitlines(keepends=False)
    first = lines[0]

    # 진짜 frontmatter 식별:
    #   1) 첫 줄이 정확히 '---' (표준 yaml opener)
    #   2) 첫 줄이 '--- key: value' 형태 (압축형)
    # '--- Page N ---', '--- 제목' 같은 페이지 마커/구분선은 제외.
    is_standard_open = (first.strip() == "---")
    open_match = COMPRESSED_FM_OPEN.match(first)
    if not is_standard_open and not open_match:
        return text, info

    info["fm_present"] = True
    fm_open_inline_content = open_match.group(1) if open_match else None

    # 닫는 --- 위치
    close_idx = None
    close_inline_content: str | None = None
    start_search = 1
    if open_match:
        # 동일 줄에 닫는 --- 가 함께 있을 가능성 (드물지만)
        if first.rstrip().endswith("---") and first.rstrip() != "---":
            # "--- tags: [...] ---" 단일줄 형태
            inner = first[3:].rstrip()
            if inner.endswith("---"):
                inner = inner[:-3].strip()
                close_idx = 0
                fm_open_inline_content = inner
                close_inline_content = None
    if close_idx is None:
        for i in range(start_search, len(lines)):
            line = lines[i]
            if line.strip() == "---":
                close_idx = i
                break
            close_match = COMPRESSED_FM_CLOSE.match(line)
            if close_match and not line.lstrip().startswith("- "):
                # 마지막 key 와 --- 가 같은 줄
                close_idx = i
                close_inline_content = close_match.group(1).strip()
                break

    if close_idx is None:
        # 닫는 --- 못 찾음 — 정규화 보류
        return text, info

    # frontmatter 라인 수집
    fm_body_lines: list[str] = []
    if open_match:
        fm_body_lines.append(fm_open_inline_content)
        info["fm_compressed"] = True
    if close_idx > 0:
        for i in range(1, close_idx):
            fm_body_lines.append(lines[i])
    if close_inline_content is not None and close_idx > 0:
        # 마지막 줄을 inline 처리한 경우, 그 줄을 추가
        fm_body_lines.append(close_inline_content)
        info["fm_compressed"] = True

    # 한 줄에 여러 key:value 가 있는 경우 분해
    expanded: list[str] = []
    needs_change = info["fm_compressed"]
    for fb in fm_body_lines:
        fb_stripped = fb.strip()
        if not fb_stripped:
            continue
        # YAML 리스트 항목/주석/이미 들여쓴 매핑은 보존
        if fb_stripped.startswith("- ") or fb_stripped.startswith("#"):
            expanded.append(fb)
            continue
        sub = _split_inline_kvs(fb_stripped)
        if len(sub) > 1:
            needs_change = True
            expanded.extend(sub)
        else:
            expanded.append(fb_stripped)

    if not needs_change:
        return text, info

    info["fm_changed"] = True
    new_fm = ["---"] + expanded + ["---"]
    body = lines[close_idx + 1 :]
    new_text = "\n".join(new_fm + body)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return new_text, info


# ─────────────────────────────────────────────────────────────
# 보수적 OCR 띄어쓰기 보정 — 본문 영역에만 적용
OCR_SPACING_RULES: list[tuple[re.Pattern[str], str]] = [
    # "대 판" / "대 결" / "헌 재" — 매우 안전
    (re.compile(r"(?<![가-힣])대 판(?=\s*\d{4}[\.\,])"), "대판"),
    (re.compile(r"(?<![가-힣])대 결(?=\s*\d{4}[\.\,])"), "대결"),
    (re.compile(r"(?<![가-힣])헌 재(?=\s*\d{4}[\.\,])"), "헌재"),
    # 연도 OCR 분리: "2 0 1 7" → "2017", "2 0 2 4" → "2024" (4자리만)
    (re.compile(r"(?<!\d)(\d) (\d) (\d) (\d)(?!\d)"), r"\1\2\3\4"),
]


def apply_ocr_spacing(body: str) -> tuple[str, int]:
    total = 0
    new_lines: list[str] = []
    for line in body.splitlines(keepends=False):
        if line.strip().startswith("```") or line.strip().startswith("|"):
            new_lines.append(line)
            continue
        new_line = line
        for pat, repl in OCR_SPACING_RULES:
            nl, n = pat.subn(repl, new_line)
            if n:
                new_line = nl
                total += n
        new_lines.append(new_line)
    new_body = "\n".join(new_lines)
    if body.endswith("\n") and not new_body.endswith("\n"):
        new_body += "\n"
    return new_body, total


# ─────────────────────────────────────────────────────────────
# 중복 헤더 정리: 같은 제목의 H1 이 연속으로 등장하면 첫 항목만 유지
DUP_H1 = re.compile(r"^# (.+)$")


def dedup_consecutive_h1(body: str) -> tuple[str, int]:
    lines = body.splitlines(keepends=False)
    new_lines: list[str] = []
    last_h1_title: str | None = None
    removed = 0
    for line in lines:
        m = DUP_H1.match(line.strip())
        if m:
            title = m.group(1).strip()
            if title == last_h1_title:
                removed += 1
                continue
            last_h1_title = title
        else:
            # 빈 줄이면 last_h1_title 유지, 그 외에는 reset
            if line.strip():
                last_h1_title = None
        new_lines.append(line)
    new_body = "\n".join(new_lines)
    if body.endswith("\n") and not new_body.endswith("\n"):
        new_body += "\n"
    return new_body, removed


# ─────────────────────────────────────────────────────────────
# 통계 수집 (변경 없이)
HANJA_PARTY = re.compile(r"[甲乙丙丁戊]")
RARE_HANJA_OCR = re.compile(r"[芮雨因成戊內日江人石仁西]")


def scan_metrics(text: str) -> dict:
    fm_check, _ = normalize_frontmatter(text)
    fm_compressed = (fm_check != text)
    body = text
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) >= 3:
            body = parts[2]
    party_count = len(HANJA_PARTY.findall(body))
    rare_ocr = len(RARE_HANJA_OCR.findall(body))
    h1_dups = 0
    last: str | None = None
    for line in body.splitlines():
        m = DUP_H1.match(line.strip())
        if m:
            t = m.group(1).strip()
            if t == last:
                h1_dups += 1
            last = t
        elif line.strip():
            last = None
    return {
        "fm_compressed": fm_compressed,
        "party_hanja": party_count,
        "rare_ocr_hanja": rare_ocr,
        "dup_h1": h1_dups,
    }


# ─────────────────────────────────────────────────────────────
def is_excluded(path: Path) -> bool:
    parts_str = str(path)
    for pat in EXCLUDE_PATH_PATTERNS:
        if pat in parts_str:
            return True
    return False


def list_target_files(root: Path) -> list[Path]:
    files = []
    for p in sorted(root.rglob("*.md")):
        if is_excluded(p):
            continue
        if p.name.endswith(".tmp.md"):
            continue
        files.append(p)
    return files


def backup_file(path: Path) -> Path:
    rel = path.relative_to(WORKSPACE_ROOT)
    backup = BACKUP_ROOT / rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    return backup


def process_file(path: Path, dry_run: bool) -> dict:
    original = path.read_text(encoding="utf-8")
    metrics = scan_metrics(original)

    text = original
    fm_changed = False
    spacing_fixes = 0
    h1_removed = 0

    text, fm_info = normalize_frontmatter(text)
    fm_changed = fm_info.get("fm_changed", False)

    # 본문 영역 분리
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) >= 3:
            head = "---\n" + parts[1] + "---\n"
            body = parts[2]
        else:
            head = ""
            body = text
    else:
        head = ""
        body = text

    body, spacing_fixes = apply_ocr_spacing(body)
    body, h1_removed = dedup_consecutive_h1(body)

    new_text = head + body
    changed = (new_text != original)

    result = {
        "path": str(path.relative_to(WORKSPACE_ROOT)),
        "fm_changed": fm_changed,
        "spacing_fixes": spacing_fixes,
        "dup_h1_removed": h1_removed,
        "metrics": metrics,
        "changed": changed,
    }

    if changed and not dry_run:
        backup_file(path)
        path.write_text(new_text, encoding="utf-8")

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--author", help="저자 단위 필터 (디렉터리명 substring match)")
    parser.add_argument("--limit", type=int, default=0, help="0=무제한")
    parser.add_argument("--report", default=None, help="JSON report 출력 경로")
    args = parser.parse_args()

    root = Path(args.root)
    files = list_target_files(root)
    if args.author:
        files = [f for f in files if args.author in str(f)]
    if args.limit:
        files = files[: args.limit]

    summary = {
        "total_files": len(files),
        "changed_files": 0,
        "fm_normalized": 0,
        "spacing_fixes_total": 0,
        "h1_dedup_total": 0,
        "by_author": {},
        "files": [],
    }

    for i, path in enumerate(files, 1):
        try:
            r = process_file(path, dry_run=args.dry_run)
        except Exception as e:
            r = {"path": str(path.relative_to(WORKSPACE_ROOT)), "error": str(e), "changed": False}
        summary["files"].append(r)
        if r.get("changed"):
            summary["changed_files"] += 1
        if r.get("fm_changed"):
            summary["fm_normalized"] += 1
        summary["spacing_fixes_total"] += r.get("spacing_fixes", 0) or 0
        summary["h1_dedup_total"] += r.get("dup_h1_removed", 0) or 0

        # author 집계
        try:
            rel = Path(r["path"])
            # sync/_교재원문/{과목}/{저자}/...
            if len(rel.parts) >= 4:
                key = f"{rel.parts[2]}/{rel.parts[3]}"
                a = summary["by_author"].setdefault(key, {"files": 0, "changed": 0, "fm_normalized": 0, "spacing": 0, "dup_h1": 0})
                a["files"] += 1
                if r.get("changed"):
                    a["changed"] += 1
                if r.get("fm_changed"):
                    a["fm_normalized"] += 1
                a["spacing"] += r.get("spacing_fixes", 0) or 0
                a["dup_h1"] += r.get("dup_h1_removed", 0) or 0
        except Exception:
            pass

        if i % 100 == 0:
            print(f"  [{i}/{len(files)}] processed", file=sys.stderr)

    if args.report:
        Path(args.report).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in summary.items() if k != "files"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
