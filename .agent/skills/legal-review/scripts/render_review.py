#!/usr/bin/env python3
"""Render a playbook-based legal review report."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT = SCRIPT_DIR.parents[3]
STATE_DIR = ROOT / ".agent" / "state"
DEFAULT_PLAYBOOK = STATE_DIR / "legal_playbook.md"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from load_playbook import parse_playbook  # noqa: E402


MISSING_NOTE = "자료 부족—보류"
SOURCE_MISSING = "소스에서 확인할 수 없습니다"
NO_HIT = "없음"


def default_playbook() -> dict:
    return {
        "source": "generic-default",
        "metadata": {
            "primary_jurisdiction": "Korea",
            "review_language": "ko-KR",
            "local_venue_tokens": "korea, republic of korea, seoul",
        },
        "clauses": [
            {
                "clause": "Limitation of Liability",
                "keywords": ["limitation of liability", "liability cap", "cap on liability", "consequential damages"],
                "favorable_signals": ["mutual cap", "fees paid", "direct damages only"],
                "standard_position": "Use a mutual liability cap tied to contract value with narrow carveouts.",
                "acceptable_range": "A fees-paid cap with narrow carveouts is acceptable.",
                "fallback_position": "If a full mutual cap is unavailable, cap direct damages at fees paid in the prior 12 months.",
                "redline_suggestion": "Replace uncapped general liability with a mutual cap tied to fees and narrow carveouts.",
                "business_impact": "Uncapped liability can exceed contract value and change pricing, reserve, and approval needs.",
                "negotiation_priority": "must-have",
                "escalation_triggers": ["unlimited liability", "uncapped liability", "consequential damages"],
                "notes": [],
            },
            {
                "clause": "Data Protection",
                "keywords": ["data protection", "privacy", "personal data", "processor", "security", "breach"],
                "favorable_signals": ["dpa", "breach notice", "return or delete"],
                "standard_position": "Require processing instructions, security commitments, breach notification, and subprocessor controls.",
                "acceptable_range": "Equivalent privacy and security controls are acceptable if they match internal standards.",
                "fallback_position": "Require a DPA, a bounded breach notice window, and safeguards for cross-border transfers.",
                "redline_suggestion": "Add DPA, security, breach-notice, subprocessor, and return-or-delete language.",
                "business_impact": "Missing privacy controls creates regulatory and customer exposure that often exceeds deal value.",
                "negotiation_priority": "must-have",
                "escalation_triggers": ["no dpa", "cross-border transfer without safeguards", "unrestricted data use"],
                "notes": [],
            },
            {
                "clause": "NDA Mutuality",
                "keywords": ["confidential information", "non-disclosure", "confidentiality", "one-way nda"],
                "favorable_signals": ["mutual confidentiality", "both parties", "each party"],
                "standard_position": "Confidentiality obligations should be mutual unless a one-way flow is clearly justified.",
                "acceptable_range": "A one-way NDA is acceptable only when the business rationale is documented.",
                "fallback_position": "If one-way confidentiality is unavoidable, narrow it to the actual disclosure flow.",
                "redline_suggestion": "Convert confidentiality obligations to mutual form and align use, care, and disclosure limits.",
                "business_impact": "One-way NDA language can leave the business exposed during diligence and negotiations.",
                "negotiation_priority": "must-have",
                "escalation_triggers": ["one-way only", "unilateral confidentiality", "reverse engineering permitted"],
                "notes": [],
            },
        ],
    }


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf", "-q"])
        from pypdf import PdfReader

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            chunks.append(f"--- Page {index} ---\n{page_text}")
    return "\n\n".join(chunks)


def read_docx(path: Path) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for para in root.findall(".//w:p", namespace):
        texts = [node.text for node in para.findall(".//w:t", namespace) if node.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def load_input_text(input_path: str | None, inline_text: str | None) -> tuple[str, str]:
    if inline_text:
        return inline_text, "inline-text"

    if not input_path:
        raise ValueError("입력 파일 경로 또는 --text 중 하나가 필요합니다.")

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {path}")

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ""}:
        return read_text_file(path), str(path)
    if suffix == ".pdf":
        return read_pdf(path), str(path)
    if suffix == ".docx":
        return read_docx(path), str(path)

    raise ValueError(f"지원하지 않는 형식입니다: {suffix}")


def find_first_hit(text: str, terms: Iterable[str]) -> str | None:
    lowered = text.lower()
    for term in terms:
        if term and term.lower() in lowered:
            return term
    return None


def metadata_tokens(metadata: dict | None, key: str, defaults: list[str]) -> list[str]:
    if not metadata:
        return defaults
    raw = str(metadata.get(key, "")).strip()
    if not raw:
        return defaults
    return [token.strip().lower() for token in raw.split(",") if token.strip()]


def contextual_trigger(text: str, clause: dict, metadata: dict | None = None) -> str | None:
    clause_name = clause.get("clause", "").lower()
    if clause_name not in {"governing law", "dispute resolution"}:
        return None

    local_tokens = metadata_tokens(metadata, "local_venue_tokens", ["korea", "republic of korea", "seoul"])
    if clause_name == "governing law":
        patterns = [
            r"(exclusive jurisdiction of (?:the )?(?:courts?|forum) of [A-Za-z][A-Za-z ,\-]{2,60}?)(?=[.;]|$)",
            r"(exclusive venue (?:shall be|is|in) [A-Za-z][A-Za-z ,\-]{2,60}?)(?=[.;]|$)",
            r"(governed by the laws of [A-Za-z][A-Za-z ,\-]{2,60}?)(?=[.;]|$)",
            r"(laws of [A-Za-z][A-Za-z ,\-]{2,60}? govern)(?=[.;]|$)",
        ]
    else:
        patterns = [
            r"(mandatory arbitration in [A-Za-z][A-Za-z ,\-]{2,60}?)(?=[.;]|$)",
            r"(seat of arbitration (?:shall be|is|in) [A-Za-z][A-Za-z ,\-]{2,60}?)(?=[.;]|$)",
            r"(exclusive jurisdiction of (?:the )?(?:courts?|forum) of [A-Za-z][A-Za-z ,\-]{2,60}?)(?=[.;]|$)",
            r"(exclusive venue (?:shall be|is|in) [A-Za-z][A-Za-z ,\-]{2,60}?)(?=[.;]|$)",
        ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        matched = normalize_ws(match.group(1).rstrip(".,;:"))
        lowered = matched.lower()
        if any(token in lowered for token in local_tokens):
            continue
        return matched
    return None


def snippet_around(text: str, term: str, width: int = 220) -> str:
    lowered = text.lower()
    target = term.lower()
    index = lowered.find(target)
    if index < 0:
        return SOURCE_MISSING
    start = max(0, index - width)
    end = min(len(text), index + len(term) + width)
    snippet = normalize_ws(text[start:end])
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def clause_terms(clause: dict) -> list[str]:
    terms = list(clause.get("keywords", []))
    terms.append(clause.get("clause", ""))
    return [term for term in terms if term]


def infer_priority(clause: dict, status: str) -> str:
    explicit = (clause.get("negotiation_priority") or "").strip()
    if explicit:
        return explicit
    if status == "RED":
        return "must-have"
    if status == "YELLOW":
        return "should-have"
    return "monitor"


def default_redline(clause: dict, status: str) -> str:
    suggested = clause.get("redline_suggestion")
    if suggested:
        return suggested
    if status == "GREEN":
        return "현 단계에서 별도 redline 제안은 필요하지 않습니다."
    return "소스에서 확인 가능한 redline 제안이 부족합니다. 플레이북 기준 문구를 수동으로 확인하세요."


def default_fallback(clause: dict, status: str) -> str:
    fallback = clause.get("fallback_position")
    if fallback:
        return fallback
    if status == "GREEN":
        return "fallback 포지션 사용 없이 현재 문구 유지 가능성이 있습니다."
    return "자료 부족—보류"


def default_business_impact(clause: dict) -> str:
    return clause.get("business_impact") or "소스에서 확인할 수 없습니다"


def deviation_note(
    status: str,
    keyword_hit: str | None,
    trigger_hit: str | None,
    favorable_hit: str | None,
) -> str:
    if status == "RED" and trigger_hit:
        return f"에스컬레이션 트리거 `{trigger_hit}` 이 문서에서 직접 확인됩니다."
    if status == "GREEN" and favorable_hit:
        return f"Favorable signal `{favorable_hit}` was found in the document."
    if keyword_hit:
        return f"Clause-related term `{keyword_hit}` was found, but favorable alignment is not fully confirmed from source text."
    return "문서에 조항은 보이지만 플레이북 기준과의 일치 여부는 추가 확인이 필요합니다."


def evaluate_clause(text: str, clause: dict, metadata: dict | None = None) -> dict:
    terms = clause_terms(clause)
    keyword_hit = find_first_hit(text, terms)
    favorable_hit = find_first_hit(text, clause.get("favorable_signals", []))
    trigger_hit = find_first_hit(text, clause.get("escalation_triggers", []))
    contextual_hit = contextual_trigger(text, clause, metadata)
    if not trigger_hit and contextual_hit:
        trigger_hit = contextual_hit

    if trigger_hit:
        status = "RED"
        evidence_term = trigger_hit
    elif favorable_hit:
        status = "GREEN"
        evidence_term = favorable_hit
    elif keyword_hit:
        status = "YELLOW"
        evidence_term = keyword_hit
    else:
        status = "YELLOW"
        evidence_term = ""

    evidence = snippet_around(text, evidence_term) if evidence_term else MISSING_NOTE

    return {
        "clause": clause.get("clause", ""),
        "status": status,
        "matched_term": favorable_hit or keyword_hit or "",
        "trigger_hit": trigger_hit or "",
        "standard_position": clause.get("standard_position", ""),
        "acceptable_range": clause.get("acceptable_range", ""),
        "fallback_position": default_fallback(clause, status),
        "redline_suggestion": default_redline(clause, status),
        "business_impact": default_business_impact(clause),
        "negotiation_priority": infer_priority(clause, status),
        "deviation_note": deviation_note(status, keyword_hit, trigger_hit, favorable_hit),
        "evidence": evidence,
    }


def select_nda_clauses(clauses: list[dict]) -> list[dict]:
    selected = [
        clause
        for clause in clauses
        if "nda" in clause.get("clause", "").lower()
        or "confidential" in clause.get("clause", "").lower()
        or "governing law" in clause.get("clause", "").lower()
        or "dispute" in clause.get("clause", "").lower()
    ]
    return selected or clauses


def counts(results: list[dict]) -> dict[str, int]:
    data = {"GREEN": 0, "YELLOW": 0, "RED": 0}
    for item in results:
        data[item["status"]] += 1
    return data


def overall_status(results: list[dict]) -> str:
    statuses = {item["status"] for item in results}
    if "RED" in statuses:
        return "RED"
    if "YELLOW" in statuses:
        return "YELLOW"
    return "GREEN"


def issue_rows(results: list[dict]) -> str:
    rows = ["| 조항 | 상태 | 기준 키워드 | 트리거 |", "|---|---|---|---|"]
    for item in results:
        rows.append(
            f"| {item['clause']} | {item['status']} | {item['matched_term'] or '-'} | {item['trigger_hit'] or '-'} |"
        )
    return "\n".join(rows)


def sort_results(results: list[dict]) -> list[dict]:
    order = {"RED": 0, "YELLOW": 1, "GREEN": 2}
    return sorted(results, key=lambda item: (order.get(item["status"], 9), item["clause"]))


def bullet_list(lines: list[str], empty_text: str) -> str:
    if not lines:
        return f"- {empty_text}"
    return "\n".join(f"- {line}" for line in lines)


def key_findings(results: list[dict]) -> str:
    lines = []
    for item in sort_results(results):
        if item["status"] == "GREEN":
            continue
        lines.append(
            f"{item['clause']}: {item['status']} / priority={item['negotiation_priority']} / {item['deviation_note']}"
        )
    return bullet_list(lines, "추가 key finding이 없습니다.")


def redline_sections(results: list[dict]) -> str:
    blocks: list[str] = []
    for item in sort_results(results):
        if item["status"] == "GREEN":
            continue
        lines = [
            f"### {item['clause']}",
            f"- 우선순위: {item['negotiation_priority']}",
            f"- redline 제안: {item['redline_suggestion']}",
            f"- fallback 포지션: {item['fallback_position']}",
            f"- 근거 스니펫: \"{item['evidence']}\"",
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else "- RED/YELLOW 조항이 없어 별도 redline 제안은 없습니다."


def business_impacts(results: list[dict]) -> str:
    lines = []
    for item in sort_results(results):
        if item["status"] == "GREEN":
            continue
        lines.append(f"{item['clause']}: {item['business_impact']}")
    return bullet_list(lines, "문서상 별도 business impact 이슈가 두드러지지 않습니다.")


def clause_sections(results: list[dict]) -> str:
    blocks: list[str] = []
    for item in results:
        lines = [
            f"### {item['clause']}",
            f"- 상태: {item['status']}",
            f"- matched term: {item['matched_term'] or NO_HIT}",
            f"- 기준 포지션: {item['standard_position'] or SOURCE_MISSING}",
            f"- 허용 범위: {item['acceptable_range'] or SOURCE_MISSING}",
            f"- 협상 우선순위: {item['negotiation_priority'] or SOURCE_MISSING}",
            f"- fallback 포지션: {item['fallback_position'] or SOURCE_MISSING}",
            f"- redline 제안: {item['redline_suggestion'] or SOURCE_MISSING}",
            f"- business impact: {item['business_impact'] or SOURCE_MISSING}",
            f"- 편차 판단: {item['deviation_note']}",
            f"- 에스컬레이션 트리거 적중: {item['trigger_hit'] or NO_HIT}",
            f"- 근거 스니펫: \"{item['evidence']}\"",
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def next_steps(mode: str, overall: str, results: list[dict]) -> str:
    lines = []
    if overall == "RED":
        lines.append("RED 조항을 우선적으로 법무 검토로 에스컬레이션합니다.")
        lines.append("redline 제안과 fallback 포지션을 상대방 문안과 대조합니다.")
    elif overall == "YELLOW":
        lines.append("누락 또는 불명확한 조항을 원문에서 다시 확인합니다.")
        lines.append("필요 시 해당 조항의 대체 문구를 수동으로 정리합니다.")
    else:
        lines.append("현 단계에서는 플레이북과 직접 충돌하는 조항이 제한적으로 보입니다.")
        lines.append("서명 또는 회신 전 최종 법무 확인만 병행합니다.")

    must_have = [item["clause"] for item in results if item.get("negotiation_priority") == "must-have"]
    if must_have:
        lines.append(f"우선 협상 조항: {', '.join(must_have)}")

    if mode == "nda-triage":
        lines.append("NDA 분류 결과를 내부 승인 경로와 연결합니다.")

    return bullet_list(lines, "자료 부족—보류")


def review_summary(source_name: str, overall: str, result_counts: dict[str, int], fallback: bool) -> str:
    baseline = "기본 플레이북" if fallback else "로컬 플레이북"
    return (
        f"`{source_name}` 기준 검토 결과는 `{overall}`입니다. "
        f"{baseline}을 사용했고 GREEN {result_counts['GREEN']}건, "
        f"YELLOW {result_counts['YELLOW']}건, RED {result_counts['RED']}건이 집계되었습니다."
    )


def load_template(mode: str) -> str:
    template_name = "contract_review.md" if mode == "contract-review" else "nda_triage.md"
    return (SKILL_DIR / "templates" / template_name).read_text(encoding="utf-8")


def render(template: str, variables: dict[str, str]) -> str:
    output = template
    for key, value in variables.items():
        output = output.replace(f"{{{{{key}}}}}", value)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="플레이북 기반 계약/NDA 검토 보고서 생성기")
    parser.add_argument("input_path", nargs="?", help="입력 문서 경로(pdf/docx/txt/md)")
    parser.add_argument("--text", help="직접 전달할 문서 텍스트")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["contract-review", "nda-triage"],
        help="검토 모드",
    )
    parser.add_argument("--playbook", default=str(DEFAULT_PLAYBOOK), help="플레이북 경로")
    parser.add_argument("--party", default="미지정", help="당사자 역할")
    parser.add_argument("--deadline", default="미지정", help="마감 시점")
    parser.add_argument("--focus", default="미지정", help="중점 검토 사항")
    parser.add_argument("--deal-context", default="미지정", help="거래 배경")
    parser.add_argument("--output", "-o", help="출력 마크다운 경로")
    args = parser.parse_args()

    source_text, source_name = load_input_text(args.input_path, args.text)
    normalized_text = normalize_ws(source_text)
    if not normalized_text:
        raise ValueError("입력 문서에서 텍스트를 추출하지 못했습니다.")

    playbook_path = Path(args.playbook)
    if playbook_path.exists():
        playbook = parse_playbook(playbook_path)
        playbook_source = str(playbook_path)
        used_fallback = False
    else:
        playbook = default_playbook()
        playbook_source = playbook["source"]
        used_fallback = True

    clauses = playbook["clauses"]
    if args.mode == "nda-triage":
        clauses = select_nda_clauses(clauses)

    metadata = playbook.get("metadata", {})
    results = [evaluate_clause(normalized_text, clause, metadata) for clause in clauses]
    result_counts = counts(results)
    overall = overall_status(results)
    template = load_template(args.mode)

    variables = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_name": source_name,
        "playbook_source": playbook_source,
        "party": args.party,
        "deadline": args.deadline,
        "focus": args.focus,
        "deal_context": args.deal_context,
        "summary": review_summary(source_name, overall, result_counts, used_fallback),
        "overall_status": overall,
        "green_count": str(result_counts["GREEN"]),
        "yellow_count": str(result_counts["YELLOW"]),
        "red_count": str(result_counts["RED"]),
        "issues_table": issue_rows(results),
        "key_findings": key_findings(results),
        "redline_sections": redline_sections(results),
        "business_impacts": business_impacts(results),
        "clause_sections": clause_sections(results),
        "next_steps": next_steps(args.mode, overall, results),
        "disclaimer": "법률 자문이 아닌 검토 초안입니다. 최종 판단과 대외 발신 전에는 해당 법무 검토가 필요합니다.",
    }

    output = render(template, variables)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"보고서 저장됨: {output_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
