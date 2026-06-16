"""
백링크 형식 통일 batch 변환 스크립트 (2026-04-30)

변환 규칙:
  Phase A: 풀형식 case 백링크 → 단축형
    [[대판 1999.3.12, 98다18124]]    → 대판 1999.3.12, [[98다18124]]
    [[헌재 2007.6.28, 2004헌마643]]  → 헌재 2007.6.28, [[2004헌마643]]

  Phase B: 평문 §N → [[§N]]   (§10 이상만)
    조문 §168 → 조문 [[§168]]

  Phase C: 평문 case → 단축형 백링크
    [확인필요] 라벨로만 출력. 자동 변환 X.

대상 영역: L2 정리노트(민법/형법/헌법/상법/국제법) + L3 wiki
제외 영역: L1 교재원문, _meta, _inbox, _ocr_extracted, _답안지, _발제,
            _조문원문, _판례색인, _백업, .obsidian, .trash, .smart-env, Clippings, __pycache__

제외 컨텍스트:
  - YAML frontmatter (--- ... ---)
  - 코드블록 (``` ... ```, `inline`)
  - 표 라인 (|...|)
  - 각주 정의 ([^N]: ...)
  - 이미 백링크 안에 들어있는 패턴

사용:
  python convert.py --dry-run        # 변경 예상만 출력
  python convert.py --apply          # 백업 후 실제 변환
  python convert.py --apply --zone L2_민법   # 특정 영역만
"""
import os
import re
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

SYNC = Path(r"H:\내 드라이브\sync")
BACKUP_ROOT = SYNC / "_백업" / "2026-04-30" / "backlink_normalize"

# ==== 영역 분류 ====
INCLUDE_ZONES = {"L2_민법", "L2_형법", "L2_헌법", "L2_상법", "L2_국제법", "L3_wiki"}
EXCLUDE_DIRS = {".obsidian", ".trash", ".smart-env", "Clippings", "_백업",
                "__pycache__", "_meta", "_inbox", "_ocr_extracted",
                "_답안지", "_발제", "_조문원문", "_판례색인",
                "_교재원문",  # L1
                }

def classify(path: Path) -> str:
    parts = path.relative_to(SYNC).parts
    if not parts:
        return "ROOT"
    head = parts[0]
    if head == "_교재원문":
        return "L1_교재원문"
    if head == "wiki":
        return "L3_wiki"
    if head.startswith("_"):
        return f"META_{head}"
    if head in ("민법", "형법", "헌법", "상법", "선택법", "국제법"):
        return f"L2_{head}"
    return f"OTHER_{head}"

# ==== 패턴 ====
CASE_NUMBER = r"\d{2,4}(?:다카|헌가|헌마|헌바|헌라|헌사|두|누|다|도|카|그|마|모|드|므|구|허|후|타|차|초|호|재|단)\d+"

# Phase A: 풀형식 case 백링크
# [[대판/대결/헌재/대법원/(전합) 날짜, 사건번호 (...)]]
PAT_CASE_LINK_FULL = re.compile(
    r"\[\[\s*"
    r"(대판|대결|헌재|대법원)"          # 1: 법원 종류
    r"\s*\(?전?합?\)?\s*"               # 전원합의체 표기 흡수
    r"(\d{4}[.\s]\s*\d{1,2}[.\s]\s*\d{1,2}\.?)"  # 2: 날짜
    r"[,\s]*"
    rf"({CASE_NUMBER})"                  # 3: 사건번호
    r"([^\]]*)"                          # 4: 추가 메타
    r"\]\]"
)

# Phase B: 평문 §N (§10 이상)
# negative lookbehind: 백링크 [[§N 안에 있지 않도록
PAT_ARTICLE_PLAIN = re.compile(
    r"(?<!\[\[)"          # [[ 뒤가 아님
    r"(?<!\w)"            # 앞에 단어문자 없음
    r"§(\d{1,4})"
    r"(?!\w)"             # 뒤에 단어문자 없음
    r"(?![^\[]*\]\])"     # 같은 라인 뒷부분에 ]]가 안 닫힌 [[ 안에 있지 않음
)

