"""Sonnet으로 청크 OCR 검토 (파일럿: 실시간 API, 전면: Batches API).

사용:
  python review_chunk_sonnet.py --pilot          # pilot_chunks.json 실시간 처리
  python review_chunk_sonnet.py --all            # 전면 (Batches API, 미구현 — 전면 승인 후)
  python review_chunk_sonnet.py --chunk path     # 단일 청크 테스트
  python review_chunk_sonnet.py --pilot --skip-api  # API 없이 규칙 기반만 적용

출력: .agent/data/ocr_chunks_reviewed/{동일 상대경로}
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

SKIP_API = "--skip-api" in sys.argv

if not SKIP_API:
    try:
        import anthropic
    except ImportError:
        print("anthropic 패키지 필요: pip install anthropic")
        sys.exit(1)

WORKSPACE_ROOT = Path(VAULT_ROOT)
CHUNKS_ROOT = WORKSPACE_ROOT / ".agent" / "data" / "ocr_chunks"
REVIEWED_ROOT = WORKSPACE_ROOT / ".agent" / "data" / "ocr_chunks_reviewed"
PILOT_CHUNKS_PATH = WORKSPACE_ROOT / ".agent" / "state" / "pilot_chunks.json"

MODEL = "claude-sonnet-4-6"

# 시스템 프롬프트 (캐싱 대상 — 변경 금지)
SYSTEM_PROMPT = """\
당신은 한국 법학 교재의 OCR 오인식 교정 전문가입니다.

## 역할
법학 교재 PDF를 OCR로 추출한 마크다운 청크에서 오인식·오류만 수정합니다.

## 허용 수정
1. OCR 글자 오식 수정 (예: 뻄뽀→원래 단어, 시1:%→채권법시, 뽀좇→해당 단어)
2. 붙어버린 띄어쓰기 복원 (예: "이된경우" → "이 된 경우")
3. 결합된 줄 분리 (두 문장이 이어붙은 경우 줄바꿈 복원)
4. 한자 OCR 오인식 수정 (예: 芮→병, Z→을, 戊→무 — 맥락상 당사자명인 경우)

## 절대 금지
- 원문 요약, 주해, 해설 추가
- 판례번호(대판 YYYY.M.D., 사건번호), 조문(**제N조**) 원문 변경
- <!-- p.NNN --> 페이지 마커 삭제·변경
- <!-- chunk_meta: ... --> 메타 주석 삭제·변경
- frontmatter(--- ... ---) 내용 변경
- 문장 재작성 또는 의미 변경
- 불확실한 추측으로 내용 채우기

## 출력 형식
수정된 마크다운 전문만 출력합니다. 설명·주석·markdown 코드펜스 불필요.
수정 사항이 없으면 입력과 동일한 텍스트를 그대로 출력합니다.
"""

USER_TEMPLATE = """\
아래 법학 교재 OCR 청크의 오인식·오류만 수정해 주세요.

<chunk>
{chunk_content}
</chunk>
"""


def review_chunk(client: anthropic.Anthropic, chunk_text: str) -> str:
    """단일 청크를 Sonnet으로 검토. 수정된 텍스트 반환."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(chunk_content=chunk_text),
            }
        ],
    )
    return response.content[0].text


def process_pilot(client=None) -> None:
    if not PILOT_CHUNKS_PATH.exists():
        print(f"파일럿 청크 인덱스 없음: {PILOT_CHUNKS_PATH}")
        sys.exit(1)

    records = json.loads(PILOT_CHUNKS_PATH.read_text(encoding="utf-8"))
    mode = "규칙 기반(skip-api)" if SKIP_API else "Sonnet API"
    print(f"파일럿 청크 {len(records)}개 처리 시작 [{mode}]")

    results = []
    for i, rec in enumerate(records):
        chunk_path = WORKSPACE_ROOT / rec["chunk_path"]
        if not chunk_path.exists():
            print(f"  [{i+1}/{len(records)}] 건너뜀 (없음): {chunk_path.name}")
            continue

        chunk_text = chunk_path.read_text(encoding="utf-8", errors="replace")

        out_rel = Path(rec["chunk_path"]).relative_to(".agent/data/ocr_chunks")
        out_path = REVIEWED_ROOT / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  [{i+1}/{len(records)}] {chunk_path.name} ...", end=" ", flush=True)
        t0 = time.time()
        try:
            if SKIP_API:
                # API 없이: 원본 청크를 그대로 복사 (규칙 기반 정리는 원본에 이미 적용됨)
                reviewed = chunk_text
            else:
                reviewed = review_chunk(client, chunk_text)
            elapsed = time.time() - t0
            out_path.write_text(reviewed, encoding="utf-8")
            changed = reviewed.strip() != chunk_text.strip()
            print(f"{'수정됨' if changed else '복사됨' if SKIP_API else '변경없음'} ({elapsed:.1f}s)")
            results.append({
                "chunk": rec["chunk_path"],
                "source": rec["source_path"],
                "reviewed_path": str(out_path.relative_to(WORKSPACE_ROOT)),
                "changed": changed,
                "elapsed": round(elapsed, 1),
                "mode": "skip-api" if SKIP_API else "sonnet",
            })
        except Exception as e:
            print(f"오류: {e}")
            results.append({
                "chunk": rec["chunk_path"],
                "source": rec["source_path"],
                "error": str(e),
                "changed": False,
            })
        if not SKIP_API:
            time.sleep(0.3)

    results_path = WORKSPACE_ROOT / ".agent" / "state" / "pilot_review_results.json"
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    changed_count = sum(1 for r in results if r.get("changed"))
    print(f"\n완료: {len(results)}개 처리, {changed_count}개 수정됨")
    print(f"결과 → {results_path}")


def process_single(client: anthropic.Anthropic, chunk_file: Path) -> None:
    chunk_text = chunk_file.read_text(encoding="utf-8", errors="replace")
    print(f"청크 검토: {chunk_file.name}")
    reviewed = review_chunk(client, chunk_text)

    out_rel = chunk_file.relative_to(CHUNKS_ROOT)
    out_path = REVIEWED_ROOT / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(reviewed, encoding="utf-8")

    # diff 출력
    orig_lines = chunk_text.splitlines()
    rev_lines = reviewed.splitlines()
    diffs = [(i+1, o, r) for i, (o, r) in enumerate(zip(orig_lines, rev_lines)) if o != r]
    print(f"\n수정 라인 {len(diffs)}개:")
    for lineno, orig, rev in diffs[:20]:
        print(f"  L{lineno}: {orig[:80]}")
        print(f"       → {rev[:80]}")
    if len(diffs) > 20:
        print(f"  ... (총 {len(diffs)}개)")
    print(f"\n→ {out_path}")


def main() -> None:
    if SKIP_API:
        client = None
    else:
        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수에서 자동 로드

    if "--chunk" in sys.argv:
        idx = sys.argv.index("--chunk")
        process_single(client, Path(sys.argv[idx + 1]))
    elif "--pilot" in sys.argv:
        process_pilot(client)
    elif "--all" in sys.argv:
        print("전면 실행은 파일럿 승인 후 구현 예정입니다.")
        sys.exit(1)
    else:
        print("옵션 필요: --pilot | --all | --chunk <path>")
        sys.exit(1)


if __name__ == "__main__":
    main()
