"""
06b extract 모드 — 사례집 PDF/텍스트(풀이 포함) → 카드화.
AI가 풀이 영역 자동 식별 → 쟁점 추출 → 검증필요::AI추출 태그 자동 부착.

사용법:
    python scripts/06b_extract.py <input.pdf|input.md> [옵션]

옵션:
    --subject 민법
    --source "김춘환 민법사례연습 9판"
    --case-id "김민사-p234"
    --difficulty A
    --scope "민법1·형법총론"
    --skip-topics "도산법,국제사법"
"""

import argparse
import base64
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


def build_user_message_text(input_path: Path, fields: dict) -> list:
    """텍스트 입력 → content blocks 리스트"""
    text = input_path.read_text(encoding="utf-8")
    
    user_xml = f"""<input>
  <subject>{fields['subject']}</subject>
  <source>{fields['source']}</source>
  <case_id>{fields['case_id']}</case_id>
  <difficulty>{fields['difficulty']}</difficulty>
  <scope>{fields['scope']}</scope>
  <skip_topics>{fields['skip_topics']}</skip_topics>
  <case_problem_with_solution>
{text}
  </case_problem_with_solution>
</input>"""
    
    return [{"type": "text", "text": user_xml}]


def build_user_message_pdf(input_path: Path, fields: dict) -> list:
    """PDF 입력 → document content block + 메타 XML"""
    pdf_bytes = input_path.read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    
    meta_xml = f"""<input>
  <subject>{fields['subject']}</subject>
  <source>{fields['source']}</source>
  <case_id>{fields['case_id']}</case_id>
  <difficulty>{fields['difficulty']}</difficulty>
  <scope>{fields['scope']}</scope>
  <skip_topics>{fields['skip_topics']}</skip_topics>
  <case_problem_with_solution>
    [PDF 첨부됨 — 본 메시지의 document content block 참조]
  </case_problem_with_solution>
</input>"""
    
    return [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        },
        {"type": "text", "text": meta_xml},
    ]


def main():
    parser = argparse.ArgumentParser(description="06b extract 사례집 카드화")
    parser.add_argument("input", help="입력 파일 (.pdf 또는 .md)")
    parser.add_argument("--subject", default="")
    parser.add_argument("--source", default=None)
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--difficulty", default="A", choices=["A", "B", "C"])
    parser.add_argument("--scope", default="")
    parser.add_argument("--skip-topics", default="")
    parser.add_argument("--output-name", default=None)
    args = parser.parse_args()
    
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"ERROR: 입력 파일 없음: {input_path}")
        sys.exit(1)
    
    logger = setup_logger("06b_extract")
    logger.info(f"=== 06b extract 시작 ===")
    logger.info(f"Input: {input_path.name}")
    
    fields = {
        "subject": args.subject,
        "source": args.source or input_path.stem,
        "case_id": args.case_id or input_path.stem,
        "difficulty": args.difficulty,
        "scope": args.scope,
        "skip_topics": args.skip_topics,
    }
    
    # 환경
    api_key = get_anthropic_key()
    client = Anthropic(api_key=api_key)
    
    # 프롬프트
    system_prompt = read_prompt("06b_claude_사례집문제_extract_v3.6.xml")
    
    # 입력 유형에 따라 content 분기
    if input_path.suffix.lower() == ".pdf":
        content = build_user_message_pdf(input_path, fields)
        logger.info(f"PDF 입력 모드 ({input_path.stat().st_size / 1024:.0f}KB)")
    else:
        content = build_user_message_text(input_path, fields)
        logger.info(f"텍스트 입력 모드")
    
    logger.info(f"Claude Opus 4.7 호출 중...")
    start = time.time()
    
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=32000,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    )
    
    elapsed = time.time() - start
    output_text = "".join(b.text for b in response.content if hasattr(b, "text"))
    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    
    logger.info(f"완료 ({elapsed:.1f}s, in={in_tok}, out={out_tok})")
    
    # 저장
    out_filename = args.output_name or f"{input_path.stem}_06b_TSV.txt"
    out_path = save_output(output_text, "06_cases", out_filename)
    logger.info(f"저장: {out_path.relative_to(PACKAGE_ROOT)}")
    
    # 검증
    import re
    tsv_blocks = re.findall(r"```tsv\n(.+?)```", output_text, re.DOTALL)
    검증필요_count = 0
    for i, tsv in enumerate(tsv_blocks, 1):
        result = verify_tsv(tsv)
        검증필요_count += tsv.count("검증필요::AI추출")
        logger.info(f"TSV 블록 {i}: 카드 {result['card_count']}장, 이슈 {len(result['issues'])}")
        for issue in result["issues"]:
            logger.warning(f"  - {issue}")
    
    # 06b 특수 검증
    total_cards = sum(verify_tsv(t)["card_count"] for t in tsv_blocks)
    if total_cards > 0 and 검증필요_count < total_cards:
        logger.warning(
            f"06b 카드 중 일부에 '검증필요::AI추출' 태그 누락 "
            f"({검증필요_count}/{total_cards})"
        )
    
    # 풀이 영역 식별 결과
    if "[불명: 풀이 영역 자동 식별 실패]" in output_text:
        logger.warning("풀이 영역 자동 식별 실패. 사용자 검증 필수. 06a 사용 권장.")
    elif "풀이 영역 식별: 성공" in output_text:
        logger.info("풀이 영역 식별: 성공")
    
    log_cost("claude-opus-4-7", in_tok, out_tok)
    cost = (in_tok / 1e6 * 15.0 + out_tok / 1e6 * 75.0)
    logger.info(f"예상 비용: ${cost:.2f}")
    logger.info(f"=== 완료 ===")
    logger.info(
        f"사후 검증 안내: Anki Import 후 'tag:검증필요::AI추출' 검색 → "
        f"사례집 원본과 대조 → 검증 완료 카드는 태그 제거."
    )


if __name__ == "__main__":
    main()
