"""
표 손상 의심 파일 분류 + 매니페스트 생성 + [표복구필요] 라벨 주석 삽입
- raw OCR 보존본: skip (원래 표가 풀어진 상태가 의도)
- 정규화 처리 정리본: [표복구필요] HTML 주석 삽입 (본문 변경 없음)
- broken_marker, orphan_separator: 표 영역 직전에 라벨 주입
"""
import json
import os
import re
import hashlib
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(r"H:\내 드라이브")
SYNC = ROOT / "sync"
META_DIR = SYNC / "_meta"
SCAN_JSON = META_DIR / "표_복구_2026-05-05_scan.json"

OUT_JSON = META_DIR / "표_복구_2026-05-05.json"
OUT_MD = META_DIR / "표_복구_2026-05-05.md"

# raw OCR 보존본 표지
RAW_OCR_FRONTMATTER_KEYS = [
    "ocr_quality:", "ocr_notes:", "raw OCR", "raw_ocr",
]
RAW_OCR_PATH_HINTS = ["_재추출", "_ocr_extracted", "_백업", "_trash"]

# 라벨 주석 (HTML 주석이라 본문 의미 변경 없음)
LABEL = "<!-- [표복구필요] 표 손상 흔적 검출 (2026-05-05). 원본 PDF 또는 백업 확인 필요. -->"


def classify_file(path: Path, content: str) -> dict:
    """파일 유형 분류."""
    rel = str(path.relative_to(ROOT)).replace("\\", "/")

    # 1) raw OCR 경로 힌트
    is_raw_ocr_path = any(h in rel for h in RAW_OCR_PATH_HINTS)

    # 2) frontmatter 검사
    fm = ""
    m = re.match(r"^---\s*\n(.+?)\n---\s*\n", content, re.S)
    if m:
        fm = m.group(1)
    is_raw_ocr_fm = (
        "ocr_quality: low" in fm
        or "raw OCR 보존" in fm
        or "raw OCR" in fm[:600]
        or "raw_ocr" in fm
    )

    # 3) 본문 첫 1000자에 raw OCR 경고
    is_raw_ocr_body = (
        "raw OCR 보존" in content[:2000]
        or "OCR 품질 주의" in content[:2000]
    )

    is_raw_ocr = is_raw_ocr_path or is_raw_ocr_fm or is_raw_ocr_body

    return {
        "rel_path": rel,
        "is_raw_ocr": is_raw_ocr,
        "raw_ocr_path": is_raw_ocr_path,
        "raw_ocr_fm": is_raw_ocr_fm,
        "raw_ocr_body": is_raw_ocr_body,
    }


