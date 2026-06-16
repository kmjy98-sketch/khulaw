#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re

def extract_keywords(text):
    """
    a 텍스트에서 핵심 요건 키워드 2~5개 추출
    규칙:
    1. a에 그대로 등장하는 연속 부분 문자열만
    2. 2~14자 명사구 위주, 조사 포함 가능
    3. 요건·기준·결론·법적 효과 표현 우선
    4. 따옴표·괄호가 경계에 걸리면 빼고 안쪽 텍스트만
    5. a가 12자 이하면 1개만
    """

    # 규칙 5: 짧은 문장은 1개만
    if len(text) <= 12:
        return [text]

    keywords = []

    # 핵심 표현 패턴 (우선순위 순)
    key_patterns = [
        (r'[가-힣]{2,14}(?:이\[다면라지려면\]|일 때|할 수 있다|되다|해야)', '법적 판단'),
        (r'[가-힣]{2,14}(?:의 이익|의 효과|의 요건)', '요건 표현'),
        (r'(?:적극적|소극적|명시적|암시적|직접적|간접적)[가-힣]{2,10}', '수식어 조합'),
        (r'[가-힣]{2,14}(?:권|책임|의무|효과|기준|요건)', '법학 용어'),
    ]

    found_list = []

    # 각 패턴으로 검색
    for pattern, _ in key_patterns:
        try:
            for match in re.finditer(pattern, text):
                kw = match.group(0)
                # 조사 제거
                kw = re.sub(r'([가-힣])(은|는|이|가|을|를|에|으로|으로부터|에게|에게서|과|와|로서)$', r'\1', kw)
                # 따옴표·괄호 정리
                kw = kw.strip('""''()（）『』「」')
                # 길이 확인
                if 2 <= len(kw) <= 14 and kw not in found_list:
                    found_list.append(kw)
                # 5개 도달하면 중단
                if len(found_list) >= 5:
                    break
            if len(found_list) >= 5:
                break
        except:
            pass

    # 패턴이 충분하지 않으면 명사 후보 추출
    if len(found_list) < 2:
        tokens = re.split(r'(?<=[가-힣])(?:은|는|이|가|을|를|에|으로|에게|과|와)', text)
        for token in tokens:
            token = token.strip()
            for match in re.finditer(r'[가-힣]{2,14}', token):
                kw = match.group(0)
                if kw not in found_list:
                    found_list.append(kw)
                if len(found_list) >= 5:
                    break
            if len(found_list) >= 5:
                break

    # 최대 5개, 최소 1개 확보
    result = found_list[:5] if len(found_list) >= 2 else (found_list if found_list else [text[:14]])

    return result

# 파일 읽기 및 처리
input_path = r"H:\내 드라이브\.agent\state\kw_slices_cloze\slice_c37.jsonl"
output_path = r"H:\내 드라이브\.agent\state\kw_out_cloze\slice_c37_out.jsonl"

count = 0
with open(input_path, 'r', encoding='utf-8') as f_in, \
     open(output_path, 'w', encoding='utf-8') as f_out:

    for line in f_in:
        line = line.strip()
        if not line:
            continue

        try:
            card = json.loads(line)
            k = card.get('k')
            a = card.get('a', '')

            if not a:
                continue

            # 키워드 추출
            keywords = extract_keywords(a)

            # 출력 구성
            output_card = {
                'k': k,
                'kw': keywords
            }

            # jsonl 라인으로 기록 (유니코드 이스케이프 금지)
            f_out.write(json.dumps(output_card, ensure_ascii=False) + '\n')
            count += 1

        except json.JSONDecodeError:
            continue
        except Exception as e:
            continue

print(f"완료 {count}건")
