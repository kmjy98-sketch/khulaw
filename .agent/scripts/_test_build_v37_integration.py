# -*- coding: utf-8 -*-
"""_test_build_v37_integration.py — build_v37_apkg.py guid 패치 통합 검증.

컨테이너에서 genanki + 합성 카드 픽스처로 실제 빌드를 돌려:
  1) 같은 위치 카드의 본문을 수정해도 guid가 불변(재임포트 회독 보존)
  2) 같은 출처·내용 중복 카드는 dedup(카드 수 보존)
실 H:\ 카드(19,629장) 규모 검증은 로컬에서. 여기선 패치 로직의 정확성만 확인.
실행: python3 .agent/scripts/_test_build_v37_integration.py
"""
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "build_v37_apkg.py")
PAD = "\n" * 35  # txt.count("\n")<30 skip 회피

CARD_BASIC = """### [요건] 채권자취소권
앞: 채권자취소권의 요건은?
뒤: {back}
"""
CARD_CLOZE = """### [판례] 사해행위
빈칸: 채무자의 {{{{무자력}}}}은 {extra}사해행위 취소의 요건이다
"""


def write_fixture(srcdir, back, extra):
    # 한 파일에 basic + cloze + basic중복(같은 출처·내용) → dedup 대상
    content = PAD + CARD_BASIC.format(back=back) + "\n" + CARD_CLOZE.format(extra=extra) + "\n" + CARD_BASIC.format(back=back)
    Path(srcdir, "논점민법재산법_p10-12.md").write_text(content, encoding="utf-8")


def run_build(srcdir, outdir):
    env = dict(os.environ, V37_SRC=srcdir, V37_OUT=outdir)
    r = subprocess.run([sys.executable, SCRIPT], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"build 실패:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def read_notes(outdir):
    apkg = Path(outdir, "민법", "기본서_v37.apkg")
    assert apkg.exists(), f"apkg 없음: {apkg}"
    with tempfile.TemporaryDirectory() as ex:
        with zipfile.ZipFile(apkg) as z:
            z.extractall(ex)
        db = next((p for p in Path(ex).iterdir() if p.name.startswith("collection.anki")), None)
        con = sqlite3.connect(db)
        rows = con.execute("select guid, flds from notes").fetchall()
        con.close()
    return {g: f for g, f in rows}


def main():
    with tempfile.TemporaryDirectory() as base:
        src = Path(base, "src"); out1 = Path(base, "out1"); out2 = Path(base, "out2")
        for d in (src, out1, out2):
            d.mkdir()

        # 1차 빌드
        write_fixture(src, back="피보전채권, 사해행위, 사해의사", extra="")
        run_build(str(src), str(out1))
        notes1 = read_notes(str(out1))

        # 2차 빌드: 카드 본문 수정(basic 뒤 + cloze extra 추가), 위치 동일
        write_fixture(src, back="피보전채권, 사해행위, 사해의사, 채무초과", extra="객관적으로 ")
        run_build(str(src), str(out2))
        notes2 = read_notes(str(out2))

        g1, g2 = set(notes1), set(notes2)

        # 검증 1: dedup — basic 1 + cloze 1 = 2장 (중복 basic 제거)
        assert len(notes1) == 2, f"dedup 실패: {len(notes1)}장 (기대 2). flds={list(notes1.values())}"
        print(f"[OK] dedup: 중복 basic 제거 → {len(notes1)}장(basic+cloze)")

        # 검증 2: guid 불변 — 본문 수정 후에도 guid 동일(재임포트 회독 보존)
        assert g1 == g2, f"guid 변동! 1차={g1}\n2차={g2}"
        print(f"[OK] guid 불변: 본문 수정 후에도 동일 guid {sorted(g1)}")

        # 검증 3: 내용은 실제로 갱신됨(같은 guid, 다른 flds)
        changed = [g for g in g1 if notes1[g] != notes2[g]]
        assert changed, "본문 수정이 flds에 반영 안 됨"
        print(f"[OK] 내용 갱신: {len(changed)}개 노트가 같은 guid로 flds 갱신 → 회독 보존+내용 업데이트")

        print("\n=== 통합 검증 통과: guid 안정(회독 보존) + dedup 정상 ===")


if __name__ == "__main__":
    main()