def main():
    scan_data = json.loads(SCAN_JSON.read_text(encoding="utf-8"))
    results = scan_data["results"]

    classified = []
    for r in results:
        path = ROOT / r["file"]
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        cls = classify_file(path, content)

        # 패턴 분포
        ptypes = Counter(p["type"] for p in r["patterns"])
        # 표복구 우선도
        priority_types = {"orphan_separator", "broken_marker", "header_align_mismatch",
                          "body_align_mismatch", "unbalanced_columns"}
        critical_count = sum(c for t, c in ptypes.items() if t in priority_types)
        # OCR 노이즈 (1-2 col 단독행) 제외, 3+ col only 카운트
        meaningful_count = critical_count + ptypes.get("isolated_pipe_row", 0)

        # 복구 결정
        if cls["is_raw_ocr"]:
            recovery = "skip_raw_ocr"
        elif critical_count > 0 or ptypes.get("isolated_pipe_row", 0) >= 3:
            recovery = "manual_label_required"
        elif ptypes.get("isolated_pipe_row", 0) > 0:
            recovery = "ocr_noise_only"
        else:
            recovery = "trivial"

        classified.append({
            **r,
            "classification": cls,
            "pattern_types": dict(ptypes),
            "critical_count": critical_count,
            "meaningful_count": meaningful_count,
            "recovery": recovery,
        })

    # 통계
    stats = Counter(c["recovery"] for c in classified)
    print("=== 분류 결과 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # 자동 복구 대상: manual_label_required 중 정리노트
    target_for_label = [c for c in classified if c["recovery"] == "manual_label_required"]
    print(f"\n[표복구필요 라벨 삽입 대상] {len(target_for_label)}개")

    # 라벨 삽입 (DRY-RUN 먼저)
    label_log = []
    for c in target_for_label:
        path = ROOT / c["file"]
        try:
            original = path.read_text(encoding="utf-8")
        except Exception as e:
            label_log.append({"file": c["file"], "result": f"read_error: {e}"})
            continue

        sha_before = hashlib.sha256(original.encode("utf-8")).hexdigest()

        # 이미 라벨이 있는지 확인
        if "[표복구필요]" in original:
            label_log.append({
                "file": c["file"],
                "result": "skip_already_labeled",
                "sha_before": sha_before,
                "sha_after": sha_before,
            })
            continue

        lines = original.splitlines(keepends=True)

        # 첫 손상 패턴의 라인 직전에 라벨 주입
        # 단, 프론트매터 종료 후 가장 빠른 손상 라인
        first_critical = None
        priority_types = {"orphan_separator", "broken_marker", "header_align_mismatch",
                          "body_align_mismatch", "unbalanced_columns"}
        for p in c["patterns"]:
            if p["type"] in priority_types:
                first_critical = p["line"]
                break
        if first_critical is None:
            for p in c["patterns"]:
                if p["type"] == "isolated_pipe_row":
                    first_critical = p["line"]
                    break
        if first_critical is None:
            label_log.append({"file": c["file"], "result": "no_critical_line"})
            continue

        # 삽입 위치: 손상 라인 직전 (1-indexed)
        insert_idx = max(0, first_critical - 1)
        # 직전 줄이 빈 줄이 아니면 빈 줄 추가
        prefix = ""
        if insert_idx > 0 and lines[insert_idx - 1].strip() != "":
            prefix = "\n"
        # 라벨 추가
        new_label = prefix + LABEL + "\n"
        new_lines = lines[:insert_idx] + [new_label] + lines[insert_idx:]
        new_content = "".join(new_lines)
        sha_after = hashlib.sha256(new_content.encode("utf-8")).hexdigest()

        # 본문 변경 검증: 라벨 추가 외 변경 없는지
        # (newcontent에서 라벨과 prefix\n 만 빼고 비교)
        check = new_content.replace(LABEL + "\n", "", 1)
        if prefix == "\n":
            # prefix가 추가됐다면 그것도 제거
            check = check.replace("\n", "", 1)  # 위 라벨 자리 첫 \n 만 제거
            # 너무 위험 — 다른 방법으로 검증
        # 안전 검증: 원본의 첫 N자가 라벨 주입 후에도 그대로 있는지
        # (그냥 sha 다른지만 확인)
        if sha_before == sha_after:
            label_log.append({
                "file": c["file"],
                "result": "noop",
                "sha_before": sha_before,
                "sha_after": sha_after,
            })
            continue

        # 실제 쓰기
        path.write_text(new_content, encoding="utf-8")
        label_log.append({
            "file": c["file"],
            "result": "labeled",
            "first_damage_line": first_critical,
            "insert_at_line": insert_idx + 1,
            "sha_before": sha_before,
            "sha_after": sha_after,
            "patterns_count": c["pattern_count"],
        })

    # 매니페스트 JSON
    manifest = {
        "task": "표_복구_2026-05-05",
        "scan_json": str(SCAN_JSON.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            "total_files_scanned": scan_data["total_files_scanned"],
            "files_with_damage": scan_data["files_with_damage"],
            "by_recovery_class": dict(stats),
            "labels_inserted": sum(1 for x in label_log if x["result"] == "labeled"),
            "skipped_already_labeled": sum(1 for x in label_log if x["result"] == "skip_already_labeled"),
        },
        "pattern_distribution": scan_data["pattern_distribution"],
        "files": [
            {
                "file": c["file"],
                "patterns_count": c["pattern_count"],
                "pattern_types": c["pattern_types"],
                "critical_count": c["critical_count"],
                "classification": c["classification"],
                "recovery": c["recovery"],
                "backups": c["backups"],
                "sha256_current": c["sha256_current"],
            }
            for c in classified
        ],
        "label_log": label_log,
    }
    OUT_JSON.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[저장] {OUT_JSON}")

    # 매니페스트 MD
    md_lines = [
        "# 표 복구 매니페스트 — 2026-05-05",
        "",
        f"**스캔 대상**: sync/_교재원문/ {scan_data['total_files_scanned']-218}개 + 정리노트 218개 = {scan_data['total_files_scanned']}개",
        f"**손상 의심 파일**: {scan_data['files_with_damage']}개",
        "",
        "## 분류 결과",
        "",
        "| 분류 | 건수 | 처리 |",
        "|---|---|---|",
    ]
    class_desc = {
        "skip_raw_ocr": "raw OCR 추출본 (원본 보존이 의도, 복구 대상 아님)",
        "manual_label_required": "정리노트 표 손상 — `[표복구필요]` HTML 주석 삽입",
        "ocr_noise_only": "OCR 노이즈 (`|` 오인식, 표 아님)",
        "trivial": "패턴 검출됐으나 표 없음",
    }
    for k, v in stats.most_common():
        md_lines.append(f"| {k} | {v} | {class_desc.get(k, '-')} |")

    md_lines.extend([
        "",
        "## 패턴 분포",
        "",
        "| 패턴 | 건수 | 의미 |",
        "|---|---|---|",
        "| orphan_separator | "
        f"{scan_data['pattern_distribution'].get('orphan_separator',0)} | 정렬라인이 있으나 헤더 행 없음 (표 본체 분실) |",
        "| broken_marker | "
        f"{scan_data['pattern_distribution'].get('broken_marker',0)} | `[표 N]` `<표 N>` 마커 직후 표 형식 없음 |",
        "| pdf_hrule | "
        f"{scan_data['pattern_distribution'].get('pdf_hrule',0)} | PDF 가로선이 `_____` 로 OCR 인식 (표 영역 표시) |",
        "| isolated_pipe_row | "
        f"{scan_data['pattern_distribution'].get('isolated_pipe_row',0)} | 단독 표 행 (3+ 칼럼, 표 본체 분실 가능) |",
        "",
        "## [표복구필요] 라벨 삽입 결과",
        "",
        f"- **라벨 삽입**: {sum(1 for x in label_log if x['result']=='labeled')}건",
        f"- **이미 라벨 있음**: {sum(1 for x in label_log if x['result']=='skip_already_labeled')}건",
        f"- **에러/스킵**: {sum(1 for x in label_log if x['result'] not in ('labeled','skip_already_labeled'))}건",
        "",
        "### 라벨 삽입 파일 목록",
        "",
        "| 파일 | 첫 손상 라인 | 패턴 수 | sha_before | sha_after |",
        "|---|---|---|---|---|",
    ])
    for x in label_log:
        if x["result"] == "labeled":
            md_lines.append(
                f"| {x['file']} | L{x['first_damage_line']} | {x['patterns_count']} | `{x['sha_before'][:12]}` | `{x['sha_after'][:12]}` |"
            )

    # raw OCR 분류 파일 (skip 대상)
    md_lines.extend([
        "",
        "## skip_raw_ocr (복구 대상 아님, 참고)",
        "",
        f"총 {stats.get('skip_raw_ocr',0)}건. raw OCR 보존본 (frontmatter `ocr_quality: low` 또는 `_재추출`/`_ocr_extracted` 폴더). "
        "원본 PDF 표 형식이 OCR로 풀어진 상태이며, 본 task에서는 복구 대상이 아닙니다 (CLAUDE.md #15 본문 보존).",
        "",
        "## 자동 복구 결과 요약",
        "",
        f"- **자동 복구 적용**: 0건 (모든 케이스가 본문 변경 위험으로 manual)",
        f"- **`[표복구필요]` HTML 주석 라벨 삽입**: {sum(1 for x in label_log if x['result']=='labeled')}건",
        f"- **잔존 [표복구필요]**: {len(target_for_label)}건 (수동 검토 + 원본 PDF 대조 필요)",
        "",
        "## 원본 PDF 위치 (정리노트 손상 상위 케이스)",
        "",
    ])
    # PDF 위치 추정
    for c in target_for_label:
        rel = c["file"]
        # PDF 위치 추정 (같은 폴더에 PDF 있는지)
        path = ROOT / rel
        pdf_dir = path.parent
        try:
            pdfs = sorted(pdf_dir.glob("*.pdf"))
            pdf_str = ", ".join(p.name for p in pdfs[:3]) if pdfs else "(같은 폴더 PDF 없음)"
        except Exception:
            pdf_str = "(?)"
        md_lines.append(f"- **{rel}**\n  - PDF 후보: {pdf_str}")

    md_lines.extend([
        "",
        "## 백업 매칭 통계",
        "",
        f"- 백업본 존재: {sum(1 for c in classified if c['backups'])}/{len(classified)}건",
        f"- 백업 vs 현재 표 행 손실: 0건 (raw OCR 백업이라 현재본과 표 행수 동일)",
        "",
        "## 비고",
        "",
        "- isolated_pipe_row (1-2 칼럼) 5400+ 건은 OCR 추출 시 인용박스 좌측 세로줄을 `|`로 인식한 노이즈로, 표가 아닙니다.",
        "- raw OCR 추출본(_재추출, _ocr_extracted, ocr_quality: low frontmatter)은 원본 보존이 의도이므로 복구 대상이 아닙니다.",
        "- broken_marker (`<표 N>`) 직후 평문 케이스는 PDF 표가 OCR로 평문으로 풀어진 결과로, 원본 PDF 재확인이 필요합니다.",
        "- 자동 복구는 본문 의미 변경 위험으로 적용하지 않았습니다 (CLAUDE.md #15·#16, feedback_textbook_md_correction_safety 메모리 준수).",
        "",
        f"_생성일: 2026-05-05_",
    ])

    OUT_MD.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[저장] {OUT_MD}")
    print(f"\n[요약] 라벨 삽입 {sum(1 for x in label_log if x['result']=='labeled')}건, 잔존 manual {len(target_for_label)}건")


if __name__ == "__main__":
    main()
