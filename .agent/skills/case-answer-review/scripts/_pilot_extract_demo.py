# -*- coding: utf-8 -*-
"""_pilot_extract_demo.py — 사례집 → unit 추출 → 루브릭 채점 end-to-end 파일럿.

실행: python3 이파일 [casebook.md] [설문index]
기본 파일: outputs/01_ocr_llamaparse/민사사례연습1_llamaparse_p031-060.md (repo 상대경로 폴백).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _casebook_extract import split_problems, extract_unit  # noqa: E402
from _case_rubric import score_rubric_units  # noqa: E402

DEFAULT = "outputs/01_ocr_llamaparse/민사사례연습1_llamaparse_p031-060.md"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else None
    md = open(path, encoding="utf-8").read()

    problems = split_problems(md)
    print(f"[1] 설문 분할: {len(problems)}개 검출")
    for i, p in enumerate(problems):
        print(f"    [{i}] 설문{p['설문번호']} ({p['배점']}점) {p['설문'][:42]}")

    # 데모 대상: 인자 없으면 요건/쟁점/결론이 가장 잘 잡힌 설문 자동 선택
    if idx is None:
        scored = [(len(extract_unit(p)["쟁점"]) + len(extract_unit(p)["근거"])
                   + (1 if extract_unit(p)["결론"] else 0), i) for i, p in enumerate(problems)]
        idx = max(scored)[1] if scored else 0
    target = problems[idx]
    unit = extract_unit(target)

    print(f"\n[2] 추출 대상: 설문{target['설문번호']} ({target['배점']}점) — index {idx}")
    print("[3] 추출된 unit 스키마(초안):")
    print(json.dumps({k: v for k, v in unit.items() if not k.startswith("_배")},
                     ensure_ascii=False, indent=2))

    # [4] 모범답안 본문을 학생답안처럼 채점 → 자기일관성(높게 나와야 함)
    self_score = score_rubric_units(target["body"], [unit], unit_type="청구")
    print(f"\n[4] 모범답안 자기채점(sanity, 높을수록 추출 정합): "
          f"등급={self_score['grade']} 점수={self_score['score']} "
          f"제안={self_score['review_suggestions']}")
    for name, it in self_score["units"][0]["items"].items():
        print(f"      {name}: {it['status']} {it['score']}")

    # [5] 약한 답안 → 낮은 점수 + review 제안
    weak = f"{unit['label']} 정도만 언급하고 결론은 반대로 인용한다"
    weak_score = score_rubric_units(weak, [{**unit, "결론": "기각"}], unit_type="청구")
    print(f"\n[5] 약한 답안 채점: 등급={weak_score['grade']} 점수={weak_score['score']} "
          f"제안={weak_score['review_suggestions']}")

    print(f"\n[6] 검토필요(자동추출 한계) 필드: {unit['_needs_review'] or '없음'}")


if __name__ == "__main__":
    main()
