# -*- coding: utf-8 -*-
"""_casebook_extract.py — 사례집 모범답안(OCR md) → unit 스키마 초안 추출 (파일럿).

대상 구조(민사사례연습1 등): 설문(`N. ... (NN점)`) → 모범답안(논점정리→청구별 검토→결론).
자동 추출 신뢰도:
  - 高: 근거조문(민법 제X조/§X), 판례(대판 …다…), 결론(기각/인용/유죄/무죄)
  - 中: 라벨(청구/죄명 헤더), 쟁점(<mark>[..]</mark>·논점정리 항목)
  - 低(검토필요): 요건사실·포섭_사실 — OCR 산문이라 휴리스틱. 06a user_issue_list 보강 권장.
추출 못 한 항목은 빈 리스트 + needs_review 플래그로 둔다(#2 — 추측 금지).
시스템 유틸리티(#30 면제).
"""
import re

_JOMUN = re.compile(r"민법\s*제\s*(\d+)\s*조(?:\s*제\s*(\d+)\s*항)?(?:\s*(단서))?|§\s*(\d+)")
_PANYE = re.compile(
    r"(?:대판|대결|헌재)\s*\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?\s*[,]?\s*"
    r"\d+(?:다|도|두|므|그|헌[가-힣]?)\d+(?:\s*[·,]\s*\d+(?:다|도)?\d+)*"
)
_SUL = re.compile(r"(?m)^\s*(?:<mark>)?\s*(\d+)\s*\.\s*(.+?)\(\s*(\d+)\s*점\s*\)")
_HEADER = re.compile(r"(?m)^#{1,3}\s*(?:[IVXⅠ-Ⅹ]+|\d+)\s*\.\s*(.+?)\s*$")
_MARK = re.compile(r"<mark>\s*\[?\s*([^\]<\n]+?)\s*\]?\s*</mark>")
_ENUM = re.compile(r"(?:①|②|③|④|⑤|㉠|㉡|㉢|㉣)\s*([^①②③④⑤㉠㉡㉢㉣\n]{4,60})")
_CONCL = [("기각", "기각"), ("인용", "인용"), ("취득했", "인용"), ("취득하였", "인용"),
          ("죄책을 진다", "유죄"), ("지지 않는다", "무죄"), ("성립한다", "성립"),
          ("성립하지", "불성립")]


def _jomun_list(text):
    out = []
    for m in _JOMUN.finditer(text):
        if m.group(4):
            out.append(f"§{m.group(4)}")
        elif m.group(1):
            s = f"§{m.group(1)}"
            if m.group(2):
                s += f"①②③④⑤⑥"[int(m.group(2)) - 1] if m.group(2).isdigit() and 1 <= int(m.group(2)) <= 6 else f"제{m.group(2)}항"
            if m.group(3):
                s += " 단서"
            out.append(s)
    return list(dict.fromkeys(out))


def split_problems(md):
    """md를 설문 단위로 분할. 각 설문의 본문(다음 설문 직전까지)을 모은다."""
    marks = list(_SUL.finditer(md))
    problems = []
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(md)
        problems.append({
            "설문번호": m.group(1),
            "설문": re.sub(r"\s+", " ", m.group(2)).strip(),
            "배점": int(m.group(3)),
            "body": md[start:end],
        })
    return problems


def extract_unit(problem):
    """설문 1개 → unit 스키마 초안. 미확인 항목은 빈 + needs_review."""
    body = problem["body"]
    headers = [h.strip() for h in _HEADER.findall(body)]
    claim_headers = [h for h in headers
                     if any(k in h for k in ("청구", "죄책", "죄", "책임", "심판", "위헌"))
                     and "논점" not in h and "결" not in h]
    issues = [re.sub(r"\s+", " ", x).strip() for x in _MARK.findall(body)]
    yogeon = [re.sub(r"\s+", " ", x).strip() for x in _ENUM.findall(body)][:6]

    concl = None
    tail = body[-400:]  # 결론은 보통 말미
    for cue, label in _CONCL:
        if cue in tail or cue in body:
            concl = label
            break

    label = claim_headers[0] if claim_headers else (problem["설문"][:40] or "미상")
    needs_review = []
    if not yogeon:
        needs_review.append("요건")
    if not issues:
        needs_review.append("쟁점")
    if concl is None:
        needs_review.append("결론")

    return {
        "label": label,
        "근거": _jomun_list(body),
        "요건": yogeon,                       # 低신뢰 — 검토필요
        "쟁점": list(dict.fromkeys(issues)),   # 中
        "포섭_사실": [],                       # 자동추출 보류 — 06a 보강
        "결론": concl,
        "keywords": _panye_list(body),         # 판례 = 학설·판례 키워드
        "_배점": problem["배점"],
        "_needs_review": needs_review,
    }


def _panye_list(text):
    return list(dict.fromkeys(_PANYE.findall(text)))[:6]


def extract_file(md):
    """md 전체 → 설문별 unit 초안 리스트."""
    return [extract_unit(p) | {"_설문": p["설문"], "_설문번호": p["설문번호"]}
            for p in split_problems(md)]
