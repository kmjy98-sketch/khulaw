#!/usr/bin/env python3
"""
sonnet_review.py — corrections/{교재}.jsonl 의 저신뢰도/anchor 항목을 Sonnet 4.6 로 재검토.

대상 (marker-pdf 파이프라인 신스키마):
  - kind == "text"  AND  haiku 교정 완료 (correction.corrected 존재)
  - 저신뢰도(confidence < threshold) OR anchor 라인이 변경된 경우
  - 아직 sonnet_reviewed != True

사용법:
  python sonnet_review.py
  python sonnet_review.py --dry-run
  python sonnet_review.py --confidence-threshold 0.85
"""

import os
import sys
import json
import glob
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE            = os.environ.get("MEMORY_BASE", vp(".auto-memory"))
CORRECTIONS_DIR = os.path.join(BASE, "ocr_state", "corrections")
LEGACY_DIR      = os.path.join(BASE, "corrections")

try:
    import anthropic
except ImportError:
    print("anthropic 패키지 필요: pip install anthropic")
    sys.exit(1)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from legal_regex import is_anchor_line

client = anthropic.Anthropic()

_SYSTEM = """당신은 한국 법학 교재 OCR 교정 시니어 검토자입니다. Haiku가 교정한 결과를 재검토합니다.
규칙:
- 조문번호(제X조), 사건번호, 판례번호, 한자는 절대 수정하지 않는다 (anchor 보존).
- marker-pdf 추출본('new')과 기존 본문('old')을 함께 보고 판단한다.
- 교정이 적절하면 approved: true, 부적절하면 approved: false 로 원본 유지.
- 반드시 JSON으로만 응답: {"approved": bool, "final": "최종 텍스트", "reason": "..."}"""


def _resolve_dirs() -> list:
    dirs = []
    if os.path.isdir(CORRECTIONS_DIR):
        dirs.append(CORRECTIONS_DIR)
    if os.path.isdir(LEGACY_DIR) and LEGACY_DIR != CORRECTIONS_DIR:
        if any(p.endswith(".jsonl") for p in os.listdir(LEGACY_DIR)):
            dirs.append(LEGACY_DIR)
    return dirs


def _review_item(item: dict) -> dict:
    original   = item.get("old") or item.get("original", "")
    extracted  = item.get("new") or item.get("paddle", "")
    correction = item.get("correction", {}) or {}
    corrected  = correction.get("corrected", original)
    confidence = item.get("confidence")
    if confidence is None:
        confidence = correction.get("confidence", 0.0)

    if is_anchor_line(original):
        return {"approved": False, "final": original, "reason": "anchor — preserved original"}

    prompt = (
        f"기존 본문(old): '{original}'\n"
        f"marker-pdf 추출(new): '{extracted}'\n"
        f"Haiku 교정안: '{corrected}' (신뢰도: {confidence:.2f})\n"
        f"클래스: {item.get('class', '?')}  kind: {item.get('kind', 'text')}\n"
        "이 교정이 적절한지 검토하라."
    )
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(resp.content[0].text)
    except Exception as e:
        return {"approved": False, "final": original, "reason": f"API error: {e}"}


def _is_target(item: dict, threshold: float) -> bool:
    if item.get("sonnet_reviewed"):
        return False
    kind = item.get("kind") or item.get("type")
    if kind not in ("text", "text_conflict"):
        return False
    correction = item.get("correction") or {}
    if not correction.get("corrected"):
        return False  # haiku 교정이 안 된 항목은 sonnet 재검토 대상 아님
    conf = item.get("confidence")
    if conf is None:
        conf = correction.get("confidence", 1.0)
    is_low_conf = conf < threshold
    anchor_changed = correction.get("changed") and is_anchor_line(
        item.get("old") or item.get("original", ""))
    return bool(is_low_conf or anchor_changed or item.get("status") == "low_confidence")


def main():
    parser = argparse.ArgumentParser(description="Sonnet 4.6 OCR 교정 재검토")
    parser.add_argument("--confidence-threshold", type=float, default=0.85)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dirs = _resolve_dirs()
    if not dirs:
        print(f"corrections 디렉터리 없음: {CORRECTIONS_DIR}")
        sys.exit(1)

    jsonl_files = []
    for d in dirs:
        jsonl_files.extend(sorted(glob.glob(os.path.join(d, "*.jsonl"))))
    if not jsonl_files:
        print(f"corrections 파일 없음: {dirs}")
        sys.exit(1)

    print(f"교재 파일: {len(jsonl_files)}개  (dirs: {dirs})")

    total_targets  = 0
    total_approved = 0

    for jf in jsonl_files:
        book_id = Path(jf).stem
        with open(jf, "r", encoding="utf-8") as f:
            items = [json.loads(l) for l in f if l.strip()]

        targets = [(i, it) for i, it in enumerate(items)
                   if _is_target(it, args.confidence_threshold)]

        if not targets:
            continue

        print(f"  {book_id}: {len(targets)}건 재검토")
        total_targets += len(targets)

        if args.dry_run:
            for i, item in targets[:3]:
                print(f"    [{i}] conf={item.get('confidence','?')} | "
                      f"{(item.get('old') or item.get('original','') or '')[:50]}")
            continue

        approved_n = 0
        for idx, (i, item) in enumerate(targets):
            review = _review_item(item)
            items[i]["review"]          = review
            items[i]["sonnet_reviewed"] = True
            items[i]["status"]          = "reviewed"
            if review.get("approved"):
                approved_n     += 1
                total_approved += 1
            if (idx + 1) % 20 == 0:
                print(f"    {idx+1}/{len(targets)} 검토 완료...")

        with open(jf, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        print(f"    완료: 승인 {approved_n} / 거부 {len(targets)-approved_n}")

    if not args.dry_run:
        print(f"\n전체: {total_targets}건 재검토 / 승인: {total_approved}")


if __name__ == "__main__":
    main()
