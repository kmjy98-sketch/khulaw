"""OCR 추출 과정에서 삭제된 공백 복원.

법학 교재 본문에서 자주 관찰되는 특정 merge 패턴만 타겟으로 삼아 공백 주입.
일반 단어 분할 시도는 하지 않음(의사/의무 같은 고유어 파괴 방지).

규칙은 모두 `조사/어미 경계` + `의미 단위 선도어(된·한·할·될·경우·때·것·그 등)` 조합에
한정. 각 규칙은 앞뒤에 한글이 붙은 경우만 변환한다.
"""

from __future__ import annotations

import re
import shutil
import sys
from datetime import date
from pathlib import Path

WORKSPACE_ROOT = Path(r"H:\내 드라이브")
DEFAULT_ROOT = Path(r"H:\내 드라이브\sync\_교재원문")

# (정규식, 치환) — 모두 앞뒤 한글 lookaround
# 조사/연결형 + 선도어 조합만 대상
SPACE_RULES: list[tuple[re.Pattern[str], str]] = [
    # 1. 조사 + 단어 (의/이/가/은/는/을/를/에/와/과/로/으로/도/만)
    (re.compile(r"(?<=[가-힣])(이|가|은|는|을|를|에|도|만|부터|까지|와|과|로|으로|에서|에게|에도|에는|에서는|에서도)(된|한|될|할|하는|되는|있는|없는|경우|때|그|이|저|것|점|수|뿐|바|듯|해|반|등|것이|중)(?=[가-힣])"), r"\1 \2"),
    # 2. 어미 + 단어
    (re.compile(r"(?<=[가-힣])(하면|하여|해서|하므로|하므로서|되어|되면|된다|한다|되는|하는|되고|하고|되며|하며|아니면|라면|라도|라고|라는)(그|이|저|경우|때|것|점|수|뿐|바|해당|반드시|당연히|마땅히|특히|즉)(?=[가-힣])"), r"\1 \2"),
    # 3. 판례 식별자 앞
    (re.compile(r"(?<=[가-힣])(대판|대결|헌재|판례|결정|판결)(?=\d{4}[\.\,])"), r"\1 "),
    # 4. 복수의 공백 정규화: 3칸 이상 → 1칸
    (re.compile(r"[ \t]{3,}"), " "),
    # 5. 이행불능/불능이 + 된
    (re.compile(r"(?<=[가-힣])이(된|된경우|됨)(?=[가-힣 ])"), r"이 \1"),
    # 6. '관한' 앞
    (re.compile(r"(?<=[가-힣])에관한(?=[가-힣])"), r"에 관한 "),
    # 7. '대한' 앞
    (re.compile(r"(?<=[가-힣])에대한(?=[가-힣])"), r"에 대한 "),
    # 8. '대하여' 앞
    (re.compile(r"(?<=[가-힣])에대하여(?=[가-힣])"), r"에 대하여 "),
    # 9. '따라/따른/따르면' 앞
    (re.compile(r"(?<=[가-힣])에따라(?=[가-힣])"), r"에 따라 "),
    (re.compile(r"(?<=[가-힣])에따른(?=[가-힣])"), r"에 따른 "),
    (re.compile(r"(?<=[가-힣])에따르면(?=[가-힣])"), r"에 따르면 "),
    # 10. '의하여/의한' 앞
    (re.compile(r"(?<=[가-힣])에의하여(?=[가-힣])"), r"에 의하여 "),
    (re.compile(r"(?<=[가-힣])에의해(?=[가-힣])"), r"에 의해 "),
    (re.compile(r"(?<=[가-힣])에의한(?=[가-힣])"), r"에 의한 "),
    # 11. '관하여' 앞
    (re.compile(r"(?<=[가-힣])에관하여(?=[가-힣])"), r"에 관하여 "),
    # 12. "~의 경우/때/권리/내용/결과"
    (re.compile(r"(?<=[가-힣])의(경우|때|권리|내용|결과|목적|효과|요건|성립|해제|해지|행사|청구|반환|양도|효력|범위|방법|의무|책임|대상|주체|취지|성질|해석|특성|특약|규정|의의|취득|상실|발생|소멸|변경|처분|점유)(?=[가-힣 ])"), r"의 \1"),
    # 13. '한다고/라고/라는/라도' 앞의 '이/그' — 제거. 오탐 위험.
    # 14a. "~(는)그목적물" 식 완전 결합 — 앞뒤 공백 복원
    (re.compile(r"(?<=[가-힣])그(목적물|권리|채권|채무|효력|부분|상태|조항|계약|사건|사안|법리|법률|판결|당시|책임|의무|경우|때|이익|목적|경위|가액|범위|대가|부동산|건물|토지|물건|원인|행위|규정|사정|처분|담보)(?=[가-힣 ])"), r" 그 \1"),
    # 14b. " 그목적물" (그는 띄워져 있으나 명사가 붙은 경우) — 뒤만 공백 복원
    (re.compile(r"(?<![가-힣])그(목적물|권리|채권|채무|효력|부분|상태|조항|계약|사건|사안|법리|법률|판결|당시|책임|의무|경우|때|이익|목적|경위|가액|범위|대가|부동산|건물|토지|물건|원인|행위|규정|사정|처분|담보)(?=[가-힣 ])"), r"그 \1"),
]


def process_line(line: str) -> tuple[str, int]:
    total = 0
    # 코드 펜스나 위키링크, 각주 정의 안은 건드리지 않음
    if line.strip().startswith("```") or line.strip().startswith("|"):
        return line, 0
    if line.strip().startswith("[^") and "]:" in line.split("]", 1)[0] + "]":
        return line, 0

    for pattern, repl in SPACE_RULES:
        new_line, n = pattern.subn(repl, line)
        if n:
            line = new_line
            total += n
    # 이중 공백 정리
    line = re.sub(r" +", " ", line)
    return line, total


def process_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    # 진입: 프론트매터 이후만 대상
    if original.startswith("---\n"):
        parts = original.split("---\n", 2)
        if len(parts) >= 3:
            front = "---\n" + parts[1] + "---\n"
            body = parts[2]
        else:
            front = ""
            body = original
    else:
        front = ""
        body = original

    total = 0
    new_lines: list[str] = []
    for line in body.splitlines(keepends=False):
        new_line, n = process_line(line)
        new_lines.append(new_line)
        total += n

    if total == 0:
        return 0

    new_body = "\n".join(new_lines)
    if body.endswith("\n") and not new_body.endswith("\n"):
        new_body += "\n"

    new_content = front + new_body
    if new_content == original:
        return 0

    try:
        rel = path.relative_to(WORKSPACE_ROOT)
        backup = WORKSPACE_ROOT / "5.기타" / "교재원문_백업" / date.today().isoformat() / "spacing_fix" / rel
    except ValueError:
        backup = WORKSPACE_ROOT / "5.기타" / "교재원문_백업" / date.today().isoformat() / "spacing_fix" / path.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(new_content, encoding="utf-8")
    return total


def main(argv: list[str]) -> None:
    total_replacements = 0
    total_files = 0

    target = Path(argv[0]) if argv else DEFAULT_ROOT

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
            total_replacements += count
            total_files += 1

    print(f"\n변경 파일 {total_files}개 / 총 치환 {total_replacements}건")


if __name__ == "__main__":
    main(sys.argv[1:])
