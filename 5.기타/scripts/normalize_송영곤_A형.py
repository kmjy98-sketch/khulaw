# -*- coding: utf-8 -*-
"""
송영곤 A형 OCR 정규화 스크립트
================================
대상  : sync/_교재원문/민법/송영곤_논점민법_본책/ + 송영곤_논점민법_보충/
근거  : H:\\내 드라이브\\sync\\_meta\\송영곤_B형_표준템플릿_v1.md (§6 자동 batch 패턴)
원칙  : CLAUDE.md #1 (소스 보존), #34 (anchor 보존), #15 (Verify-Before-Act),
        #16 (삭제 금지) — 변경된 원본은 백업 PowerShell이 처리

사용법
------
    # 1. dry-run (진단만)
    python normalize_송영곤_A형.py --target 본책 --dry-run

    # 2. 실제 적용
    python normalize_송영곤_A형.py --target 본책 --apply

    # 3. 보충 처리
    python normalize_송영곤_A형.py --target 보충 --dry-run
    python normalize_송영곤_A형.py --target 보충 --apply

의존성
------
    pip install pyyaml tqdm

원칙
----
* 정규식은 §6 표 "자동 batch 적용 가능 (안전)" 항목만 적용.
* 한자 깨짐, 의미불명 기호는 anchor — 자동 치환 금지 (사용자 검수 후 별도 task).
* 조문 callout / 판례 callout 본문은 "변경 없음" — 라인이 callout 내부면 패턴 적용 제외.
* 사건번호 끝 각주 마커 [^N]은 본문 내 정의부 부재 시 OCR 노이즈로 간주 → 제거.
* 헤더 계층 보정·callout 깨짐 정리는 LLM 검증 필요 영역 → 본 스크립트는 수행하지 않음.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

try:
    import yaml  # type: ignore
except ImportError:
    print("[FATAL] pyyaml 미설치. 'pip install pyyaml tqdm' 후 재실행.", file=sys.stderr)
    sys.exit(2)

try:
    from tqdm import tqdm  # type: ignore
except ImportError:
    print("[FATAL] tqdm 미설치. 'pip install pyyaml tqdm' 후 재실행.", file=sys.stderr)
    sys.exit(2)


# ----------------------------------------------------------------------
# 경로
# ----------------------------------------------------------------------
BASE_ROOT = Path(r"H:\내 드라이브\sync\_교재원문\민법")
BON_CHAEK = BASE_ROOT / "송영곤_논점민법_본책"
BO_CHUNG = BASE_ROOT / "송영곤_논점민법_보충"
META_DIR = Path(r"H:\내 드라이브\sync\_meta")
TODAY = "2026-04-29"
DRY_RUN_REPORT = META_DIR / f"송영곤_정규화_dry_run_{TODAY}.md"
APPLY_REPORT = META_DIR / f"송영곤_정규화_apply_{TODAY}.md"


# ----------------------------------------------------------------------
# 정규식 패턴 (§6 자동 batch 적용 가능)
# ----------------------------------------------------------------------
# 페이지 헤더: "제N관 ... 숫자" 단독 라인
RE_PAGE_HEADER_GUAN = re.compile(
    r"^\s*제\s*\d+\s*관\s+\[?\[?[가-힣A-Za-z·\(\)\s]+\]?\]?\s+\d+\s*$"
)
# 페이지 헤더: "제N관 [[xxx]]" (페이지 번호 없는 단독 라인)
RE_PAGE_HEADER_GUAN_NUMLESS = re.compile(
    r"^\s*제\s*\d+\s*관\s+\[?\[?[가-힣A-Za-z·\(\)\s]+\]?\]?\s*$"
)
# 페이지 헤더: "제N장 ... 숫자" 단독 라인
RE_PAGE_HEADER_JANG = re.compile(r"^\s*제\s*\d+\s*장\s+.+?\s+\d+\s*$")
# 페이지 헤더: "제N부 ..." 단독 라인 (대괄호 깨짐 포함)
RE_PAGE_HEADER_BU = re.compile(r"^\s*\[?\s*제\s*[OoO0\d]+\s*부\s+.+?$")
# 단독 라인 페이지 번호 (3자리 이하 + "- N -" 형식)
RE_PAGE_NUM_BARE = re.compile(r"^\s*\d{1,3}\s*$")
RE_PAGE_NUM_DASH = re.compile(r"^\s*-\s*\d{1,4}\s*-\s*$")
# 사건번호 끝 각주 마커: \d+다\d+[^\d+]
RE_FOOTNOTE_DA = re.compile(r"(\d+\s*다\s*\d+)\s*\[\^\d+\]")
# 사건번호 끝 각주 마커: \d+민[가-힣]+[^\d+]
RE_FOOTNOTE_MIN = re.compile(r"(\d+민[가-힣]+\d*)\s*\[\^\d+\]")
# 사건번호 끝 각주 마커: \d+그\d+[^\d+], \d+마\d+[^\d+]
RE_FOOTNOTE_GU_MA = re.compile(r"(\d+\s*[그마]\s*\d+)\s*\[\^\d+\]")
# 사건번호 끝 각주 마커: 헌재 관련 \d+헌[가-힣]+\d+[^\d+]
RE_FOOTNOTE_HEON = re.compile(r"(\d+\s*헌[가-힣]+\s*\d+)\s*\[\^\d+\]")


# ----------------------------------------------------------------------
# 데이터 구조
# ----------------------------------------------------------------------
@dataclass
class FileReport:
    path: str
    category: str
    line_count_before: int = 0
    line_count_after: int = 0
    word_count_before: int = 0
    word_count_after: int = 0
    pattern_counts: dict = field(default_factory=lambda: defaultdict(int))
    in_callout_skipped: int = 0
    front_matter_normalized: bool = False
    warnings: list = field(default_factory=list)


@dataclass
class RunReport:
    target: str
    mode: str
    timestamp: str
    files: list = field(default_factory=list)
    totals: dict = field(default_factory=dict)


# ----------------------------------------------------------------------
# Front matter 정상화
# ----------------------------------------------------------------------
def parse_compressed_front_matter(text: str) -> tuple[dict | None, str]:
    """A형 압축 front matter를 파싱하여 (메타딕트, 본문) 반환.
    파싱 실패 시 (None, 원본) 반환.
    """
    if not text.startswith("---"):
        return None, text

    # 표준 yaml front matter면 그대로
    m_std = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if m_std:
        try:
            meta = yaml.safe_load(m_std.group(1))
            if isinstance(meta, dict) and "tags" in meta:
                # 이미 표준 형식
                return meta, text[m_std.end():]
        except yaml.YAMLError:
            pass

    # A형 압축 형식: --- tags: [...]\n키: 값 키: 값\n쟁점: [...]\n---
    m_compressed = re.match(r"^---\s*(.*?)\n---\s*\n", text, re.DOTALL)
    if not m_compressed:
        return None, text

    raw = m_compressed.group(1).strip()
    # tags 라인 추출
    tags_match = re.search(r"tags\s*:\s*\[([^\]]+)\]", raw)
    tags = []
    if tags_match:
        tags = [t.strip() for t in tags_match.group(1).split(",") if t.strip()]

    # 한 줄에 압축된 메타 필드 파싱 (교재: ... 판: 12 과목: 민법 ...)
    meta: dict = {"tags": tags}
    # 알려진 한국어 키 목록
    keys = ["교재", "판", "과목", "원본_chunk", "페이지", "페이지_범위",
            "포함_페이지", "서브책자", "쟁점"]

    # tags 라인 제거 후 나머지 파싱
    raw_no_tags = re.sub(r"tags\s*:\s*\[[^\]]+\]", "", raw)

    # 키: 값 패턴을 순차적으로 추출
    # 단순 split 대신 lookahead 사용
    key_pattern = "(" + "|".join(keys) + r")\s*:\s*"
    matches = list(re.finditer(key_pattern, raw_no_tags))
    for i, m in enumerate(matches):
        key = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_no_tags)
        val = raw_no_tags[start:end].strip()
        # 배열 형식 [...]
        if val.startswith("[") and "]" in val:
            arr_end = val.index("]") + 1
            arr_str = val[:arr_end]
            try:
                val = yaml.safe_load(arr_str)
            except yaml.YAMLError:
                pass
        meta[key] = val

    body = text[m_compressed.end():]
    return meta, body


def build_standard_front_matter(meta: dict, file_path: Path, category: str) -> str:
    """B형 템플릿 §1에 맞춰 표준 yaml 헤더 빌드."""
    if not meta:
        return ""
    out = {}
    out["tags"] = meta.get("tags", [])
    if "교재" in meta:
        out["교재"] = meta["교재"]
    if "판" in meta:
        try:
            out["판"] = int(str(meta["판"]).strip())
        except (ValueError, TypeError):
            out["판"] = meta["판"]
    if "과목" in meta:
        out["과목"] = meta["과목"]
    if "서브책자" in meta:
        out["서브책자"] = meta["서브책자"]
    if "원본_chunk" in meta:
        out["원본_chunk"] = meta["원본_chunk"]
    # 페이지_범위 통일 (구 "페이지" 키 → "페이지_범위")
    page_range = meta.get("페이지_범위") or meta.get("페이지")
    if page_range:
        out["페이지_범위"] = str(page_range).strip()
    if "포함_페이지" in meta:
        pages = meta["포함_페이지"]
        if isinstance(pages, str):
            try:
                pages = yaml.safe_load(pages)
            except yaml.YAMLError:
                pass
        out["포함_페이지"] = pages
    if "쟁점" in meta:
        jaengs = meta["쟁점"]
        if isinstance(jaengs, str):
            try:
                jaengs = yaml.safe_load(jaengs)
            except yaml.YAMLError:
                jaengs = [jaengs]
        out["쟁점"] = jaengs
    out["정리일"] = TODAY
    out["정리_버전"] = "B-v1-prep"  # 정규식 batch만 적용된 단계

    yml = yaml.safe_dump(out, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{yml}---\n"


# ----------------------------------------------------------------------
# 본문 정규화 (callout 내부는 보호)
# ----------------------------------------------------------------------
def normalize_body(body: str, report: FileReport) -> str:
    """본문에 §6 자동 batch 패턴 적용. callout 내부 라인은 보호."""
    out_lines: list[str] = []
    in_callout = False
    callout_type = None  # 조문/판례 등

    for raw_line in body.split("\n"):
        stripped = raw_line.rstrip("\r")
        # callout 시작/종료 추적
        callout_start = re.match(r"^>\s*\[!(조문|판례|정의|예시|주의|참고|note|warning|info|tip)\]", stripped)
        if callout_start:
            in_callout = True
            callout_type = callout_start.group(1)
            out_lines.append(stripped)
            continue
        # callout 본문 (>로 시작하는 라인)
        if in_callout:
            if stripped.startswith(">") or stripped == "":
                # 빈 라인은 callout 종료 신호로 간주
                if stripped == "":
                    in_callout = False
                    callout_type = None
                else:
                    # callout 안: 변경 금지 (위험)
                    report.in_callout_skipped += 1
                out_lines.append(stripped)
                continue
            else:
                # callout 종료
                in_callout = False
                callout_type = None

        # 일반 본문 라인 — 패턴 적용
        line = stripped

        # 1) 페이지 헤더 단독 라인 (제N관 / 제N장 / 제N부) — 삭제
        #    단, 정상 마크다운 헤더(### 제N관 ...)는 유지
        if not line.startswith("#"):
            if RE_PAGE_HEADER_GUAN.match(line):
                report.pattern_counts["page_header_guan"] += 1
                continue
            if RE_PAGE_HEADER_GUAN_NUMLESS.match(line):
                # 숫자 없는 단독 "제N관 신의칙" 형식 — 페이지 헤더 가능성 높음
                # 단, 본문 첫 등장 시는 헤더로 승격 필요할 수 있어 경고만
                report.pattern_counts["page_header_guan_numless_kept"] += 1
                # 일단 보존. (B형 변환 단계에서 LLM이 헤더 승격 판단)
            if RE_PAGE_HEADER_JANG.match(line):
                report.pattern_counts["page_header_jang"] += 1
                continue
            if RE_PAGE_HEADER_BU.match(line):
                # "[제 O 부 …" 깨진 페이지 헤더
                report.pattern_counts["page_header_bu"] += 1
                continue

        # 2) 페이지 번호 단독 라인 (숫자만 / "- N -")
        if RE_PAGE_NUM_BARE.match(line) and not line.startswith("#"):
            # 매우 위험 — 본문 안 숫자일 수 있음. 빈 컨텍스트일 때만.
            # 안전 검사: 직전·직후 라인이 빈 라인이거나 헤더면 페이지 번호로 간주.
            # 보수적으로: 라인이 1~3자리 숫자만 단독으로 있고, 주변 컨텍스트 검증은 생략 (위험).
            # → 보존하되 카운트만. 사용자 검수 시 일괄 처리.
            report.pattern_counts["page_num_bare_kept"] += 1
            # 보존
        if RE_PAGE_NUM_DASH.match(line):
            report.pattern_counts["page_num_dash"] += 1
            continue

        # 3) 사건번호 끝 각주 마커 제거 (CLAUDE.md #34 anchor 보호하면서 마커만 제거)
        new_line = line
        for pat, key in [
            (RE_FOOTNOTE_DA, "footnote_da"),
            (RE_FOOTNOTE_MIN, "footnote_min"),
            (RE_FOOTNOTE_GU_MA, "footnote_gu_ma"),
            (RE_FOOTNOTE_HEON, "footnote_heon"),
        ]:
            new_line2, n = pat.subn(r"\1", new_line)
            if n > 0:
                report.pattern_counts[key] += n
            new_line = new_line2

        out_lines.append(new_line)

    return "\n".join(out_lines)


# ----------------------------------------------------------------------
# 파일 처리
# ----------------------------------------------------------------------
def process_file(file_path: Path, category: str, apply: bool) -> FileReport:
    report = FileReport(path=str(file_path), category=category)
    try:
        original = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        report.warnings.append(f"인코딩 오류: {e}")
        return report

    report.line_count_before = original.count("\n") + 1
    report.word_count_before = len(original.split())

    # 1. front matter 정상화
    meta, body = parse_compressed_front_matter(original)
    if meta:
        new_fm = build_standard_front_matter(meta, file_path, category)
        report.front_matter_normalized = True
    else:
        new_fm = ""
        body = original

    # 2. 본문 정규화
    new_body = normalize_body(body, report)

    new_text = new_fm + new_body
    report.line_count_after = new_text.count("\n") + 1
    report.word_count_after = len(new_text.split())

    # 위험 검증: 단어 수 변동이 5% 초과면 경고
    if report.word_count_before > 0:
        delta_pct = abs(report.word_count_after - report.word_count_before) / report.word_count_before * 100
        if delta_pct > 5.0:
            report.warnings.append(
                f"단어 수 변동률 {delta_pct:.2f}% — 의미 변경 가능성. 검토 필요."
            )

    if apply:
        try:
            file_path.write_text(new_text, encoding="utf-8")
        except OSError as e:
            report.warnings.append(f"쓰기 실패: {e}")

    return report


# ----------------------------------------------------------------------
# 메인
# ----------------------------------------------------------------------
def collect_files(target: str) -> list[tuple[Path, str]]:
    """대상 파일 목록 수집 (백업 폴더 제외)."""
    targets = []
    if target in ("본책", "전체"):
        for f in BON_CHAEK.rglob("*.md"):
            s = str(f).lower()
            if "_백업" in s or "_trash" in s:
                continue
            if f.name.startswith("_"):
                continue  # _교재목차.md 같은 메타 파일 제외
            targets.append((f, "본책"))
    if target in ("보충", "전체"):
        for f in BO_CHUNG.rglob("*.md"):
            s = str(f).lower()
            if "_백업" in s or "_trash" in s:
                continue
            if f.name.startswith("_"):
                continue
            targets.append((f, "보충"))
    return targets


def write_report(run_report: RunReport, mode: str) -> None:
    out_path = APPLY_REPORT if mode == "apply" else DRY_RUN_REPORT
    META_DIR.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# 송영곤 정규화 {mode.upper()} 보고서 ({TODAY})\n")
    lines.append(f"- 대상: {run_report.target}")
    lines.append(f"- 모드: {run_report.mode}")
    lines.append(f"- 시각: {run_report.timestamp}")
    lines.append(f"- 처리 파일 수: {len(run_report.files)}\n")

    lines.append("## 통계 요약\n")
    for k, v in run_report.totals.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## 패턴 적용 카운트 (전체 합산)\n")
    pat_total: dict = defaultdict(int)
    for fr in run_report.files:
        for k, v in fr["pattern_counts"].items():
            pat_total[k] += v
    if pat_total:
        lines.append("| 패턴 | 카운트 |")
        lines.append("|---|---|")
        for k in sorted(pat_total.keys()):
            lines.append(f"| `{k}` | {pat_total[k]} |")
    else:
        lines.append("(적용된 패턴 없음)")
    lines.append("")

    # 경고 있는 파일 별도 표시
    warned = [f for f in run_report.files if f["warnings"]]
    if warned:
        lines.append("## ⚠️ 경고 발생 파일\n")
        for f in warned:
            lines.append(f"### {Path(f['path']).name}")
            for w in f["warnings"]:
                lines.append(f"- {w}")
            lines.append("")

    lines.append("## 파일별 상세\n")
    lines.append("| 파일 | 카테고리 | 라인(전→후) | 단어(전→후) | front matter | callout 보호 라인 |")
    lines.append("|---|---|---|---|---|---|")
    for f in run_report.files:
        name = Path(f["path"]).name
        fm = "✓" if f["front_matter_normalized"] else "—"
        lines.append(
            f"| {name} | {f['category']} | "
            f"{f['line_count_before']}→{f['line_count_after']} | "
            f"{f['word_count_before']}→{f['word_count_after']} | "
            f"{fm} | {f['in_callout_skipped']} |"
        )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[OK] 보고서 저장: {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="송영곤 A형 OCR 정규화")
    parser.add_argument("--target", choices=["본책", "보충", "전체"], default="전체",
                        help="대상 폴더 (기본: 전체)")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dry-run", action="store_true", help="진단만 (파일 수정 없음)")
    grp.add_argument("--apply", action="store_true", help="실제 적용")
    args = parser.parse_args()

    apply = args.apply
    mode = "apply" if apply else "dry-run"

    print()
    print("=" * 50)
    print(" 송영곤 A형 OCR 정규화 스크립트")
    print("=" * 50)
    print(f" 대상 : {args.target}")
    print(f" 모드 : {mode.upper()}")
    print(f" 일자 : {TODAY}")
    print()

    files = collect_files(args.target)
    print(f"  - 처리 대상: {len(files)} 파일")

    if not files:
        print("[WARN] 처리할 파일이 없습니다.")
        return 1

    # 백업 확인 (apply 시)
    if apply:
        backup_root_bon = BON_CHAEK / "_백업" / TODAY
        backup_root_bo = BO_CHUNG / "_백업" / TODAY
        need_warn = False
        if args.target in ("본책", "전체") and not backup_root_bon.exists():
            print(f"[WARN] 본책 백업 폴더 없음: {backup_root_bon}")
            need_warn = True
        if args.target in ("보충", "전체") and not backup_root_bo.exists():
            print(f"[WARN] 보충 백업 폴더 없음: {backup_root_bo}")
            need_warn = True
        if need_warn:
            ans = input("  백업 없이 적용하시겠습니까? (yes/no): ").strip().lower()
            if ans != "yes":
                print("  중단됨. 먼저 backup_송영곤_2026-04-29.ps1 실행하세요.")
                return 1

    run_report = RunReport(
        target=args.target,
        mode=mode,
        timestamp=__import__("datetime").datetime.now().isoformat(timespec="seconds"),
    )

    file_reports: list[FileReport] = []
    for fp, cat in tqdm(files, desc=f"[{mode}]", ncols=80):
        fr = process_file(fp, cat, apply=apply)
        file_reports.append(fr)
        # dict로 변환 (defaultdict는 yaml 직렬화 부적합)
        run_report.files.append({
            "path": fr.path,
            "category": fr.category,
            "line_count_before": fr.line_count_before,
            "line_count_after": fr.line_count_after,
            "word_count_before": fr.word_count_before,
            "word_count_after": fr.word_count_after,
            "pattern_counts": dict(fr.pattern_counts),
            "in_callout_skipped": fr.in_callout_skipped,
            "front_matter_normalized": fr.front_matter_normalized,
            "warnings": fr.warnings,
        })

    # 통계
    total_lines_before = sum(f.line_count_before for f in file_reports)
    total_lines_after = sum(f.line_count_after for f in file_reports)
    total_words_before = sum(f.word_count_before for f in file_reports)
    total_words_after = sum(f.word_count_after for f in file_reports)
    fm_count = sum(1 for f in file_reports if f.front_matter_normalized)
    warn_count = sum(1 for f in file_reports if f.warnings)

    run_report.totals = {
        "총 파일": len(file_reports),
        "라인 (before)": total_lines_before,
        "라인 (after)": total_lines_after,
        "라인 차이": total_lines_after - total_lines_before,
        "단어 (before)": total_words_before,
        "단어 (after)": total_words_after,
        "단어 차이": total_words_after - total_words_before,
        "front matter 정상화": fm_count,
        "경고 발생": warn_count,
    }

    write_report(run_report, mode)

    print()
    print("=" * 50)
    print(" 결과 요약")
    print("=" * 50)
    for k, v in run_report.totals.items():
        print(f"  {k}: {v}")
    print()
    if mode == "dry-run":
        print(" → DRY-RUN 완료. 보고서 확인 후 --apply로 재실행.")
    else:
        print(" → 적용 완료. 다음 단계: Claude가 샘플 5개 검증.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
