#!/usr/bin/env python3
"""problem_index.json에서 쟁점(issue)을 추출하고 빈도를 분석하여
issue_frequency.json을 생성한다.

사용법:
    python extract_issues.py [--subject 민법] [--top N] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROBLEM_KINDS = ("dt", "case", "textbook")

# ── 워크스페이스 경로 ──────────────────────────────────────────
def find_workspace_root() -> Path | None:
    candidates = [Path.cwd().resolve(), Path(__file__).resolve()]
    seen: set[Path] = set()
    for c in candidates:
        for p in [c, *c.parents]:
            if p in seen:
                continue
            seen.add(p)
            if (p / ".agent").exists():
                return p
    return None


WORKSPACE = find_workspace_root() or Path(".")
STATE_DIR = WORKSPACE / ".agent" / "state"
INDEX_PATH = STATE_DIR / "problem_index.json"
OUTPUT_PATH = STATE_DIR / "issue_frequency.json"


# ── 인덱스 로드 ───────────────────────────────────────────────
def load_index() -> dict[str, Any] | None:
    if not INDEX_PATH.exists():
        print(f"인덱스 파일이 없습니다: {INDEX_PATH}")
        return None
    with open(INDEX_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


# ── 쟁점 키워드 매핑 ──────────────────────────────────────────
# topic 이름 + keywords 로부터 쟁점 명칭을 정규화한다.
# question_text에서 관련 쟁점을 매칭할 때도 사용.

# 과목별 쟁점 키워드 패턴 (교차 오염 방지)
SUBJECT_ISSUE_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "민법": [
        ("권리남용", re.compile(r"권리남용")),
        ("신의칙", re.compile(r"신의성실|신의칙")),
        ("법률행위", re.compile(r"법률행위")),
        ("의사표시", re.compile(r"의사표시")),
        ("착오", re.compile(r"착오(?!론)")),
        ("사기·강박", re.compile(r"사기(?!죄)|강박|기망")),
        ("대리", re.compile(r"대리인|무권대리|표현대리|자기계약|쌍방대리|복대리")),
        ("무효·취소", re.compile(r"무효[인의]|취소[권할가]|추인")),
        ("조건·기한", re.compile(r"정지조건|해제조건|불확정기한|확정기한")),
        ("소멸시효", re.compile(r"소멸시효|시효중단|시효완성")),
        ("권리능력", re.compile(r"권리능력|태아의?\s*권리")),
        ("행위능력", re.compile(r"행위능력|미성년자|성년후견|피성년후견|제한능력자")),
        ("법인", re.compile(r"법인(?!격)|사단법인|재단법인|비법인사단")),
        ("물권법정주의", re.compile(r"물권법정주의")),
        ("물권변동", re.compile(r"물권변동|등기청구|소유권이전등기|등기의\s*추정력|공신력")),
        ("점유·소유", re.compile(r"점유권|점유취득|소유권(?!이전등기)|공동소유|점유보호")),
        ("담보물권", re.compile(r"저당권|질권|유치권")),
        ("채무불이행", re.compile(r"채무불이행|이행지체|이행불능|불완전이행")),
        ("불법행위", re.compile(r"불법행위|손해배상청구")),
        ("계약", re.compile(r"계약(?:의\s*성립|해제|해지)|청약|동시이행|위험부담")),
        ("매매", re.compile(r"매매계약|하자담보|매도인|매수인")),
        ("부당이득", re.compile(r"부당이득|비채변제|불법원인급여")),
        ("임대차", re.compile(r"임대차|임차[인권]|전대차")),
    ],
    "형법": [
        ("구성요건", re.compile(r"구성요건")),
        ("인과관계", re.compile(r"인과관계|상당인과관계")),
        ("객관적 귀속", re.compile(r"객관적\s*귀속")),
        ("고의", re.compile(r"(?<![비과])고의(?![과])|미필적\s*고의|확정적\s*고의|개괄적\s*고의")),
        ("과실범", re.compile(r"과실범|주의의무|예견가능성|신뢰의\s*원칙")),
        ("구성요건적 착오", re.compile(r"구성요건적?\s*착오|사실의?\s*착오|구체적\s*부합|법정적\s*부합")),
        ("금지착오", re.compile(r"금지착오|위법성의?\s*착오|법률의?\s*착오|§16")),
        ("위법성조각사유", re.compile(r"위법성\s*조각|정당행위|피해자\s*승낙|자구행위")),
        ("정당방위", re.compile(r"정당방위")),
        ("긴급피난", re.compile(r"긴급피난")),
        ("책임", re.compile(r"책임능력|책임조각|기대가능성|강요된\s*행위")),
        ("미수", re.compile(r"미수범|불능미수|중지미수|장애미수|실행의\s*착수|예비")),
        ("공범", re.compile(r"공동정범|간접정범|교사범|방조범|공범(?:과\s*신분|종속|독립)")),
        ("죄수", re.compile(r"죄수|상상적\s*경합|실체적\s*경합|포괄일죄|법조경합")),
        ("부작위범", re.compile(r"부작위범|보증인\s*지위|부진정\s*부작위")),
        ("우연방위", re.compile(r"우연방위")),
        ("원인에서 자유로운 행위", re.compile(r"원인에서\s*자유|원자행")),
    ],
    "헌법": [
        ("기본권 총론", re.compile(r"기본권(?:의\s*(?:본질|제한|성격|주체|효력))|기본권\s*보장")),
        ("평등권", re.compile(r"평등[권원칙]|차별금지|합리적\s*차별")),
        ("자유권", re.compile(r"자유권|신체의?\s*자유|표현의?\s*자유|양심의?\s*자유|종교의?\s*자유|직업의?\s*자유")),
        ("비례원칙", re.compile(r"비례원칙|과잉금지원칙|비례의\s*원칙")),
        ("위헌심사", re.compile(r"위헌[심법]사|헌법소원|권한쟁의")),
        ("법치주의", re.compile(r"법치주의|법률유보|포괄위임금지")),
        ("권력분립", re.compile(r"권력분립|삼권분립")),
        ("헌법재판", re.compile(r"헌법재판소|위헌결정|한정합헌|한정위헌")),
        ("국회", re.compile(r"국회의원|국회의?\s*권한|입법[권절]")),
        ("대통령", re.compile(r"대통령(?:의\s*권한|제|선거)|긴급명령|사면")),
        ("법원", re.compile(r"사법[권부]|재판(?:의\s*전제|청구)|법관의?\s*독립")),
        ("선거제도", re.compile(r"선거[제권]|선거의?\s*원칙|보통선거")),
        ("지방자치", re.compile(r"지방자치|자치[권입법]|조례")),
        ("사회적 기본권", re.compile(r"사회적\s*기본권|교육[권을]|근로[권의]|환경권")),
    ],
}


def match_issues(text: str, subject_hint: str = "") -> list[str]:
    """텍스트에서 매칭되는 쟁점 이름들을 반환. subject_hint로 해당 과목 패턴만 검색."""
    found: list[str] = []
    # 과목 힌트에 맞는 패턴 세트 선택
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for subj_key, subj_patterns in SUBJECT_ISSUE_PATTERNS.items():
        if not subject_hint or subj_key in subject_hint:
            patterns.extend(subj_patterns)

    for name, pattern in patterns:
        if pattern.search(text):
            found.append(name)
    return found


# ── 쟁점 빈도 추출 ────────────────────────────────────────────
def extract_subject_issues(subject_name: str, subject_data: dict[str, Any]) -> list[dict[str, Any]]:
    """한 과목의 모든 토픽·문제를 순회하며 쟁점 빈도를 추출.
    카운트 기준: question_text에서 매칭된 횟수 (문제 1개 = 1회).
    토픽 레벨 쟁점은 해당 토픽 정보로만 사용하고 빈도를 부풀리지 않는다."""
    issue_counter: Counter[str] = Counter()
    issue_problems: defaultdict[str, list[str]] = defaultdict(list)
    issue_statutes: defaultdict[str, set[str]] = defaultdict(set)
    issue_topics: defaultdict[str, set[str]] = defaultdict(set)

    topics = subject_data.get("topics", {})
    for topic_name, topic_data in topics.items():
        keywords = topic_data.get("keywords", [])
        toc_path = topic_data.get("toc_path", "")

        # 토픽 이름과 키워드에서 쟁점 매칭 (메타 정보용, 빈도 카운트 아님)
        topic_text = f"{topic_name} {' '.join(keywords)} {toc_path}"
        topic_issues = match_issues(topic_text, subject_name)

        # 조문 번호 추출
        statute_matches = re.findall(r"§(\d+)|제(\d+)조", topic_text)
        statutes = {f"§{m[0] or m[1]}" for m in statute_matches}
        for issue in topic_issues:
            issue_statutes[issue].update(statutes)
            issue_topics[issue].add(topic_name)

        # 각 문제 텍스트에서 쟁점 매칭 — 문제 1건 = 1회 카운트
        problems = topic_data.get("problems", {})
        for kind in PROBLEM_KINDS:
            for item in problems.get(kind, []):
                if isinstance(item, str):
                    continue
                q_text = item.get("question_text", "")
                q_id = item.get("id", item.get("display_label", "unknown"))
                if not q_text:
                    continue

                q_issues = match_issues(q_text, subject_name)
                q_statutes = re.findall(r"§(\d+)|제(\d+)조", q_text)
                q_statute_set = {f"§{m[0] or m[1]}" for m in q_statutes}

                for issue in q_issues:
                    issue_counter[issue] += 1
                    issue_problems[issue].append(q_id)
                    issue_statutes[issue].update(q_statute_set)
                    issue_topics[issue].add(topic_name)

    # 빈도순 정렬 + 랭크 부여
    sorted_issues = issue_counter.most_common()
    results: list[dict[str, Any]] = []
    for rank, (name, freq) in enumerate(sorted_issues, 1):
        results.append({
            "name": name,
            "frequency": freq,
            "rank": rank,
            "problem_ids": sorted(set(issue_problems[name]))[:30],  # 최대 30개
            "related_statutes": sorted(issue_statutes[name]),
            "related_topics": sorted(issue_topics[name]),
        })

    return results


def scan_md_files(md_dirs: list[str], subject_hint: str) -> list[dict[str, Any]]:
    """마크다운 파일들을 직접 스캔하여 쟁점 빈도를 추출.
    problem_index에 데이터가 없는 과목(형법, 헌법)에 사용."""
    issue_counter: Counter[str] = Counter()
    issue_files: defaultdict[str, list[str]] = defaultdict(list)
    issue_statutes: defaultdict[str, set[str]] = defaultdict(set)
    total_pages = 0

    for md_dir in md_dirs:
        dir_path = Path(md_dir)
        if not dir_path.exists():
            print(f"  [경고] 경로 없음: {md_dir}")
            continue
        md_files = sorted(dir_path.glob("*.md"))
        for md_file in md_files:
            if md_file.name == "chunks_index.json":
                continue
            # pdf_extracts에서는 해당 과목 파일만 필터
            if "pdf_extracts" in str(dir_path):
                if subject_hint == "형법" and not md_file.name.startswith("crm_"):
                    continue
                if subject_hint == "헌법" and not md_file.name.startswith("con_"):
                    continue
            try:
                text = md_file.read_text(encoding="utf-8")
            except Exception:
                continue

            # 페이지 단위로 분할 (--- Page N --- 구분자)
            pages = re.split(r"---\s*Page\s+\d+\s*---", text)
            if len(pages) <= 1:
                # 페이지 구분 없으면 500자 단위로 분할
                pages = [text[i:i+500] for i in range(0, len(text), 500)]

            for page in pages:
                if not page.strip():
                    continue
                total_pages += 1
                page_issues = match_issues(page, subject_hint)
                page_statutes = re.findall(r"§(\d+)|제(\d+)조", page)
                page_statute_set = {f"§{m[0] or m[1]}" for m in page_statutes}

                for issue in page_issues:
                    issue_counter[issue] += 1
                    if md_file.name not in issue_files[issue]:
                        issue_files[issue].append(md_file.name)
                    issue_statutes[issue].update(page_statute_set)

    # 빈도순 정렬
    sorted_issues = issue_counter.most_common()
    results: list[dict[str, Any]] = []
    for rank, (name, freq) in enumerate(sorted_issues, 1):
        results.append({
            "name": name,
            "frequency": freq,
            "rank": rank,
            "problem_ids": [],
            "related_statutes": sorted(issue_statutes[name]),
            "related_topics": sorted(set(issue_files[name]))[:10],
        })

    return results, total_pages


def build_frequency_index(index: dict[str, Any], subject_filter: str | None = None,
                          md_scan_config: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """전체 인덱스에서 쟁점 빈도를 추출.
    md_scan_config가 주어지면 마크다운 직접 스캔도 병행."""
    subjects_data = index.get("subjects", {})
    result_subjects: dict[str, Any] = {}

    for subject_name, subject_data in subjects_data.items():
        if subject_filter and subject_filter not in subject_name:
            continue
        issues = extract_subject_issues(subject_name, subject_data)
        if issues:
            result_subjects[subject_name] = {
                "total_issues": len(issues),
                "total_problems_scanned": sum(
                    len(problems.get(k, []))
                    for topic in subject_data.get("topics", {}).values()
                    for k in PROBLEM_KINDS
                    for problems in [topic.get("problems", {})]
                ),
                "issues": issues,
            }

    # 마크다운 직접 스캔 (problem_index에 없는 과목)
    if md_scan_config:
        for subject_name, md_dirs in md_scan_config.items():
            if subject_filter and subject_filter not in subject_name:
                continue
            if subject_name in result_subjects and result_subjects[subject_name]["total_problems_scanned"] > 0:
                continue  # 이미 problem_index에 데이터 있으면 스킵
            print(f"\n[MD 스캔] {subject_name}: {len(md_dirs)}개 디렉토리")
            issues, total_pages = scan_md_files(md_dirs, subject_name)
            if issues:
                result_subjects[subject_name] = {
                    "total_issues": len(issues),
                    "total_problems_scanned": total_pages,
                    "scan_source": "md_files",
                    "issues": issues,
                }

    return {
        "version": "1.0",
        "last_updated": date.today().isoformat(),
        "subjects": result_subjects,
    }


# ── CLI ────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="쟁점 빈도 추출기")
    parser.add_argument("--subject", "-s", type=str, default=None, help="과목 필터 (예: 민법)")
    parser.add_argument("--top", "-n", type=int, default=15, help="상위 N개 출력 (기본 15)")
    parser.add_argument("--dry-run", action="store_true", help="파일 저장 없이 결과만 출력")
    parser.add_argument("--scan-md", action="store_true",
                        help="problem_index 외에 마크다운 파일도 직접 스캔 (형법/헌법용)")
    args = parser.parse_args()

    index = load_index()
    if index is None:
        return

    # 마크다운 직접 스캔 설정 (형법/헌법은 problem_index에 데이터 없음)
    md_scan_config = None
    if args.scan_md:
        md_scan_config = {
            "형법": [
                str(WORKSPACE / ".agent/data/pdf_extracts"),  # crm_1-1(김성돈), crm_1-2(서보학)
                str(WORKSPACE / "2.형사/20.서보학_형법1/기출_추출"),
                str(WORKSPACE / "2.형사/20.서보학_형법1/사례_추출"),
            ],
            "헌법": [
                str(WORKSPACE / "3.공법/91.보관/강성민_헌법ox/정리_추출"),
                str(WORKSPACE / "3.공법/10.이진_헌법원리1/정리"),
            ],
        }

    freq_index = build_frequency_index(index, args.subject, md_scan_config)

    # 콘솔 출력
    for subject_name, data in freq_index["subjects"].items():
        print(f"\n{'='*60}")
        print(f"[{subject_name}] 총 문제 {data['total_problems_scanned']}건 스캔 → 쟁점 {data['total_issues']}종 추출")
        print(f"{'='*60}")
        for issue in data["issues"][:args.top]:
            statutes = ", ".join(issue["related_statutes"][:5]) or "-"
            topics = ", ".join(issue["related_topics"][:3]) or "-"
            print(f"  #{issue['rank']:>2}  {issue['name']:<16}  빈도 {issue['frequency']:>3}  조문 [{statutes}]  토픽 [{topics}]")

    # 파일 저장
    if not args.dry_run:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(freq_index, f, ensure_ascii=False, indent=2)
        print(f"\n저장 완료: {OUTPUT_PATH}")
    else:
        print("\n[dry-run] 파일 저장 건너뜀")


if __name__ == "__main__":
    main()
