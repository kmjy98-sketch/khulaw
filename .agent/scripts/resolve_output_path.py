#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resolve_output_path.py — 생성 산출물의 표준 목적지 '경로만' 반환 (읽기전용)
==========================================================================

CLAUDE.md #42(파일 생성 위치)·#46(정본 경로)·classification-rules_v2(과목/강의 매핑)
을 근거로, 생성 스킬(study-notes·law-note·card·OCR·찌라시·문서)이 '작성 직전' 목적지를
받도록 한다. 파일을 만들거나 옮기지 않는다 — 경로 문자열만 계산.

설계 원칙
---------
- 미매칭/불명확 → decided=False('판정보류'). 임의 추정 금지(#2).
- 0.공유드라이브/ 입력 → 차단(#16-B).
- 산출물 유형이 명확(카드·OCR·위키·찌라시·메모)하면 고정 경로(#42·#46).
- 노트류는 (과목, 현행교수) 화이트리스트에 한해 강의 폴더, 그 외 보류.
- 실제 배선(스킬 호출)은 1책 dry-run 검증 통과 후. 현재는 함수 제공만.

사용
----
from resolve_output_path import resolve_output_path
r = resolve_output_path("note", subject="민사", professor="송영곤")
# -> {"path": "1.민사/_강의/송영곤_기본민법/정리", "decided": True, "reason": "현행강의"}
"""
from __future__ import annotations

# 과목 루트 (#classification-rules_v2 §과목 분류 체계)
SUBJECT_ROOT = {
    "민사": "1.민사", "형사": "2.형사", "공법": "3.공법",
    "선택법": "4.선택법", "기타": "5.기타",
}

# 현행 강의(강의 중심) 화이트리스트 — classification-rules_v2 2026-06-16 하이브리드
CURRENT_LECTURE = {
    ("민사", "송영곤"): "1.민사/_강의/송영곤_기본민법",
    ("형사", "김기용"): "2.형사/_강의/김기용_형법교안",
    ("공법", "강성민"): "3.공법/_강의/강성민_헌법",
}

# 유형이 명확한 파생 산출물 → 고정 경로 (#42·#46)
ARTIFACT_DEST = {
    "card": "outputs/02_cards_v37",           # 카드 정본 (#46)
    "ocr": "outputs/01_ocr_llamaparse",       # 교재 OCR (#46)
    "wiki": "sync/위키/원문",                  # 위키 원문 정본 (#38·#46)
    "jjirashi": "sync/찌라시",                 # 시험직전 압축 (#17)
    "meta": "9.작업중/클로드",                     # 운영 메모·보고서 (#42)
    "doc": "5.기타/문서",                      # 비노트 문서 docx 등 (#42)
    "script_oneoff": ".agent/scripts",        # 일회성 스크립트 (#42)
    "state": ".agent/state",                  # 상태 json (#42)
}

SHARED_DRIVE = "0.공유드라이브"


def resolve_output_path(artifact_type: str, subject: str | None = None,
                        professor: str | None = None, title: str | None = None) -> dict:
    """생성 산출물 목적지(상대경로)만 반환. 이동·생성 없음."""
    at = (artifact_type or "").strip().lower()

    # #16-B: 공유드라이브 입력 차단
    for v in (subject, professor, title):
        if v and SHARED_DRIVE in str(v):
            return {"path": None, "decided": False, "reason": "차단: 0.공유드라이브(#16-B)"}

    # 1) 유형 고정 산출물
    if at in ARTIFACT_DEST:
        return {"path": ARTIFACT_DEST[at], "decided": True, "reason": f"고정경로({at}, #42/#46)"}

    # 2) 노트류: 과목+현행교수 → 강의 폴더, 아니면 보류
    if at in ("note", "노트", "정리", "summary"):
        if not subject or subject not in SUBJECT_ROOT:
            return {"path": None, "decided": False, "reason": "판정보류: 과목 불명확"}
        key = (subject, (professor or "").strip())
        if key in CURRENT_LECTURE:
            return {"path": CURRENT_LECTURE[key] + "/정리", "decided": True, "reason": "현행강의(강의중심)"}
        # 현행 외 교수/책만 케이스는 92.개념 vs 91.보관 분기가 내용 의존 → 보류(#2·#45-B)
        return {"path": None, "decided": False,
                "reason": f"판정보류: '{subject}/{professor}' 현행강의 아님 — 92.개념/91.보관/책직속 중 내용 확인 필요"}

    # 3) 미지원 유형
    return {"path": None, "decided": False, "reason": f"판정보류: 미지원 유형 '{artifact_type}'"}


if __name__ == "__main__":
    import json
    import sys
    args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    print(json.dumps(resolve_output_path(
        args.get("type", ""), args.get("subject"), args.get("professor"), args.get("title")
    ), ensure_ascii=False))
