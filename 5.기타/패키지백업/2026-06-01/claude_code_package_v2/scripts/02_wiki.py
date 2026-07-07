"""
02-wiki 위키화 파이프라인 (v3.6 Phase 2).
[운영 권장] 위키화는 안티그래비티(Gemini Flash)에서 처리 — 대용량 원문 저비용 압축.
[legacy 스크립트] 이 파일은 Anthropic SDK 경로 (품질 우선 시 대안). 01번 OCR 출력 또는 PDF 직접 → Obsidian 위키 마크다운.

파이프라인 위치:
  [PDF] → 01번 OCR → **02-wiki (이 스크립트)** → 02-card / 06a / 06b → Anki

사용법:
    python scripts/02_wiki.py <input.md|input.pdf> [옵션]

옵션:
    --source "송영곤 [2026] 논점민법강의 12판"
    --book-type 단권화|사례집|판례집|객관식문제집|기록형|혼합|미상
    --chunk-anchor "CHUNK: pages 1-100 | total 300 pages | source: 송영곤 논점민법강의"
    --scope "민법1·형법총론"
    --output-name "송영곤논점민강_chunk_001.md"

자동 동작:
    1. 입력이 PDF면 그대로 첨부, .md면 텍스트로 전달
    2. prompts/02-wiki_claude_위키화_v3.6.xml을 system prompt로
    3. 책 유형 자동 식별 + 속성 라벨 + Obsidian callout 변환 적용
    4. outputs/02_wiki/책이름_chunk_NNN.md 저장
    5. 비용·소요 시간·검증 결과 로깅
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
    save_output, PACKAGE_ROOT
)


def build_user_message_text(input_path: Path, fields: dict) -> list:
    """텍스트 입력 (01번 OCR 출력 등)"""
    text = input_path.read_text(encoding="utf-8")
    
    user_xml = f"""<input>
  <source>{fields['source']}</source>
  <book_type_hint>{fields['book_type_hint']}</book_type_hint>
  <chunk_anchor>{fields['chunk_anchor']}</chunk_anchor>
  <scope>{fields['scope']}</scope>
  <content_source>
{text}
  </content_source>
</input>"""
    
    return [{"type": "text", "text": user_xml}]


def build_user_message_pdf(input_path: Path, fields: dict) -> list:
    """PDF 직접 입력 (01번 건너뛰고 02-wiki만 사용)"""
    pdf_bytes = input_path.read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    
    meta_xml = f"""<input>
  <source>{fields['source']}</source>
  <book_type_hint>{fields['book_type_hint']}</book_type_hint>
  <chunk_anchor>{fields['chunk_anchor']}</chunk_anchor>
  <scope>{fields['scope']}</scope>
  <content_source>
    [PDF 첨부됨 — 본 메시지의 document content block 참조]
  </content_source>
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


def verify_wiki_output(text: str, logger) -> dict:
    """위키화 출력 자동 검증"""
    issues = []
    
    # frontmatter 확인
    if not text.startswith("---"):
        issues.append("YAML frontmatter 누락")
    
    # 책 유형 추정 메시지 확인
    if "책 유형 추정:" not in text:
        issues.append("책 유형 추정 메시지 누락")
    
    # 속성 라벨 부착 확인
    attr_count = text.count("<!-- 속성:")
    if attr_count < 3:
        issues.append(f"속성 라벨 부착 적음 ({attr_count}개) — 위키화 실패 가능성")
    
    # 마크다운 충돌 회피 확인
    # 박스 라벨이 callout으로 변환됐는지
    raw_box_count = (
        text.count("[논점정리]") + text.count("[논점의 정리]")
        + text.count("[관련판례]") + text.count("[해설]")
        + text.count("[모범답안]")
    )
    callout_count = (
        text.count("> [!summary]") + text.count("> [!example]")
        + text.count("> [!note]") + text.count("> [!analysis]")
        + text.count("> [!warning]") + text.count("> [!important]")
    )
    if raw_box_count > callout_count and raw_box_count > 0:
        issues.append(
            f"박스 라벨 callout 변환 미흡 (raw={raw_box_count}, callout={callout_count})"
        )
    
    # [불명] → {불명} 변환 확인
    if "[불명]" in text and text.count("[불명]") > 1:  # 1회는 매핑 규칙 본문일 수 있음
        issues.append(f"[불명] 토큰 잔존 ({text.count('[불명]')}개) — {{불명}}으로 변환되어야 함")
    
    # END_OF_CHUNK 확인
    if "END_OF_CHUNK:" not in text:
        issues.append("END_OF_CHUNK 메시지 누락")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "attr_count": attr_count,
        "callout_count": callout_count,
    }


