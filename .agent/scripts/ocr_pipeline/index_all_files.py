"""OCR 잔존 스코어 계산 + 전체 파일 인덱싱.

출력: .agent/state/all_files_index.json
  [{"path": "...", "subject": "민법", "textbook": "강혜림_민법1",
    "lines": 320, "ocr_score": 0.12, "ocr_hits": 14}, ...]

파일럿 선정: --pilot 옵션으로 과목별 상위 5개 출력.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_p = os.path.abspath(__file__)  # noqa: E402
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:  # noqa: E402
    _p = os.path.dirname(_p)  # noqa: E402
sys.path.insert(0, os.path.join(_p, 'scripts'))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

WORKSPACE_ROOT = Path(VAULT_ROOT)
SOURCE_ROOT = WORKSPACE_ROOT / "sync" / "_교재원문"
OUTPUT_PATH = WORKSPACE_ROOT / ".agent" / "state" / "all_files_index.json"

EXCLUDE_DIRS = {"_backup_", "_trash", "_재추출", "_재추출본", "_raw", "_src", "_orig", "_archive"}

SUBJECTS = ["민법", "형법", "헌법", "선택법"]

# OCR 잔존 패턴 (가중치)
# 높을수록 확실한 OCR 오류
OCR_PATTERNS: list[tuple[re.Pattern, float]] = [
    # 희귀 한자 (당사자명 오인식 잔존) — hanja_fix에서 못 잡은 것
    (re.compile(r"[芮雨因戊]"), 3.0),
    # 알파벳/숫자가 한글 단어 중간에 박혀 있음 (공백 없이)
    (re.compile(r"[가-힣][A-Za-z0-9%:$#@&*][가-힣]"), 2.5),
    # 한글과 붙은 괄호 없는 숫자+특수문자 조합 (예: 시1:%, $뻄뽀, 뽀좇)
    (re.compile(r"[가-힣]\d+[:％%]"), 2.0),
    # 문장 중간에 ■ ● ○ ◆ ▷ ▶ 나타남 (줄 시작 제외)
    (re.compile(r"(?<=\S)[■●○◆▷▶◀◁]\S"), 1.5),
    # 조사/어미 뒤에 바로 한글 단어 (공백 없음) — spacing 잔존
    (re.compile(r"(?<=[가-힣])(이|가|은|는|을|를|에|의|와|과|로|도|만)(된|한|될|할|하는|되는|있는|없는|경우|때|것|점)[가-힣]"), 1.0),
    # 페이지 마커 형식 오류 잔존 (<!-- p.NNN --> 이 아닌 것)
    (re.compile(r"^\d{1,4}\s*[¦|]\s"), 2.0),
    # 이상한 한글 음절 연속 (의미 없는 3음절+ 덩어리, 뻄뽀뽀좇 등)
    # 형태소 분석 없이 근사: ㅃ/ㄸ/ㄲ 쌍자음 포함 3+ 연속 (OCR 노이즈)
    (re.compile(r"[뻄뽀쩔뻑뻤뻘쩐쩝쩡쩔뽁뽂뽃뽄뽅뽆뽇뽈뽉뽊뽋뽌뽍뽎뽏뽐뽑뽒뽓뽔뽕]{2,}"), 3.0),
    # 연속 공백 3칸 이상 (formatting artifact)
    (re.compile(r"[ \t]{4,}"), 0.5),
]


def is_excluded(path: Path) -> bool:
    for part in path.parts:
        for ex in EXCLUDE_DIRS:
            if part.startswith(ex) or part == ex:
                return True
    return False


def ocr_score(text: str) -> tuple[float, int]:
    """텍스트의 OCR 잔존 스코어(0~1)와 히트 수 반환."""
    lines = text.splitlines()
    if not lines:
        return 0.0, 0

    total_weight = 0.0
    hit_count = 0
    for line in lines:
        for pattern, weight in OCR_PATTERNS:
            matches = pattern.findall(line)
            if matches:
                total_weight += weight * len(matches)
                hit_count += len(matches)

    # 스코어 = 총 가중치 / 라인 수 (클수록 오염도 높음, 0~∞)
    score = total_weight / max(len(lines), 1)
    return round(score, 4), hit_count


def index_files(root: Path = SOURCE_ROOT) -> list[dict]:
    records = []
    for subj in SUBJECTS:
        subj_path = root / subj
        if not subj_path.exists():
            continue
        for md in sorted(subj_path.rglob("*.md")):
            if is_excluded(md):
                continue
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lines = text.splitlines()
            score, hits = ocr_score(text)
            # 교재명: 과목 바로 아래 폴더
            parts = md.relative_to(subj_path).parts
            textbook = parts[0] if len(parts) > 1 else ""
            records.append({
                "path": str(md.relative_to(WORKSPACE_ROOT)),
                "subject": subj,
                "textbook": textbook,
                "lines": len(lines),
                "ocr_score": score,
                "ocr_hits": hits,
            })
    return sorted(records, key=lambda r: r["ocr_score"], reverse=True)


def select_pilot(records: list[dict], per_subject: int = 5) -> list[dict]:
    """과목별 상위 N개 선정."""
    pilot = []
    seen: dict[str, int] = {}
    for r in records:
        s = r["subject"]
        if seen.get(s, 0) < per_subject:
            pilot.append(r)
            seen[s] = seen.get(s, 0) + 1
    return pilot


def main() -> None:
    pilot_mode = "--pilot" in sys.argv

    print("인덱싱 중...")
    records = index_files()
    print(f"  총 {len(records)} 파일")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → {OUTPUT_PATH}")

    if pilot_mode:
        pilot = select_pilot(records, per_subject=5)
        pilot_path = OUTPUT_PATH.parent / "pilot_files.json"
        pilot_path.write_text(json.dumps(pilot, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n파일럿 선정 ({len(pilot)}개):")
        for r in pilot:
            print(f"  [{r['subject']}] {r['textbook']} | score={r['ocr_score']} hits={r['ocr_hits']} lines={r['lines']}")
            print(f"    {r['path']}")
        print(f"\n  → {pilot_path}")


if __name__ == "__main__":
    main()
