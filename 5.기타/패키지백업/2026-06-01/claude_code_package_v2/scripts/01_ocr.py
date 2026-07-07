"""
01번 OCR 파이프라인 (v3.6 Phase 2 — 2모델 역할분담).
[운영 권장] OCR은 안티그래비티(Gemini Flash) — 대용량 원문 PDF 저비용 처리.
[legacy 스크립트] 이 파일은 Anthropic SDK 경로 (Sonnet 4.6 default, Haiku 4.5 옵션).
PDF 청크 → 마킹/구조/조문 추출 → outputs/01_ocr/

v3.6 Phase 1 (2026-05): Gemini 3.1 Pro 사용
v3.6 Phase 1.1 (2026-05): Claude(Sonnet/Haiku)로 교체
v3.6 Phase 2 (2026-06): 안티그래비티(Gemini Flash)=OCR+위키화 / Opus 4.8=카드화 2모델 분담

사용법:
    python scripts/01_ocr.py <PDF경로> [--mode A|B] [--model sonnet|haiku|opus] [--source 책이름]

예:
    python scripts/01_ocr.py inputs/raw_pdf/형법총론.pdf --mode B --model sonnet --source "김성돈 형법총론"

자동 동작:
    1. pdf_split_100p.py로 100p 분할
    2. 각 청크를 Claude API로 OCR (document content block)
    3. outputs/01_ocr/책이름_chunk_NNN.md 저장
    4. 비용·소요 시간·검증 결과 로깅
"""

import argparse
import base64
import subprocess
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
    save_output, estimate_pages, PACKAGE_ROOT
)


# 모델 별칭 → Anthropic 모델 ID
MODEL_ALIASES = {
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001",
    "opus": "claude-opus-4-8",
}

# 모델별 max_tokens 권장값
MODEL_MAX_TOKENS = {
    "claude-sonnet-4-6": 32000,
    "claude-haiku-4-5-20251001": 16000,
    "claude-opus-4-8": 32000,
}


def split_pdf(pdf_path: Path, logger) -> list[Path]:
    """pdf_split_100p.py 호출 → 청크 PDF 경로 리스트 반환"""
    split_script = PACKAGE_ROOT / "scripts" / "pdf_split_100p.py"

    logger.info(f"PDF 분할 시작: {pdf_path.name}")
    result = subprocess.run(
        [sys.executable, str(split_script), str(pdf_path)],
        capture_output=True, text=True, cwd=PACKAGE_ROOT
    )

    if result.returncode != 0:
        logger.error(f"PDF 분할 실패: {result.stderr}")
        sys.exit(1)

    # 분할 결과 디렉토리 추정
    chunks_dir = pdf_path.parent / f"{pdf_path.stem}_chunks"
    if not chunks_dir.exists():
        chunks_dir = PACKAGE_ROOT / f"{pdf_path.stem}_chunks"

    chunk_files = sorted(chunks_dir.glob("*.pdf"))
    logger.info(f"분할 완료: {len(chunk_files)}개 청크")
    return chunk_files


def call_claude_ocr(
    client,
    pdf_path: Path,
    system_prompt: str,
    chunk_anchor: str,
    mode: str,
    model: str,
    logger,
) -> tuple[str, int, int]:
    """단일 청크 OCR 호출. (출력, input_tokens, output_tokens) 반환"""

    pdf_bytes = pdf_path.read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    user_message = f"{chunk_anchor}\n모드: {mode}\n[PDF 첨부됨 — document content block]"

    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        },
        {"type": "text", "text": user_message},
    ]

    max_tokens = MODEL_MAX_TOKENS.get(model, 16000)

    logger.info(f"  Claude API 호출 중 (model={model}, max_tokens={max_tokens})...")
    start = time.time()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as e:
        logger.error(f"  API 호출 실패: {e}")
        raise

    elapsed = time.time() - start

    output_text = "".join(b.text for b in response.content if hasattr(b, "text"))
    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens

    logger.info(f"  완료 ({elapsed:.1f}s, in={in_tok}, out={out_tok})")

    return output_text, in_tok, out_tok


