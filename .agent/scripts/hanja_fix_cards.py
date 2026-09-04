# -*- coding: utf-8 -*-
"""
hanja_fix_cards.py — 02_cards 카드 행의 잔존 한자 한글화 (#37, feedback_no_hanja)
- 대상: outputs/02_cards/*.md 의 TSV 데이터 행(탭 2개 이상)만. 파일 머리말의 변환 보고 메모는 보존.
- Pass A: 한글(한자) 괄호 병기 제거 — "모자(母子)" → "모자" (괄호 안이 순수 한자·가운뎃점일 때만)
- Pass B: 단독 한자 음독 치환 — 당사자 10간(甲乙丙丁戊己庚辛壬癸) + 성씨(芮·成) + 검증된 음독자
- 제외: 不(부/불 중의) 등 미검증 문자 — 잔여분은 보고서로 남김
- 백업: 변경 원본 행 → 5.기타/카드백업_한자치환_{날짜}/changed_lines_backup.jsonl (#16)
- anchor(사건번호·조문번호)는 숫자·한글이라 영향 없음 (#34)
"""
import json
import os
import re
import sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

SRC = Path(vp("outputs", "02_cards"))
BAK_DIR = Path(vp("5.기타", "카드백업_한자치환_2026-06-11"))

HANJA = re.compile(r"[一-鿿]")
# 한글(한자병기) — 괄호 안이 한자(·포함)뿐일 때 괄호째 제거
PAREN = re.compile(r"(?<=[가-힣])[(（]([一-鿿][一-鿿·]{0,11})[)）]")

CHAR_MAP = str.maketrans({
    # 당사자 10간 + 성씨
    "甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무",
    "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계",
    "芮": "예", "成": "성",
    # 가족·단독 지칭 (컨텍스트 검증됨)
    "母": "모", "父": "부", "妻": "처", "夫": "부", "子": "자",
    # 검증된 음독 단독자
    "道": "도", "條": "조", "無": "무", "全": "전", "合": "합",
    "正": "정", "有": "유", "占": "점", "性": "성", "物": "물",
    "權": "권", "法": "법", "的": "적", "人": "인", "同": "동",
    "前": "전", "私": "사", "使": "사", "者": "자", "死": "사",
    "知": "지", "時": "시", "自": "자", "異": "이", "期": "기",
    "多": "다", "公": "공", "大": "대", "主": "주", "地": "지",
    "意": "의", "章": "장", "債": "채", "燒": "소", "延": "연",
    "頭": "두", "冒": "모", "源": "원", "孫": "손", "路": "로",
})


def fix_line(line: str) -> str:
    line = PAREN.sub("", line)
    return line.translate(CHAR_MAP)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    BAK_DIR.mkdir(parents=True, exist_ok=True)
    backup, residual = [], Counter()
    files_changed = lines_changed = before_total = after_total = 0

    for f in sorted(SRC.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")
        changed = False
        for i, line in enumerate(lines):
            if line.count("\t") < 2 or not HANJA.search(line):
                continue
            before_total += len(HANJA.findall(line))
            new = fix_line(line)
            after_total += len(HANJA.findall(new))
            residual.update(HANJA.findall(new))
            if new != line:
                backup.append({"file": f.name, "line": i + 1, "original": line})
                lines[i] = new
                lines_changed += 1
                changed = True
        if changed:
            assert len(lines) == len(text.split("\n")), f"행 수 변동: {f.name}"
            f.write_text("\n".join(lines), encoding="utf-8")
            files_changed += 1

    (BAK_DIR / "changed_lines_backup.jsonl").write_text(
        "\n".join(json.dumps(b, ensure_ascii=False) for b in backup), encoding="utf-8"
    )
    print(f"파일 {files_changed}개 / 행 {lines_changed}개 변경, 카드행 한자 {before_total} → {after_total}")
    print("잔여(미치환) 문자:", dict(residual.most_common(25)))
    print(f"백업: {BAK_DIR / 'changed_lines_backup.jsonl'} ({len(backup)}행)")


if __name__ == "__main__":
    sys.exit(main())
