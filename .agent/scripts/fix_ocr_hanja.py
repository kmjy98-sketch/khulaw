"""OCR 희귀 한자 → 당사자명 한글 치환.

안전 규칙:
- `芮`, `雨` : 당사자 맥락(갑·을·병·정 근방)이면 전부 `병`으로 치환. 이 두 문자는
  일반 한국어 법학 교재 본문에 거의 쓰이지 않으므로 위험 낮음.
- `因`      : 갑/을/Z/기/병/정 인접 시 `병`. 단독 등장(國內 등 일반 단어)은 보존.
- `成`      : 당사자 맥락이면서 이름 패턴(成이/成은/成의/成를/成에게)일 때 `무`.
  괄호 표기 `성(成)`은 보존.
- `Z`       : 한글 조사(이/은/는/을/를/의/에/와/과/도/부터/에게)가 바로 뒤에 붙으면
  `을`로 치환. 숫자/영문과 붙은 경우(Z3, 23Z급 등)는 보존.
- `戊`      : 당사자 맥락이면 `무`. 이인규_사례연습 계열만 등장.

김준호 민법강의 전용 추가 규칙 (2026-04-22):
- `內` → 병, `日` → 을, `江` → 을, `人` → 병, `石` → 을, `仁` → 병, `西` → 무
  각각 조사 직접 연결 + 당사자 맥락 필수. 괄호 안 고립(`(內)`)은 보존.

치환 대상 아님(명시적 건너뜀): `기`, `하`, `X`, `Y`, `丁`(원문 한자).

백업: 5.기타/교재원문_백업/{date}/hanja_fix/{상대경로}
"""

from __future__ import annotations

import re
import shutil
import sys
from datetime import date
from pathlib import Path

WORKSPACE_ROOT = Path(r"H:\내 드라이브")
DEFAULT_ROOT = Path(r"H:\내 드라이브\sync\_교재원문")

# 당사자 이름 맥락 — 같은 문단(라인) 안에 이 중 하나라도 있어야 치환 허용
PARTY_CONTEXT = re.compile(r"[갑을병정무]|[甲乙丙丁戊己庚辛壬癸]|\bZ\b")

# 조사가 바로 뒤에 오는 경우 (당사자 이름 쓰임새)
FOLLOWED_BY_PARTICLE = re.compile(r"(?=[이은는을를의에와과도만부터]|에게|에서|이나|과의)")

# ── 치환 규칙 ─────────────────────────────────────────────────
# (pattern, replacement, requires_party_context)

RULES: list[tuple[re.Pattern[str], str, bool]] = [
    # 芮 — 거의 확실히 병. 맥락 요구 없이 치환하되 괄호 표기만 보존
    (re.compile(r"芮"), "병", False),
    # 雨 — 거의 확실히 병.
    (re.compile(r"雨"), "병", False),
    # 因 — 당사자 맥락에서만 병으로 (國內 등 일반어는 "內"이지 "因"이 아니므로 대체로 안전)
    (re.compile(r"因"), "병", True),
    # 成 — 당사자 이름 패턴만 (成이/成은/成의/成를/成에게/成도/成과)
    (re.compile(r"成(?=[이은는을를의에와과도만]|에게|에서)"), "무", True),
    # 戊 — 당사자 맥락에서 무
    (re.compile(r"戊(?=[이은는을를의에와과도만]|에게|에서)"), "무", True),
    # Z — 조사 바로 뒤가 있는 경우만 을로
    (re.compile(r"\bZ(?=[이은는을를의에와과도만]|에게|에서)"), "을", True),
    # Zr / Zi 같은 꼬리 OCR: "Z" + 소문자 한 글자
    (re.compile(r"\bZ[r]\b"), "을", True),
    # 김준호 민법강의 전용 — 당사자 이름 OCR 오인식
    # 모두 조사 직접 연결 + 당사자 맥락 필수 (괄호 고립 `(內)` 은 _replace 에서 보존)
    (re.compile(r"內(?=[이은는을를의에와과도만]|에게|에서)"), "병", True),
    (re.compile(r"日(?=[이은는을를의에와과도만]|에게|에서)"), "을", True),
    (re.compile(r"江(?=[이은는을를의에와과도만]|에게|에서)"), "을", True),
    (re.compile(r"人(?=[이은는을를의에와과도만]|에게|에서)"), "병", True),
    (re.compile(r"石(?=[이은는을를의에와과도만]|에게|에서)"), "을", True),
    (re.compile(r"仁(?=[이은는을를의에와과도만]|에게|에서)"), "병", True),
    (re.compile(r"西(?=[이은는을를의에와과도만]|에게|에서)"), "무", True),
]


def process_line(line: str) -> tuple[str, int]:
    """한 라인을 규칙에 따라 치환. 치환 건수 반환."""
    total = 0
    has_party_context = bool(PARTY_CONTEXT.search(line))
    for pattern, repl, need_ctx in RULES:
        if need_ctx and not has_party_context:
            continue

        def _replace(m: re.Match[str]) -> str:
            # 괄호 표기 보존: (芮), 성(成), 丙(因) 등 — 한자 원문 인용으로 판단
            start = m.start()
            end = m.end()
            if start > 0 and line[start - 1] == "(" and end < len(line) and line[end] == ")":
                return m.group(0)
            return repl

        new_line, n = pattern.subn(_replace, line)
        if n:
            line = new_line
            total += n
    return line, total


def process_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    total = 0
    new_lines: list[str] = []
    for line in original.splitlines(keepends=False):
        new_line, n = process_line(line)
        new_lines.append(new_line)
        total += n

    if total == 0:
        return 0

    new_content = "\n".join(new_lines)
    if original.endswith("\n") and not new_content.endswith("\n"):
        new_content += "\n"

    if new_content == original:
        return 0

    # 백업 (sync 내부 금지 → 5.기타/교재원문_백업/로 분리)
    try:
        rel = path.relative_to(WORKSPACE_ROOT)
        backup = WORKSPACE_ROOT / "5.기타" / "교재원문_백업" / date.today().isoformat() / "hanja_fix" / rel
    except ValueError:
        backup = WORKSPACE_ROOT / "5.기타" / "교재원문_백업" / date.today().isoformat() / "hanja_fix" / path.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(new_content, encoding="utf-8")
    return total


def main(argv: list[str]) -> None:
    total_replacements = 0
    total_files = 0

    if argv:
        target = Path(argv[0])
    else:
        target = DEFAULT_ROOT

    files = sorted(target.rglob("*.md"))
    files = [
        f for f in files
        if not any(
            p.startswith("_backup") or p.startswith("_trash") or p.startswith(".")
            or p in ("_재추출", "_재추출본", "_raw", "_src", "_orig")
            for p in f.parts
        )
    ]

    for md in files:
        if md.name.endswith(".tmp.md"):
            continue
        count = process_file(md)
        if count:
            try:
                rel = md.relative_to(target)
            except ValueError:
                rel = md.name
            print(f"  [{count:>5}] {rel}")
            total_replacements += count
            total_files += 1

    print(f"\n변경 파일 {total_files}개 / 총 치환 {total_replacements}건")


if __name__ == "__main__":
    main(sys.argv[1:])