def main():
    parser = argparse.ArgumentParser(description="01번 OCR 자동 파이프라인 (Claude 기반)")
    parser.add_argument("pdf", help="원본 PDF 경로")
    parser.add_argument("--mode", default="B", choices=["A", "B"],
                        help="A: 마킹+조문만, B: 전체 추출 (default B)")
    parser.add_argument("--model", default="sonnet", choices=list(MODEL_ALIASES.keys()),
                        help="모델: sonnet (default, 마킹 인식 정확) / haiku (저비용) / opus (최고)")
    parser.add_argument("--source", default=None, help="책 이름 (anchor에 표시)")
    parser.add_argument("--chunk-only", type=int, default=None,
                        help="특정 청크만 처리 (예: 1 = 첫 청크만, 디버깅용)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        print(f"ERROR: PDF 파일 없음: {pdf_path}")
        sys.exit(1)

    source_name = args.source or pdf_path.stem
    model_id = MODEL_ALIASES[args.model]

    logger = setup_logger("01_ocr")
    logger.info(f"=== 01번 OCR 시작 (Claude) ===")
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"Source: {source_name}")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Model: {args.model} ({model_id})")

    # 1. 환경 확인
    try:
        api_key = get_anthropic_key()
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # 2. 프롬프트 로드 (Claude 전용 프롬프트)
    try:
        system_prompt = read_prompt("01_claude_마킹_구조_조문_추출_v3.6.md")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # 3. PDF 분할
    chunk_files = split_pdf(pdf_path, logger)
    total_pages = estimate_pages(pdf_path)

    if args.chunk_only is not None:
        chunk_files = [chunk_files[args.chunk_only - 1]]
        logger.info(f"디버그 모드: {args.chunk_only}번 청크만 처리")

    # 4. 각 청크 OCR
    total_in_tokens = 0
    total_out_tokens = 0
    success_count = 0
    fail_count = 0

    for i, chunk_path in enumerate(chunk_files, 1):
        page_start = (i - 1) * 100 + 1
        page_end = min(i * 100, total_pages)

        chunk_anchor = (
            f"CHUNK: pages {page_start:03d}-{page_end:03d} "
            f"| total {total_pages} pages | source: {source_name} "
            f"| mode: full extraction"
        )

        logger.info(f"[{i}/{len(chunk_files)}] {chunk_path.name}")

        for retry in range(3):
            try:
                output_text, in_tok, out_tok = call_claude_ocr(
                    client, chunk_path, system_prompt,
                    chunk_anchor, args.mode, model_id, logger
                )

                # 저장
                out_filename = f"{source_name}_chunk_{i:03d}_p{page_start:03d}-{page_end:03d}.md"
                out_path = save_output(output_text, "01_ocr", out_filename)
                logger.info(f"  저장: {out_path.relative_to(PACKAGE_ROOT)}")

                # 비용 추적
                log_cost(model_id, in_tok, out_tok)
                total_in_tokens += in_tok
                total_out_tokens += out_tok
                success_count += 1
                break

            except Exception as e:
                logger.warning(f"  재시도 {retry + 1}/3: {e}")
                if retry == 2:
                    logger.error(f"  청크 {i} 처리 실패. 다음 청크 진행.")
                    fail_count += 1
                else:
                    time.sleep(5)

    # 5. 요약
    logger.info(f"=== 완료 ===")
    logger.info(f"성공: {success_count}/{len(chunk_files)}, 실패: {fail_count}")
    logger.info(f"총 토큰: in={total_in_tokens:,}, out={total_out_tokens:,}")

    # 비용 계산 (모델별 단가)
    pricing = {
        "claude-sonnet-4-6": (3.0, 15.0),
        "claude-haiku-4-5-20251001": (0.80, 4.0),
        "claude-opus-4-8": (15.0, 75.0),
    }
    in_price, out_price = pricing.get(model_id, (0, 0))
    cost = (total_in_tokens / 1e6 * in_price + total_out_tokens / 1e6 * out_price)
    logger.info(f"예상 비용: ${cost:.2f} (model={args.model})")
    logger.info(f"출력 폴더: outputs/01_ocr/")


if __name__ == "__main__":
    main()
