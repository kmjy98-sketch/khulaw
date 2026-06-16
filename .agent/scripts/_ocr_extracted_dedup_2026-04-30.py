"""
_ocr_extracted_dedup_2026-04-30.py

sync/_ocr_extracted/ 전체 파일을 정본 폴더(sync/_교재원문/)와 중복 확인 후 통합.

분류:
  A. 완전 중복 (정본에 동일 fingerprint 존재) → _trash/2026-04-30/_ocr_extracted/
  B. 부분 일치 (정본이 raw OCR을 포함·확장한 버전) → 정본 폴더/_재추출/
  C. unique (정본 부재) → 정본 폴더(또는 신규 폴더) + 정규화

사용:
  python _ocr_extracted_dedup_2026-04-30.py --dry-run    # 분류 plan만 출력
  python _ocr_extracted_dedup_2026-04-30.py --apply       # 실제 이동
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# UTF-8 출력 강제
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(r"H:\내 드라이브\sync")
RAW_ROOT = ROOT / "_ocr_extracted"
CANON_ROOT = ROOT / "_교재원문"
TRASH_ROOT = Path(r"H:\내 드라이브\_trash\2026-04-30\_ocr_extracted")
META_ROOT = ROOT / "_meta"
TODAY = "2026-04-30"

# raw 폴더명 → 후보 정본 폴더 (수동 매핑)
# 키는 raw 폴더 이름 prefix, 값은 정본 폴더 상대경로(_교재원문 기준)
RAW_TO_CANON = {
    "1민사__20전경운_민법3":                       "민법/전경운_민법3",
    "1민사__30송영곤_기본민법__강의자료__사례":    "민법/송영곤_논점민법_보충",
    "1민사__30송영곤_기본민법__강의자료__선택형__민법_송영곤_DT": "민법/송영곤_논점민법_보충",
    "1민사__30송영곤_기본민법__강의자료__선택형__민법_송영곤_기본민법강의_DT": "민법/송영곤_논점민법_보충",
    # 송영곤 사례연습 가족/담보/물권/민총: 신규 정본 폴더 (기존 미등록)
    "1민사__31송영곤_사례__교재__송영곤_사례연습_가족":  "민법/송영곤_사례_가족",
    "1민사__31송영곤_사례__교재__송영곤_사례연습_담보":  "민법/송영곤_사례_담보",
    "1민사__31송영곤_사례__교재__송영곤_사례연습_물권":  "민법/송영곤_사례_물권",
    "1민사__31송영곤_사례__교재__송영곤_사례연습_민총":  "민법/송영곤_사례_민총",
    "2형사__30홍형철_기본형법":                    "형법/홍형철_기본형법",
    "2형사__40김성돈_형법총론":                    "형법/김성돈_형법총론",
    "2형사__96기타__2026_레인보우_형법_OX":        "형법/김기용_레인보우OX",
    "3공법__91보관__강성민_헌법ox":                "헌법/강성민_헌법OX",
    "4선택법__10법조윤리":                         "선택법/법조윤리_한권탁_기출",
}


def strip_yaml(text: str) -> str:
    """YAML frontmatter 제거"""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:]
    return text


def extract_yaml(text: str) -> dict:
    """YAML frontmatter 추출 (간이 파서, matched_existing_mds 등 단순 키만)"""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    yaml_block = text[4:end]
    out = {}
    for line in yaml_block.split("\n"):
        m = re.match(r'^(\w+):\s*(.*)$', line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            # 따옴표 제거
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            out[key] = val
    return out


def get_matched_existing(text: str) -> list:
    """frontmatter에서 matched_existing_mds 배열 추출"""
    m = re.search(r'matched_existing_mds:\s*\[(.*?)\]', text, re.DOTALL)
    if not m:
        return []
    inner = m.group(1)
    files = re.findall(r'"([^"]+)"', inner)
    return files


def fingerprint(body: str) -> str:
    """본문 정규화 후 모든 한글/영숫자 추출 → 단일 문자열"""
    # 마크다운/메타 노이즈 제거
    body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL)  # HTML 주석
    body = re.sub(r'^---+$', '', body, flags=re.MULTILINE)   # 수평선
    body = re.sub(r'^#+\s.*$', '', body, flags=re.MULTILINE) # 헤더 라인
    body = re.sub(r'^\s*[-*]\s+', '', body, flags=re.MULTILINE)  # 리스트 마커
    # 한글, 영숫자만 추출 (공백·구두점 제거)
    chars = re.findall(r'[가-힣A-Za-z0-9]+', body)
    return "".join(chars)


def shingles(s: str, k: int = 30) -> set:
    """k-shingle 집합"""
    if len(s) < k:
        return {s}
    return {s[i:i+k] for i in range(len(s) - k + 1)}


def list_md(folder: Path):
    """폴더 하위 .md 파일 (재귀 O, _백업/_중복/_reflow 제외, _재추출/은 포함)"""
    out = []
    if not folder.exists():
        return out
    EXCLUDE_DIRS = {"_백업", "_trash", "_reflow"}
    EXCLUDE_PREFIX = ("_중복", "_reflow_", "_trash")
    for p in folder.rglob("*.md"):
        # 부모 디렉토리 중 제외 폴더가 있으면 skip
        parts = p.relative_to(folder).parts
        if any(part in EXCLUDE_DIRS or any(part.startswith(pre) for pre in EXCLUDE_PREFIX) for part in parts[:-1]):
            continue
        # 파일명이 _로 시작하는 시스템 파일 (예: _교재목차.md) 제외
        if p.name.startswith("_"):
            continue
        out.append(p)
    return out


def candidate_canon_folder(raw_folder_name: str) -> Path | None:
    """raw 폴더명에서 후보 정본 폴더 찾기 (가장 긴 매칭 prefix)"""
    best = None
    best_len = 0
    for prefix, canon_rel in RAW_TO_CANON.items():
        if raw_folder_name.startswith(prefix) and len(prefix) > best_len:
            best = CANON_ROOT / canon_rel
            best_len = len(prefix)
    return best


def source_pdf_stem(raw_text: str, raw_path: Path) -> str:
    """source_pdf yaml 또는 raw 폴더명에서 책명 prefix 추출"""
    yml = extract_yaml(raw_text)
    src = yml.get("source_pdf", "")
    if src:
        # 1.민사/20.전경운_민법3/교재/민법의_기초이론_3_전경운_교재.pdf → 민법의_기초이론_3_전경운_교재
        stem = Path(src).stem
        return stem
    # 폴백: 폴더명 마지막 부분 (__ 분리)
    parts = raw_path.parent.name.split("__")
    return parts[-1] if parts else raw_path.parent.name


def classify(raw_path: Path, canon_folder: Path | None) -> dict:
    """raw 파일 한 개를 A/B/C로 분류"""
    raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
    raw_body = strip_yaml(raw_text)
    raw_fp = fingerprint(raw_body)
    raw_sh = shingles(raw_fp)
    raw_hash = hashlib.sha256(raw_fp.encode()).hexdigest()

    matched_in_yaml = get_matched_existing(raw_text)
    pdf_stem = source_pdf_stem(raw_text, raw_path)

    result = {
        "raw_path": str(raw_path),
        "raw_size": raw_path.stat().st_size,
        "raw_fp_len": len(raw_fp),
        "raw_hash": raw_hash,
        "source_pdf_stem": pdf_stem,
        "matched_existing_mds": matched_in_yaml,
        "candidate_canon_folder": str(canon_folder) if canon_folder else None,
        "classification": "C",  # 기본값
        "best_match": None,
        "best_match_ratio": 0.0,
        "filename_prefix_match": False,
        "reason": "",
    }

    if not raw_fp:
        result["classification"] = "C"
        result["reason"] = "raw 본문 fingerprint 비어있음 (frontmatter only?)"
        return result

    if canon_folder is None or not canon_folder.exists():
        result["reason"] = f"후보 정본 폴더 없음: {canon_folder}"
        return result

    # 모든 정본 파일 fingerprint 합쳐서 비교 (raw 50p chunk가 정본 여러 개로 split 됨)
    canon_files = list_md(canon_folder)
    if not canon_files:
        result["reason"] = "정본 폴더에 .md 파일 없음"
        return result

    # 후보 매칭 hint 우선 처리
    hint_files = []
    for hint in matched_in_yaml:
        hp = Path(r"H:\내 드라이브") / hint
        if hp.exists():
            hint_files.append(hp)

    # 정본 폴더 전체 + hint 합집합
    all_canon = list({str(p): p for p in canon_files + hint_files}.values())

    # 각 정본 파일과 raw 비교
    best_individual_ratio = 0.0
    best_individual_path = None
    individual_match_hashes = []
    for cp in all_canon:
        ctxt = cp.read_text(encoding="utf-8", errors="replace")
        cbody = strip_yaml(ctxt)
        cfp = fingerprint(cbody)
        if not cfp:
            continue
        chash = hashlib.sha256(cfp.encode()).hexdigest()
        if chash == raw_hash:
            individual_match_hashes.append(str(cp))
        csh = shingles(cfp)
        if not raw_sh:
            continue
        ratio = len(raw_sh & csh) / len(raw_sh)
        if ratio > best_individual_ratio:
            best_individual_ratio = ratio
            best_individual_path = str(cp)

    # 통합 비교: 모든 정본 fingerprint 합집합으로 raw 포함 여부 측정
    union_sh = set()
    for cp in all_canon:
        ctxt = cp.read_text(encoding="utf-8", errors="replace")
        cbody = strip_yaml(ctxt)
        cfp = fingerprint(cbody)
        union_sh |= shingles(cfp)

    union_ratio = len(raw_sh & union_sh) / len(raw_sh) if raw_sh else 0.0

    result["best_match"] = best_individual_path
    result["best_match_ratio"] = round(best_individual_ratio, 4)
    result["union_ratio"] = round(union_ratio, 4)
    result["individual_exact_hashes"] = individual_match_hashes

    # 파일명 prefix 매칭: 정본 폴더 내 .md 중 raw의 source_pdf_stem으로 시작하는 파일이 있는지
    pdf_stem_prefix = pdf_stem
    prefix_matches = [str(cp) for cp in all_canon if cp.name.startswith(pdf_stem_prefix)]
    result["filename_prefix_match"] = bool(prefix_matches)
    result["filename_prefix_matches"] = prefix_matches[:5]

    # 분류 규칙
    if individual_match_hashes:
        result["classification"] = "A"
        result["reason"] = f"정본에 동일 fingerprint 존재: {individual_match_hashes[0]}"
    elif union_ratio >= 0.95:
        result["classification"] = "B"
        result["reason"] = f"정본 합집합이 raw의 {union_ratio:.1%} 포함 (정본 split/확장)"
    elif best_individual_ratio >= 0.95:
        result["classification"] = "B"
        result["reason"] = f"정본 1개({best_individual_path})가 raw의 {best_individual_ratio:.1%} 포함"
    elif prefix_matches and union_ratio >= 0.4:
        result["classification"] = "B"
        result["reason"] = f"파일명 prefix({pdf_stem_prefix}) 정본 존재 + union {union_ratio:.1%} (정본이 raw normalize 버전)"
    elif prefix_matches:
        result["classification"] = "B-partial"
        result["reason"] = f"파일명 prefix({pdf_stem_prefix}) 정본 존재하나 본문 일치 낮음 (union {union_ratio:.1%}) - 검토 필요"
    elif union_ratio >= 0.5:
        result["classification"] = "B-partial"
        result["reason"] = f"정본 부분 포함 ({union_ratio:.1%}) - 검토 필요"
    else:
        result["classification"] = "C"
        result["reason"] = f"정본 일치 낮음 (best={best_individual_ratio:.1%}, union={union_ratio:.1%}, no filename prefix match)"

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제 이동 실행")
    ap.add_argument("--out", default=str(META_ROOT / f"_ocr_extracted_통합_매니페스트_{TODAY}.json"))
    args = ap.parse_args()

    raw_files = sorted(RAW_ROOT.rglob("*.md"))
    print(f"[INFO] raw .md 파일: {len(raw_files)}개")

    plan = []
    for rp in raw_files:
        raw_folder_name = rp.parent.name
        canon = candidate_canon_folder(raw_folder_name)
        rec = classify(rp, canon)
        plan.append(rec)
        print(f"  [{rec['classification']:>9}] {rp.name}  → {rec['reason']}")

    # 분류 통계
    counts = {}
    for r in plan:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    print(f"\n[INFO] 분류 통계: {counts}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({
            "date": TODAY,
            "total": len(plan),
            "counts": counts,
            "plan": plan,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[INFO] 매니페스트(plan) 저장: {out}")

    if not args.apply:
        print("\n[DRY-RUN] --apply 플래그 없이 실행 -- 파일 이동 안 함")
        return

    # === apply 단계 ===
    print("\n[APPLY] 파일 이동 시작")
    moves = []
    for rec in plan:
        rp = Path(rec["raw_path"])
        cls = rec["classification"]
        canon_folder = Path(rec["candidate_canon_folder"]) if rec["candidate_canon_folder"] else None
        pdf_stem = rec.get("source_pdf_stem", rp.stem)

        # raw 상대경로 (RAW_ROOT 기준)
        rel = rp.relative_to(RAW_ROOT)

        # 페이지 suffix 추출 (예: _p0001-0050)
        page_match = re.search(r'(_p\d+-\d+)\.md$', rp.name)
        page_suf = page_match.group(1) if page_match else ""
        cleaned_name = f"{pdf_stem}{page_suf}.md"

        # 본문 + 기존 yaml 추출
        original_text = rp.read_text(encoding="utf-8", errors="replace")
        body = strip_yaml(original_text)
        original_yaml = extract_yaml(original_text)
        original_match_arr = get_matched_existing(original_text)

        if cls == "A":
            # _trash로 이동 (수정 X)
            dst = TRASH_ROOT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                ts = datetime.now().strftime("%H%M%S")
                dst = dst.with_name(f"{dst.stem}_{ts}{dst.suffix}")
            shutil.move(str(rp), str(dst))
            moves.append({
                "src": str(rp), "dst": str(dst), "classification": cls,
                "raw_hash": rec["raw_hash"], "matched_canon": rec.get("best_match"),
            })
            print(f"  [A] {rp.name} -> _trash/")
            continue

        # B / B-partial / C: 새 frontmatter 작성 후 이동
        if canon_folder is None:
            # 폴백: _trash/C_unknown
            dst_dir = TRASH_ROOT / "C_unknown" / rel.parent
            dst = dst_dir / cleaned_name
            status_tag = "C_no_canon_folder"
        elif cls in ("B", "B-partial"):
            dst_dir = canon_folder / "_재추출"
            dst = dst_dir / cleaned_name
            status_tag = "B_정본확장" if cls == "B" else "B_부분_확인필요"
        else:  # C
            # 정본 폴더 자체가 새로 생성되는 경우 (송영곤 사례연습 가족/담보/물권/민총) → 폴더 root
            # 기존 폴더가 있으면 _재추출/으로
            if canon_folder.exists():
                dst_dir = canon_folder / "_재추출"
            else:
                dst_dir = canon_folder
            dst = dst_dir / cleaned_name
            status_tag = "C_unique_확인필요"

        dst_dir.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            ts = datetime.now().strftime("%H%M%S")
            dst = dst.with_name(f"{dst.stem}_{ts}{dst.suffix}")

        # 새 frontmatter 작성 (기존 source_pdf 등 유지 + status 추가)
        new_yaml_lines = ["---"]
        new_yaml_lines.append(f'status: {status_tag}')
        new_yaml_lines.append(f'분류일: {TODAY}')
        new_yaml_lines.append(f'분류배경: "_ocr_extracted/ raw OCR 통합 작업 (sha256 fingerprint 비교)"')
        if original_yaml.get("source_pdf"):
            new_yaml_lines.append(f'source_pdf: "{original_yaml["source_pdf"]}"')
        new_yaml_lines.append(f'source_pdf_stem: "{pdf_stem}"')
        if original_yaml.get("pdf_pages"):
            new_yaml_lines.append(f'pdf_pages: "{original_yaml["pdf_pages"]}"')
        if original_yaml.get("extracted_at"):
            new_yaml_lines.append(f'extracted_at: "{original_yaml["extracted_at"]}"')
        if original_yaml.get("engine"):
            new_yaml_lines.append(f'engine: "{original_yaml["engine"]}"')
        new_yaml_lines.append(f'raw_본문_sha256: "{rec["raw_hash"]}"')
        new_yaml_lines.append(f'raw_원경로: "{str(rp).replace(chr(92), "/")}"')
        new_yaml_lines.append(f'분류근거: "{rec["reason"]}"')
        if rec.get("best_match"):
            bm = rec["best_match"].replace(chr(92), "/")
            new_yaml_lines.append(f'best_정본후보: "{bm}"')
        if original_match_arr:
            new_yaml_lines.append(f'matched_existing_mds_count: {len(original_match_arr)}')
        new_yaml_lines.append(f'union_ratio: {rec.get("union_ratio", 0)}')
        new_yaml_lines.append(f'best_match_ratio: {rec.get("best_match_ratio", 0)}')
        new_yaml_lines.append("---")
        new_yaml = "\n".join(new_yaml_lines)

        # 본문 그대로 (body는 strip_yaml 결과)
        new_text = new_yaml + "\n" + body
        # 본문 검증: body 부분 sha256
        body_hash_after = hashlib.sha256(fingerprint(body).encode()).hexdigest()

        dst.write_text(new_text, encoding="utf-8")
        # 원본 raw 삭제 (이동) — 빈 폴더는 유지
        rp.unlink()

        moves.append({
            "src": str(rp), "dst": str(dst), "classification": cls,
            "status_tag": status_tag,
            "raw_hash": rec["raw_hash"],
            "body_hash_after": body_hash_after,
            "body_hash_match": body_hash_after == rec["raw_hash"],
            "matched_canon": rec.get("best_match"),
        })
        print(f"  [{cls}] {rp.name} -> {dst.name}  (status={status_tag})")

    # raw 빈 폴더는 유지(삭제 금지) — 이동만
    print(f"\n[APPLY] 총 {len(moves)}건 이동 완료")
    moves_path = out.with_name(out.stem + "_moves.json")
    moves_path.write_text(json.dumps(moves, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[APPLY] 이동 로그: {moves_path}")

    # 본문 sha256 검증 통계
    if moves:
        non_a = [m for m in moves if m.get("body_hash_after") is not None]
        match_count = sum(1 for m in non_a if m.get("body_hash_match"))
        print(f"[APPLY] 본문 sha256 일치: {match_count}/{len(non_a)} (B/C only, A는 _trash 이동만)")


if __name__ == "__main__":
    main()
