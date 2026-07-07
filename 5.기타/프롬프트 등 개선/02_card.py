"""
02-card 단권화 카드화 파이프라인 (v3.6).
Claude Opus 4.7 API로 위키 마크다운 (또는 압축본) → Anki TSV.

파이프라인 위치:
  [PDF] → 01번 OCR → 02-wiki → **02-card (이 스크립트)** → Anki

사용법:
    python scripts/02_card.py <input.md> [옵션]

옵션:
    --subject 민법|형법|헌법|...  (선택, 위키 frontmatter에서 추론 가능)
    --mode distill_as_is|auto_summarize  (default: distill_as_is)
    --note-type auto|rule|case_law|mcq  (default: auto — 위키 속성 라벨로 자동 분기)
    --difficulty A|B|C  (default: A)
    --generate-precursor-cards  (true 시 선행 단서 카드 추가 생성)
    --scope "민법1·형법총론"  (선택)
    --skip-topics "가족법,국제사법"  (선택)

예:
    python scripts/02_card.py outputs/02_wiki/송영곤_chunk_001_wiki.md \\
        --subject 민법 --note-type auto --difficulty A
"""

import argparse
import re
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


def call_claude_card(
    client,
    system_prompt: str,
    input_content: str,
    subject: str,
    mode: str,
    note_type: str,
    difficulty: str,
    generate_precursor_cards: bool,
    scope: str,
    skip_topics: str,
    logger,
) -> tuple[str, int, int]:
    """Claude Opus 4.7 호출. 출력 + 토큰 반환"""
    
    user_message = f"""<input>
  <subject>{subject}</subject>
  <mode>{mode}</mode>
  <note_type>{note_type}</note_type>
  <difficulty>{difficulty}</difficulty>
  <generate_precursor_cards>{str(generate_precursor_cards).lower()}</generate_precursor_cards>
  <scope>{scope}</scope>
  <skip_topics>{skip_topics}</skip_topics>
  <content>
{input_content}
  </content>
</input>"""
    
    logger.info(f"  Claude Opus 4.7 호출 중...")
    start = time.time()
    
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=32000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    
    elapsed = time.time() - start
    output_text = "".join(b.text for b in response.content if hasattr(b, "text"))
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    
    logger.info(f"  완료 ({elapsed:.1f}s, in={input_tokens}, out={output_tokens})")
    
    return output_text, input_tokens, output_tokens


def detect_wiki_input(content: str) -> bool:
    """입력이 02-wiki 출력인지 감지 (frontmatter + 속성 주석 존재)"""
    return content.startswith("---") and "<!-- 속성:" in content


def main():
    parser = argparse.ArgumentParser(description="02-card 단권화 카드화 (v3.6)")
    parser.add_argument("input", help="입력 파일 (02-wiki 출력 또는 압축본)")
    parser.add_argument("--subject", default="", help="과목 (위키 frontmatter에서 추론 가능)")
    parser.add_argument("--mode", default="distill_as_is",
                        choices=["distill_as_is", "auto_summarize"])
    parser.add_argument("--note-type", default="auto",
                        choices=["auto", "rule", "case_law", "mcq"],
                        help="auto: 위키 속성 라벨로 자동 분기 (default)")
    parser.add_argument("--difficulty", default="A", choices=["A", "B", "C"])
    parser.add_argument("--generate-precursor-cards", action="store_true",
                        help="선행 단서 카드 추가 생성 (소크라티즈 대체)")
    parser.add_argument("--scope", default="")
    parser.add_argument("--skip-topics", default="")
    parser.add_argument("--output-name", default=None)
    args = parser.parse_args()
    
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"ERROR: 입력 파일 없음: {input_path}")
        sys.exit(1)
    
    logger = setup_logger("02_card")
    logger.info(f"=== 02-card 단권화 카드화 시작 ===")
    logger.info(f"Input: {input_path}")
    logger.info(f"Note type: {args.note_type}")
    if args.generate_precursor_cards:
        logger.info(f"선행 단서 카드: ON (소크라티즈 대체)")
    
    # 환경 확인
    try:
        api_key = get_anthropic_key()
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)
    
    client = Anthropic(api_key=api_key)
    
    # 프롬프트 로드 (v3.6)
    system_prompt = read_prompt("02-card_claude_Anki카드화_v3.6.xml")
    
    # 입력 읽기
    input_content = input_path.read_text(encoding="utf-8")
    logger.info(f"입력 길이: {len(input_content)}자")
    
    # 위키 입력 감지
    if detect_wiki_input(input_content):
        logger.info("위키 입력 감지 → 속성 자동 분기 모드")
    else:
        logger.info("legacy 압축본 입력 → note_type 필드 사용")
        if args.note_type == "auto":
            logger.warning(
                "  note_type=auto이지만 위키 속성 라벨이 없음. "
                "AI가 content 분석 후 자동 추정함."
            )
    
    # 호출
    try:
        output_text, in_tok, out_tok = call_claude_card(
            client, system_prompt, input_content,
            args.subject, args.mode, args.note_type,
            args.difficulty, args.generate_precursor_cards,
            args.scope, args.skip_topics, logger
        )
    except Exception as e:
        logger.error(f"API 호출 실패: {e}")
        sys.exit(1)
    
    # 저장
    out_filename = args.output_name or f"{input_path.stem}_TSV.txt"
    out_path = save_output(output_text, "02_cards", out_filename)
    logger.info(f"저장: {out_path.relative_to(PACKAGE_ROOT)}")
    
    # 검증
    tsv_blocks = re.findall(r"```tsv\n(.+?)```", output_text, re.DOTALL)
    total_cards = 0
    if tsv_blocks:
        for i, tsv in enumerate(tsv_blocks, 1):
            result = verify_tsv(tsv)
            total_cards += result["card_count"]
            logger.info(f"TSV 블록 {i} 검증: 카드 {result['card_count']}장, 이슈 {len(result['issues'])}")
            for issue in result["issues"]:
                logger.warning(f"  - {issue}")
    else:
        logger.warning("TSV 코드블록 미발견. 출력 형식 확인 필요.")
    
    # 속성 자동 분기 결과 표시
    if "## 자동 분기 결과" in output_text:
        분기_lines = []
        in_section = False
        for line in output_text.split("\n"):
            if line.startswith("## 자동 분기 결과"):
                in_section = True
                continue
            if in_section:
                if line.startswith("## "):
                    break
                if line.strip().startswith("-"):
                    분기_lines.append(line.strip())
        if 분기_lines:
            logger.info("속성 자동 분기:")
            for line in 분기_lines:
                logger.info(f"  {line}")
    
    # 사례형 발견 안내
    if "06a 또는 06b 사용 권장" in output_text:
        logger.warning("사례형 문제 발견 → 06a 또는 06b로 별도 처리 권장")
    
    # 비용
    log_cost("claude-opus-4-7", in_tok, out_tok)
    cost = (in_tok / 1e6 * 15.0 + out_tok / 1e6 * 75.0)
    logger.info(f"예상 비용: ${cost:.2f}")
    logger.info(f"총 카드: {total_cards}장")
    logger.info(f"=== 완료 ===")


if __name__ == "__main__":
    main()