# Phase C (정보 수집용): 평문 case
PAT_CASE_PLAIN = re.compile(
    r"(?<!\[\[)"
    r"(대판|대결|헌재|대법원)"
    r"\s*\(?전?합?\)?\s*"
    r"(\d{4}[.\s]\s*\d{1,2}[.\s]\s*\d{1,2}\.?)"
    r"[,\s]*"
    rf"({CASE_NUMBER})"
)

# ==== 컨텍스트 처리 ====
def split_frontmatter(text: str):
    """frontmatter, body 분리"""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[:end+5], text[end+5:]
    if text.startswith("--- "):
        # `--- tags: [...]` 형식 (한 줄 frontmatter)
        nl = text.find("\n")
        if nl != -1:
            after = text[nl+1:]
            end = after.find("---")
            if end != -1:
                end_full = nl + 1 + end + 3
                return text[:end_full], text[end_full:]
    return "", text

def mask_protected_regions(body: str):
    """변환 대상 외 영역을 마스킹.
    반환: (masked_body, restore_list) — masked는 §나 case 패턴 매칭 안 됨"""
    placeholders = []

    def store(m):
        idx = len(placeholders)
        placeholders.append(m.group(0))
        return f"\x00MASK{idx:06d}\x00"

    # 코드블록 (fenced)
    body = re.sub(r"```.*?```", store, body, flags=re.DOTALL)
    # 인라인 코드
    body = re.sub(r"`[^`\n]+`", store, body)
    # 표 라인 (전체 라인 마스킹)
    body = re.sub(r"^\|.*\|\s*$", store, body, flags=re.MULTILINE)
    # 각주 정의 라인
    body = re.sub(r"^\[\^[^\]]+\]:.*$", store, body, flags=re.MULTILINE)

    return body, placeholders

def unmask(body: str, placeholders):
    def restore(m):
        idx = int(m.group(1))
        return placeholders[idx]
    return re.sub(r"\x00MASK(\d{6})\x00", restore, body)

# ==== 변환 함수 ====

def convert_phase_a(body: str):
    """풀형식 case 백링크 → 단축형 (날짜는 평문)"""
    count = 0
    examples = []

    def repl(m):
        nonlocal count
        court, date, case_no, extra = m.group(1), m.group(2), m.group(3), m.group(4)
        # 날짜 정규화: 마지막 점 보존
        date = date.strip()
        # extra 안에 의미있는 메타 (예: " 전합")가 있으면 본문 인용으로 살림
        extra_clean = extra.strip(" ,;")
        result = f"{court} {date}, [[{case_no}]]"
        if extra_clean:
            # " — 배상명령 시효중단" 같은 부가 설명: 백링크 뒤에 평문으로 출력
            result += f" {extra_clean}"
        count += 1
        if len(examples) < 5:
            examples.append((m.group(0), result))
        return result

    new_body = PAT_CASE_LINK_FULL.sub(repl, body)
    return new_body, count, examples

def convert_phase_b(body: str):
    """평문 §N → [[§N]]  (§10 이상만)"""
    count = 0
    examples = []

    def repl(m):
        nonlocal count
        n_str = m.group(1)
        n = int(n_str)
        if n < 10:
            return m.group(0)
        result = f"[[§{n_str}]]"
        count += 1
        if len(examples) < 5:
            examples.append((m.group(0), result))
        return result

    new_body = PAT_ARTICLE_PLAIN.sub(repl, body)
    return new_body, count, examples

def collect_phase_c(body: str):
    """평문 case 위치만 수집 ([확인필요] 라벨)"""
    positions = []
    for m in PAT_CASE_PLAIN.finditer(body):
        positions.append({
            "match": m.group(0),
            "case_no": m.group(3),
        })
    return positions

