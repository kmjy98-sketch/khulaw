#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

input_file = vp(".agent", "state", "kw_slices_cloze", "slice_c32.jsonl")
output_file = vp(".agent", "state", "kw_out_cloze", "slice_c32_out.jsonl")

def extract_keywords(text):
    """
    법리 문장에서 핵심 요건 키워드 2~5개 추출

    규칙:
    ①반드시 원문에 그대로 등장하는 연속 부분 문자열만
    ②2~14자 명사구 위주, 조사 포함 가능
    ③요건·기준·결론·법적 효과가 되는 표현 우선
    ④따옴표·괄호가 경계에 걸리면 빼고 안쪽 텍스트만
    ⑤a가 12자 이하면 1개만
    """

    # 12자 이하면 1개만
    if len(text) <= 12:
        # 가장 긴 의미 있는 청크 (2~14자)
        matches = re.findall(r'[가-힣\w]{2,14}', text)
        if matches:
            # 가장 긴 것
            result = [max(matches, key=len)]
            return result
        return []

    keywords = []

    # 핵심 패턴: "XXX + 술어" 구조 추출
    # 예: "표현대리가 성립한 경우", "대리권 남용이 문제될 수 있고"

    # 패턴 1: "~할 수 있다", "~돌릴 수 있다" 등 법적 효과
    effects = re.findall(r'[가-힣]{2,14}(?:으로|을|에)\s*(?:돌릴|판단|인정|거절|거부)\s*수\s*있', text)
    if effects:
        for eff in effects[:2]:
            if eff not in keywords:
                keywords.append(eff)

    # 패턴 2: 명사 + 이/가 (주제)
    subjects = re.findall(r'([가-힣]{2,14})(?:이|가|가)\s+(?:성립|불성립|문제|인정|부정|필요|요구)', text)
    for subj in subjects[:3]:
        if subj not in keywords and len(subj) <= 14:
            keywords.append(subj)

    # 패턴 3: "~일 때", "~면", "~으면" (조건)
    conditions = re.findall(r'([가-힣]{2,14})(?:일|이)\s*(?:때|면|므로)', text)
    for cond in conditions[:2]:
        if cond not in keywords and len(cond) <= 14:
            keywords.append(cond)

    # 패턴 4: 중요 법률 용어 직접 추출 (이미 원문에 있는지 확인)
    legal_terms = [
        '표현대리', '대리권 남용', '자신이나 제3자의 이익',
        '고의 또는 과실', '무효로 돌릴 수 있다',
        '계약을 무효로', '부당이득', '손해배상',
        '채무불이행', '불법행위', '과실책임'
    ]

    for term in legal_terms:
        if term in text and term not in keywords:
            keywords.append(term)

    # 중복 제거 및 5개 제한
    final = []
    for kw in keywords:
        if kw not in final and 2 <= len(kw) <= 14:
            final.append(kw)
        if len(final) >= 5:
            break

    # 부족하면 일반 명사구 추가 (2~8자)
    if len(final) < 2:
        general = re.findall(r'[가-힣]{2,8}', text)
        if general:
            for term in general:
                if term not in final:
                    final.append(term)
                    if len(final) >= 2:
                        break

    return final[:5]

# 처리
count = 0
output_lines = []

with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        try:
            record = json.loads(line)
            k = record.get('k', '')
            a = record.get('a', '')

            if not a:
                continue

            kw = extract_keywords(a)

            output_record = {
                'k': k,
                'kw': kw
            }

            output_lines.append(json.dumps(output_record, ensure_ascii=False, separators=(',', ':')))
            count += 1

        except json.JSONDecodeError:
            continue

# 출력 파일 생성
with open(output_file, 'w', encoding='utf-8') as f:
    for line in output_lines:
        f.write(line + '\n')

print(f"완료 {count}건")
