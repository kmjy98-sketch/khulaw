"""
06a manual 모드 — 사용자 user_issue_list 기반 사례집 카드화.

사용법:
    python scripts/06a_manual.py <input.md|input.xml>

입력 파일 형식 (Markdown 또는 XML, 다음 키 포함):
    subject: 민법
    source: 민법사례연습-p234
    case_id: 민법연습-p234
    difficulty: A
    scope: [선택]
    skip_topics: [선택]
    
    [case_problem]
    (사안 + 모든 설문)
    
    [user_issue_list]
    설문1 → 채권자취소권 성립 / 제406조 ① / 사해행위·악의 추정
    설문2 → ...
"""

import argparse
import sys
import time
from pathlib import Path

try:
    from anthropic import Anthropic
except ImportError:
    print("ERROR: anthropic SDK 미설치. pip install anthropic")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (
    get_anthropic_key, setup_logger, read_prompt, log_cost,
    save_output, verify_tsv, PACKAGE_ROOT
)


def parse_input_file(path: Path) -> dict:
    """입력 파일 → dict 파싱.
    YAML frontmatter 스타일 (key: value) + [section] 블록."""
    content = path.read_text(encoding="utf-8")
    
    fields = {
        "subject": "",
        "source": path.stem,
        "case_id": path.stem,
        "difficulty": "A",
        "scope": "",
        "skip_topics": "",
        "case_problem": "",
        "user_issue_list": "",
    }
    
    # 단순 파싱: key: value 줄 + [section] 블록
    lines = content.split("\n")
    current_section = None
    section_content = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # [section] 마커
        if line_stripped.startswith("[") and line_stripped.endswith("]"):
            if current_section and section_content:
                fields[current_section] = "\n".join(section_content).strip()
            current_section = line_stripped[1:-1]
            section_content = []
            continue
        
        # key: value (section 외부에서만)
        if current_section is None and ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            key = key.strip()
            if key in fields:
                fields[key] = val.strip()
                continue
        
        # section 내부 본문
        if current_section:
            section_content.append(line)
    
    # 마지막 section 저장
    if current_section and section_content:
        fields[current_section] = "\n".join(section_content).strip()
    
    return fields


def main():
    parser = argparse.ArgumentParser(description="06a manual 사례집 카드화")
    parser.add_argument("input", help="입력 파일 (.md 또는 .xml)")
    parser.add_argument("--output-name", default=None)
    args = parser.parse_args()
    
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"ERROR: 입력 파일 없음: {input_path}")
        sys.exit(1)
    
    logger = setup_logger("06a_manual")
    logger.info(f"=== 06a manual 시작 ===")
    logger.info(f"Input: {input_path.name}")
    
    fields = parse_input_file(input_path)
    
    if not fields["case_problem"]:
        logger.error("case_problem 섹션이 비어있습니다.")
        sys.exit(1)
    if not fields["user_issue_list"]:
        logger.error(
            "user_issue_list가 비어있습니다.\n"
            "06a(manual)은 user_issue_list가 필수.\n"
            "사례집에 풀이가 포함됐다면 06b(extract) 사용을 권장합니다."
        )
        sys.exit(1)
    
    # 환경
    api_key = get_anthropic_key()
    client = Anthropic(api_key=api_key)
    
    # 프롬프트
    system_prompt = read_prompt("06a_claude_사례집문제_manual_v3.6.xml")
    
    # user message 조립
    user_message = f"""<input>
  <subject>{fields['subject']}</subject>
  <source>{fields['source']}</source>
  <case_id>{fields['case_id']}</case_id>
  <difficulty>{fields['difficulty']}</difficulty>
  <scope>{fields['scope']}</scope>
  <skip_topics>{fields['skip_topics']}</skip_topics>
  <case_problem>
{fields['case_problem']}
  </case_problem>
  <user_issue_list>
{fields['user_issue_list']}
  </user_issue_list>
</input>"""
    
    logger.info(f"Claude Opus 4.8 호출 중...")
    start = time.time()
    
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=32000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    
    elapsed = time.time() - start
    output_text = "".join(b.text for b in response.content if hasattr(b, "text"))
    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    
    logger.info(f"완료 ({elapsed:.1f}s, in={in_tok}, out={out_tok})")
    
    # 저장
    out_filename = args.output_name or f"{input_path.stem}_06a_TSV.txt"
    out_path = save_output(output_text, "06_cases", out_filename)
    logger.info(f"저장: {out_path.relative_to(PACKAGE_ROOT)}")
    
    # 검증
    import re
    tsv_blocks = re.findall(r"```tsv\n(.+?)```", output_text, re.DOTALL)
    for i, tsv in enumerate(tsv_blocks, 1):
        result = verify_tsv(tsv)
        logger.info(f"TSV 블록 {i}: 카드 {result['card_count']}장, 이슈 {len(result['issues'])}")
        for issue in result["issues"]:
            logger.warning(f"  - {issue}")
    
    log_cost("claude-opus-4-8", in_tok, out_tok)
    cost = (in_tok / 1e6 * 15.0 + out_tok / 1e6 * 75.0)
    logger.info(f"예상 비용: ${cost:.2f}")
    logger.info(f"=== 완료 ===")


if __name__ == "__main__":
    main()
