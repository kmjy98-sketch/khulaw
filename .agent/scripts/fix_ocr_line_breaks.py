"""
OCR 추출 과정에서 문장 중간에 삽입된 줄바꿈(+ 빈 줄)을 원복.

패턴:
    이전 줄 끝: 한글 문자로 끝나며 종결 기호(다./함./. 등)가 아님
    다음 줄 시작: 조사/어미/연결어("서", "의", "가", "를" …)로 시작
→ 이 경우 사이의 빈 줄을 제거하고 두 줄을 공백 없이 이어 붙임.

블록 마커(헤더, 리스트, blockquote, 표 등)로 시작하는 줄은 건너뜀.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path
from datetime import date

# 다음 줄이 이 패턴으로 시작하면 이어붙임
# 조사·어미·연결어 단독 등장
JOIN_STARTERS = [
    # 단일 조사 (단독 or 뒤에 공백/연결형)
    r"서(?![가-힣])",       # 에 + 서 분할
    r"의(?:\s|$|[^가-힣])",
    r"가(?:\s|$|[^가-힣])",
    r"이(?:\s|$|[^가-힣])",
    r"는(?:\s|$|[^가-힣])",
    r"은(?:\s|$|[^가-힣])",
    r"을(?:\s|$|[^가-힣])",
    r"를(?:\s|$|[^가-힣])",
    r"에(?:\s|$|[^가-힣])",
    r"도(?:\s|$|[^가-힣])",
    r"로(?:\s|$|[^가-힣])",
    r"와(?:\s|$|[^가-힣])",
    r"과(?:\s|$|[^가-힣])",
    r"만(?:\s|$|[^가-힣])",
    # 결합 조사
    r"에도(?:\s|$|[^가-힣])",
    r"에는(?:\s|$|[^가-힣])",
    r"에서(?:\s|$|[^가-힣])",
    r"에서는(?:\s|$|[^가-힣])",
    r"에서도(?:\s|$|[^가-힣])",
    r"에게(?:\s|$|[^가-힣])",
    r"에만(?:\s|$|[^가-힣])",
    r"으로(?:\s|$|[^가-힣])",
    r"으로서(?:\s|$|[^가-힣])",
    r"으로써(?:\s|$|[^가-힣])",
    r"으로는(?:\s|$|[^가-힣])",
    r"으로도(?:\s|$|[^가-힣])",
    r"라도(?:\s|$|[^가-힣])",
    r"라면(?:\s|$|[^가-힣])",
    r"부터(?:\s|$|[^가-힣])",
    r"까지(?:\s|$|[^가-힣])",
    # 연결형
    r"라고\s",
    r"라는\s",
    r"이라고\s",
    r"이라는\s",
    r"하여\s",
    r"되어\s",
    r"된\s",
    r"한\s",
    r"할\s",
    r"될\s",
    r"하는\s",
    r"되는\s",
    r"한다(?:\.|\s|$)",
    r"어야\s",
    r"여야\s",
    # 인용 사건번호 시작 (e.g. 2005두5956, 95다6601)
    r"\d{2,4}[다두마나가라허]\d+",
    # 연도.월.일 뒤에 이어지는 사건번호
    r"\d{4}[다두마나가라허]",
]

JOIN_STARTER_RE = re.compile(r"^(?:" + "|".join(JOIN_STARTERS) + r")")

# 블록 마커 (새 블록 시작) — 이어붙이면 안 되는 경우
BLOCK_MARKER_RE = re.compile(
    r"^\s*(?:#{1,6}\s|>\s?|-\s|\*\s|•\s|\||<!--|\[\^|\[\!|"  # 마크다운 구조
    r"\d+\.\s|[가-힣]\.\s|\([가-힣]\)\s|"                    # 리스트 번호
    r"[①-⑳]|[㉠-㉿]|"                                          # 한자/원문자
    r"\*\*[^*]"                                                  # **강조
    r")"
)

# 이전 줄이 명확한 종결 기호로 끝나면 결합하지 않음.
# 단 날짜 형식 "YYYY.M.D."로 끝나는 경우는 인용 중단으로 보고 결합 허용.
TERMINATOR_END_RE = re.compile(
    r"(?:"
    r"[가-힣][\.\!\?][\"'\)\]]?|"              # 한글 + 마침표/느낌표/물음표
    r"다\.|함\.|음\.|됨\.|임\.|없\.|있\.|"
    r"\)\s*\.?|"                                 # 인용 끝 ")"
    r"—|–|"                                       # em/en dash
    r"\]\s*\.?"                                  # [^NNN] 각주 후
    r")\s*$"
)

# 날짜/연월일로 끝나는 패턴 — 인용 중간 분할 가능성
DATE_END_RE = re.compile(r"\d{4}\.\d{1,2}\.\d{1,2}\.?\s*$")

# 이전 줄 끝이 한글 or 숫자로 끝나야 결합 대상
KOREAN_OR_DIGIT_END_RE = re.compile(r"[가-힣\d]\s*$")

# prev가 이 조사/어미로 끝나면 next가 일반 한글 단어라도 결합 허용 (강한 연결형)
PREV_STRONG_CONTINUATION_END = re.compile(
    r"(?:"
    r"의|을|를|에|에서|에게|로|으로|에도|에는|에서는|에서도|으로서|으로써|으로도|"
    r"와|과|며|면|고|만|부터|까지|서|도|"
    r"라고|라는|이라고|이라는|라도|라면|"
    r"한|된|할|될|하는|되는|하여|되어|하고|되고|하며|되며|하면|되면|"
    r"받은|지급한|있는|없는|같은|다른|모든|"
    r"이|가|은|는"
    r")\s*$"
)


def should_join(prev: str, nxt: str) -> bool:
    if not prev.strip() or not nxt.strip():
        return False
    # next가 블록 시작이면 제외
    if BLOCK_MARKER_RE.match(nxt):
        return False
    # prev가 한글 또는 숫자로 끝나야 함
    if not KOREAN_OR_DIGIT_END_RE.search(prev):
        return False
    # prev가 명확한 종결기호로 끝나면 제외 (날짜 패턴은 예외)
    if TERMINATOR_END_RE.search(prev) and not DATE_END_RE.search(prev):
        return False
    next_lstripped = nxt.lstrip()
    # 규칙 1: next가 연결 조사/어미로 시작
    if JOIN_STARTER_RE.match(next_lstripped):
        return True
    # 규칙 2: prev가 강한 연결 조사/어미로 끝나고 next가 한글로 시작
    if PREV_STRONG_CONTINUATION_END.search(prev) and re.match(r"[가-힣]", next_lstripped):
        return True
    return False


def fix_file(path: Path) -> tuple[int, int]:
    """파일을 원위치 수정. (join 횟수, 영향 받은 라인 수) 반환."""
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=False)

    out: list[str] = []
    i = 0
    joins = 0

    while i < len(lines):
        line = lines[i]
        # 빈 줄을 만나면 out[-1]과 다음 비어있지 않은 줄을 결합할지 검사
        if line.strip() == "" and out:
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and should_join(out[-1], lines[j]):
                next_lstripped = lines[j].lstrip()
                # next가 조사/어미로 시작하면 공백 없이, 명사로 시작하면 공백 삽입
                if JOIN_STARTER_RE.match(next_lstripped):
                    separator = ""
                else:
                    separator = " "
                out[-1] = out[-1].rstrip() + separator + next_lstripped
                joins += 1
                i = j + 1
                continue

        # 규칙: 인용 분할 (날짜. → 사건번호) — 빈 줄 없이도 결합
        # prev 라인이 "YYYY.M.D." 또는 "YYYY.M.D.자" 로 끝나고
        # next 라인이 "YYYY두/다/가/나/라 NNNN" 으로 시작하면 결합
        if line.strip() == "" and out and i + 1 < len(lines):
            # blank + next with case number — 이미 위에서 처리됨
            pass
        if out and line.strip():
            prev = out[-1]
            if re.search(r"\d{4}\.\d{1,2}\.\d{1,2}\.\s*$", prev) and re.match(r"^\s*\d{4}[가나다두라마바사아자차카타파]\w*", line):
                # 공백 하나로 결합
                out[-1] = prev.rstrip() + " " + line.lstrip()
                joins += 1
                i += 1
                continue

        out.append(line)
        i += 1

    new_content = "\n".join(out)
    # 원본 trailing newline 유지
    if original.endswith("\n") and not new_content.endswith("\n"):
        new_content += "\n"

    if new_content != original:
        # 백업 위치: 5.기타/교재원문_백업/{date}/linebreak_fix/{상대경로} (sync 외부)
        workspace_root = Path(r"H:\내 드라이브")
        try:
            rel = path.relative_to(workspace_root)
            backup = workspace_root / "5.기타" / "교재원문_백업" / date.today().isoformat() / "linebreak_fix" / rel
        except ValueError:
            backup = workspace_root / "5.기타" / "교재원문_백업" / date.today().isoformat() / "linebreak_fix" / path.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(new_content, encoding="utf-8")

    return joins, len(lines) - len(out)


def main(argv: list[str]) -> None:
    """인자 없으면 송영곤_쟁점노트 기본 처리.
       인자 1개(디렉터리)면 해당 디렉터리의 *.md 처리.
       인자 2개 이상(디렉터리 + 파일명들)이면 특정 파일만 처리."""
    default_dir = Path(r"H:\내 드라이브\sync\_교재원문\민법\송영곤_쟁점노트")
    total_joins = 0

    if not argv:
        target_dir = default_dir
        files = sorted(target_dir.glob("*.md"))
    elif len(argv) == 1 and Path(argv[0]).is_dir():
        target_dir = Path(argv[0])
        files = sorted(target_dir.rglob("*.md"))
        # 백업/휴지통/임시/원본 폴더 제외
        files = [
            f for f in files
            if not any(
                p.startswith("_backup") or p.startswith("_trash") or p.startswith(".")
                or p in ("_재추출", "_재추출본", "_raw", "_src", "_orig")
                for p in f.parts
            )
        ]
    else:
        target_dir = default_dir
        files = [target_dir / t for t in argv]

    for md in files:
        if not md.exists() or md.name.endswith(".tmp.md"):
            continue
        joins, removed = fix_file(md)
        if joins:
            print(f"  [{joins:>4} joins / -{removed:>3} lines] {md.relative_to(target_dir) if md.is_relative_to(target_dir) else md.name}")
            total_joins += joins

    print(f"\n총 {total_joins}건 결합")


if __name__ == "__main__":
    main(sys.argv[1:])