# ==== 메인 ====

def iter_target_files(zone_filter=None):
    for root, dirs, files in os.walk(SYNC):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if not f.endswith(".md"):
                continue
            fp = Path(root) / f
            zone = classify(fp)
            if zone not in INCLUDE_ZONES:
                continue
            if zone_filter and zone != zone_filter:
                continue
            yield fp, zone

def process_file(fp: Path, dry_run: bool, backup_each: bool):
    """단일 파일 변환. 반환: dict 통계"""
    try:
        original = fp.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": str(e), "phase_a": 0, "phase_b": 0, "phase_c": 0}

    fm, body = split_frontmatter(original)

    # body만 변환 (frontmatter는 보존)
    masked, placeholders = mask_protected_regions(body)

    # Phase A
    new_body, a_count, a_ex = convert_phase_a(masked)
    # Phase B
    new_body, b_count, b_ex = convert_phase_b(new_body)
    # Phase C (수집만)
    c_positions = collect_phase_c(new_body)

    # 마스킹 복원
    new_body = unmask(new_body, placeholders)

    new_text = fm + new_body

    changed = (new_text != original)
    if changed and not dry_run:
        if backup_each:
            rel = fp.relative_to(SYNC)
            bkp = BACKUP_ROOT / rel
            bkp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, bkp)
        fp.write_text(new_text, encoding="utf-8")

    return {
        "file": str(fp.relative_to(SYNC)),
        "phase_a": a_count,
        "phase_b": b_count,
        "phase_c": len(c_positions),
        "phase_a_examples": a_ex,
        "phase_b_examples": b_ex,
        "phase_c_positions": c_positions[:10],  # 처음 10개만
        "changed": changed,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="변경 예상만 출력")
    p.add_argument("--apply", action="store_true", help="실제 변환 적용")
    p.add_argument("--zone", help="특정 zone만 (예: L2_민법)")
    p.add_argument("--limit", type=int, default=0, help="처리 파일 수 제한 (테스트용)")
    args = p.parse_args()

    if not args.dry_run and not args.apply:
        print("--dry-run 또는 --apply 중 하나 필요")
        sys.exit(2)

    if args.apply:
        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

    results = []
    zone_stats = defaultdict(lambda: {"files_changed": 0, "phase_a": 0, "phase_b": 0, "phase_c": 0})
    n = 0
    for fp, zone in iter_target_files(zone_filter=args.zone):
        if args.limit and n >= args.limit:
            break
        r = process_file(fp, dry_run=args.dry_run, backup_each=args.apply)
        r["zone"] = zone
        if r.get("changed") or r["phase_c"] > 0:
            results.append(r)
        if r.get("changed"):
            zone_stats[zone]["files_changed"] += 1
        zone_stats[zone]["phase_a"] += r["phase_a"]
        zone_stats[zone]["phase_b"] += r["phase_b"]
        zone_stats[zone]["phase_c"] += r["phase_c"]
        n += 1

    # 출력
    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"=== {mode} ===")
    print(f"총 처리 파일: {n}")
    print()
    print(f"{'zone':<15} {'changed':>8} {'phase_a':>8} {'phase_b':>8} {'phase_c':>8}")
    print("-" * 55)
    for zone in sorted(zone_stats.keys()):
        s = zone_stats[zone]
        print(f"{zone:<15} {s['files_changed']:>8} {s['phase_a']:>8} {s['phase_b']:>8} {s['phase_c']:>8}")

    # 로그 저장
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"{mode.lower().replace('-','_')}_{ts}.json"
    log_path.write_text(json.dumps({
        "mode": mode,
        "timestamp": ts,
        "zone_filter": args.zone,
        "zone_stats": dict(zone_stats),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n로그: {log_path}")
    if args.apply:
        print(f"백업: {BACKUP_ROOT}")

if __name__ == "__main__":
    main()
