import os
import sys
import json
import argparse

# study-notes/scripts/collect.py
# 지정된 타겟 파일을 읽어와 컨텍스트(study-notes-context.json)로 저장함.
# qmd law-notes 검색은 .agent/lib/qmd_search.py 연동으로 확장 가능.

STATE_DIR = r"H:\내 드라이브\.agent\state"
CONTEXT_FILE = os.path.join(STATE_DIR, "study-notes-context.json")
ISSUE_FREQ_FILE = os.path.join(STATE_DIR, "issue_frequency.json")


def load_issue_priority(subject_hint: str, top_n: int = 15) -> list[dict]:
    """issue_frequency.json에서 해당 과목의 상위 N개 쟁점을 로드."""
    if not os.path.exists(ISSUE_FREQ_FILE):
        return []
    try:
        with open(ISSUE_FREQ_FILE, 'r', encoding='utf-8') as f:
            freq = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    for subj_name, subj_data in freq.get("subjects", {}).items():
        if subject_hint and subject_hint in subj_name:
            issues = subj_data.get("issues", [])
            return [
                {
                    "name": iss["name"],
                    "frequency": iss["frequency"],
                    "rank": iss["rank"],
                    "related_statutes": iss.get("related_statutes", [])[:5],
                    "related_topics": iss.get("related_topics", [])[:5],
                }
                for iss in issues[:top_n]
            ]
    return []


def detect_subject(target_path: str) -> str:
    """파일 경로에서 과목명을 추정."""
    path_lower = target_path.lower()
    for keyword, subject in [("민법", "민법"), ("민사", "민법"), ("형법", "형법"), ("형사", "형법"), ("헌법", "헌법"), ("공법", "헌법")]:
        if keyword in path_lower:
            return subject
    return ""


def main():
    parser = argparse.ArgumentParser(description="노트 정리용 소스 수집기")
    parser.add_argument("--target", required=True, help="기반이 될 타겟 원본 파일 경로")
    parser.add_argument("--mode", required=True, choices=["concept", "case", "exam"], help="컨텍스트 수집 모드")
    parser.add_argument("--subject", default=None, help="과목명 (자동 감지 우선)")
    args = parser.parse_args()

    if not os.path.exists(args.target):
        print(f"Error: Target file not found - {args.target}")
        sys.exit(1)

    with open(args.target, 'r', encoding='utf-8') as f:
        content = f.read()

    # 과목 감지 + 쟁점 빈도 로드
    subject = args.subject or detect_subject(args.target)
    issue_priority = load_issue_priority(subject)

    context_data = {
        "source_file": args.target,
        "mode": args.mode,
        "subject": subject,
        "content_length": len(content),
        "content": content,
        "additional_references": [],
        "issue_priority": issue_priority,
    }

    os.makedirs(STATE_DIR, exist_ok=True)
    with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
        json.dump(context_data, f, ensure_ascii=False, indent=2)

    print(f"Context successfully collected for mode '{args.mode}' (subject: {subject or 'unknown'}).")
    if issue_priority:
        print(f"Issue priority loaded: {len(issue_priority)} issues (top: {issue_priority[0]['name']})")
    else:
        print("Issue priority: none (issue_frequency.json not found or subject unmatched)")
    print(f"Saved to: {CONTEXT_FILE}")

if __name__ == "__main__":
    main()