def main():
    parser = argparse.ArgumentParser(description="02-wiki 위키화 (v3.6 Phase 1 신규)")
    parser.add_argument("input", help="입력 파일 (.md 또는 .pdf)")
    parser.add_argument("--source", default=None, help="책 출처 (예: 송영곤 논점민법강의 p.279)")
    parser.add_argument("--book-type", default="",
                        choices=["", "단권화", "사례집", "판례집", "객관식문제집", "기록형", "혼합", "미상"],
                        help="책 유형 hint (선택, AI가 자동 추정)")
    parser.add_argument("--chunk-anchor", default=None,
                        help="청크 anchor (예: 'CHUNK: pages 1-100 | total 300 pages | source: 송영곤 논점민법강의')")
    parser.add_argument("--scope", default="", help="현재 학습 범위")
    parser.add_argument("--output-name", default=None,
                        help="출력 파일명 (default: 입력 파일명_wiki.md)")
    args = parser.parse_args()
    
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"ERROR: 입력 파일 없음: {input_path}")
        sys.exit(1)
    
    logger = setup_logger("02_wiki")
    logger.info(f"=== 02-wiki 위키화 시작 ===")
    logger.info(f"Input: {input_path}")
    logger.info(f"Source: {args.source or input_path.stem}")
    logger.info(f"Book type hint: {args.book_type or '(자동 추정)'}")
    
    fields = {
        "source": args.source or input_path.stem,
        "book_type_hint": args.book_type,
        "chunk_anchor": args.chunk_anchor or f"CHUNK: source: {input_path.stem}",
        "scope": args.scope,
    }
    
    # 환경 확인
    try:
        api_key = get_anthropic_key()
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)
    
    client = Anthropic(api_key=api_key)
    
    # 프롬프트 로드
    try:
        system_prompt = read_prompt("02-wiki_claude_위키화_v3.6.xml")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    
    # 입력 유형 분기
    if input_path.suffix.lower() == ".pdf":
        content = build_user_message_pdf(input_path, fields)
        logger.info(f"PDF 입력 모드 ({input_path.stat().st_size / 1024:.0f}KB)")
    else:
        content = build_user_message_text(input_path, fields)
        logger.info(f"텍스트 입력 모드")
    
    logger.info(f"Claude Opus 4.8 호출 중 (위키화 대안 경로)...")
    start = time.time()
    
    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=32000,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as e:
        logger.error(f"API 호출 실패: {e}")
        sys.exit(1)
    
    elapsed = time.time() - start
    output_text = "".join(b.text for b in response.content if hasattr(b, "text"))
    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    
    logger.info(f"완료 ({elapsed:.1f}s, in={in_tok}, out={out_tok})")
    
    # 저장
    out_filename = args.output_name or f"{input_path.stem}_wiki.md"
    out_path = save_output(output_text, "02_wiki", out_filename)
    logger.info(f"저장: {out_path.relative_to(PACKAGE_ROOT)}")
    
    # 검증
    result = verify_wiki_output(output_text, logger)
    logger.info(f"속성 라벨: {result['attr_count']}개")
    logger.info(f"Obsidian callout: {result['callout_count']}개")
    if result["issues"]:
        for issue in result["issues"]:
            logger.warning(f"  - {issue}")
    
    # 책 유형 추정 결과 표시
    for line in output_text.split("\n")[:30]:
        if "책 유형 추정:" in line or "hint 일치 여부:" in line:
            logger.info(f"  {line.strip()}")
    
    log_cost("claude-opus-4-8", in_tok, out_tok)
    cost = (in_tok / 1e6 * 15.0 + out_tok / 1e6 * 75.0)
    logger.info(f"예상 비용: ${cost:.2f}")
    logger.info(f"=== 완료 ===")
    logger.info(
        f"다음 단계: 위키 출력을 02-card·06a·06b의 input으로 사용. "
        f"또는 outputs/02_wiki/{out_filename}을 Obsidian vault에 복사."
    )


if __name__ == "__main__":
    main()
