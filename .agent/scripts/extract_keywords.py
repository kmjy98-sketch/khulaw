#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re

input_file = r"H:\내 드라이브\.agent\state\kw_slices_cloze\slice_c48.jsonl"
output_file = r"H:\내 드라이브\.agent\state\kw_out_cloze\slice_c48_out.jsonl"

def extract_keywords(text):
    """
    법학 암기카드 문장에서 핵심 요건 키워드 추출
    """
    if len(text) <= 12:
        return [text]

    keywords = []

    # 핵심 어휘 패턴: 요건·법적 효과
    critical_patterns = [
        r'[\w\s가-힣]{2,14}(?:이|가|을|를|에|에게|로|로서|로부터|에서)\b',
        r'[\w\s가-힣]{2,14}(?:되|될|가능|불가능|있|없)',
        r'(?:고의|과실|선의|악의|중과실|경과실)',
        r'(?:대리권|청구권|청구|항변|항변권)',
        r'(?:성립|불성립|인정|부정|동의|승낙)',
        r'(?:책임|의무|권리|지위|지분)',
        r'[\w\s가-힣]{2,14}(?:을때|를때)',
    ]

    def clean_keyword(kw):
        kw = kw.strip()
        while kw and kw[0] in '"\'「『"\'':
            kw = kw[1:]
        while kw and kw[-1] in '"\'」』"\'':
            kw = kw[:-1]
        kw = kw.strip()
        return kw

    def is_valid_length(kw):
        return 2 <= len(kw) <= 14

    # 우선 패턴
    for pat in critical_patterns:
        for m in re.finditer(pat, text):
            kw = m.group(0)
            kw = clean_keyword(kw)
            if is_valid_length(kw) and kw not in keywords:
                keywords.append(kw)
                if len(keywords) >= 5:
                    return keywords

    # 폴백: 문장 끝 명사구
    if not keywords:
        words = text.split()
        for word in words:
            word = clean_keyword(word)
            if is_valid_length(word) and len(word) >= 2:
                keywords.append(word)
                if len(keywords) >= 5:
                    break

    return keywords if keywords else [text[:14]]

results = []
with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            k = record.get('k', '')
            a = record.get('a', '')

            kw = extract_keywords(a)
            output_record = {
                'k': k,
                'kw': kw
            }
            results.append(output_record)
        except json.JSONDecodeError:
            continue

with open(output_file, 'w', encoding='utf-8') as f:
    for record in results:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

print(f"완료 {len(results)}건")
