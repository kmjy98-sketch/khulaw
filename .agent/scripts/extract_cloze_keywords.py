#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re
import sys
import os  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

def extract_keywords(answer_text):
    """
    Extract 2-5 core requirement keywords from a cloze card answer.
    Rules:
    - Must be exact substring from 'a' (no changes, no abbreviations)
    - 2-14 chars, noun phrases preferred
    - Requirements, criteria, conclusions, legal effects prioritized
    - Remove quotes/parentheses at boundaries
    - If a <= 12 chars, extract only 1 keyword
    """

    # Clean parentheses/quotes at boundaries
    text = answer_text.strip()
    text = re.sub(r'^["\'\(]+', '', text)
    text = re.sub(r'["\'\)]+$', '', text)

    keywords = []

    # If text is too short, extract just one keyword
    if len(text) <= 12:
        # Try to find a meaningful noun phrase of 2-14 chars
        # Look for noun or phrase separated by particles
        matches = re.findall(r'[가-힣\w]+(?:이|가|을|를|에|에게|의|로|로부터|과|와)?[가-힣\w]*', text)
        if matches:
            for m in matches:
                if 2 <= len(m) <= 14:
                    keywords.append(m)
                    break
        if not keywords and 2 <= len(text) <= 14:
            keywords.append(text)
        return keywords[:1]

    # For longer text, extract multiple keyword candidates
    # Priority 1: Legal effect phrases (～할 수 있다, ～이 된다, 등)
    effect_patterns = [
        r'[가-힣\w]+(?:할|될|이|가|은|는)\s*수\s*있다',
        r'[가-힣\w]+(?:로\s*)?돌릴\s*수\s*있다',
        r'[가-힣\w]+(?:이|가)\s*(?:무효|취소|해제|해지)',
        r'[가-힣\w]+(?:이|가)\s*불가능하다',
        r'[가-힣\w]+(?:이|가)\s*인정된다',
    ]

    for pattern in effect_patterns:
        matches = re.finditer(pattern, text)
        for m in matches:
            phrase = m.group(0).strip()
            if 2 <= len(phrase) <= 14 and phrase in text:
                keywords.append(phrase)

    # Priority 2: Key nouns with particles (요건, 기준, 결론)
    # Find noun + particle pattern (2-14 chars)
    noun_particle_pattern = r'[가-힣\w]{1,10}(?:이|가|을|를|에|에게|의|로|로부터|과|와|도|은|는)(?:\s*[가-힣\w]{0,4})?'
    matches = re.finditer(noun_particle_pattern, text)
    seen = set()
    for m in matches:
        phrase = m.group(0).strip()
        if 2 <= len(phrase) <= 14 and phrase not in seen and phrase in text:
            keywords.append(phrase)
            seen.add(phrase)

    # Priority 3: Important noun phrases (2-14 chars, no particles)
    # Look for consecutive Hangul/word sequences
    noun_pattern = r'[가-힣\w]{2,14}'
    matches = re.finditer(noun_pattern, text)
    seen_nouns = set()
    for m in matches:
        phrase = m.group(0)
        # Skip if already extracted as compound
        if phrase not in seen_nouns and phrase in text:
            # Check if this looks like a key concept
            if any(kw in phrase or phrase in kw for kw in keywords):
                continue
            # Prioritize longer phrases
            if len(phrase) >= 4:
                keywords.append(phrase)
                seen_nouns.add(phrase)

    # Remove duplicates while preserving order
    unique_kws = []
    seen_final = set()
    for kw in keywords:
        if kw not in seen_final:
            unique_kws.append(kw)
            seen_final.add(kw)

    # Return 2-5 keywords
    return unique_kws[:5] if len(unique_kws) >= 2 else unique_kws

def process_file(input_path, output_path):
    """Process jsonl file and extract keywords"""
    count = 0
    results = []

    try:
        with open(input_path, 'r', encoding='utf-8') as infile:
            for line_num, line in enumerate(infile, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                    k = record.get('k', '')
                    a = record.get('a', '')

                    if not a:
                        continue

                    # Extract keywords
                    kw_list = extract_keywords(a)

                    # Create output record
                    output_record = {
                        'k': k,
                        'kw': kw_list
                    }

                    results.append(output_record)
                    count += 1

                except json.JSONDecodeError as e:
                    print(f"Warning: Line {line_num} JSON decode error: {e}", file=sys.stderr)
                    continue

        # Write results to output file
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for record in results:
                outfile.write(json.dumps(record, ensure_ascii=False) + '\n')

        return count

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return -1

if __name__ == '__main__':
    input_file = vp('.agent', 'state', 'kw_slices_cloze', 'slice_c01.jsonl')
    output_file = vp('.agent', 'state', 'kw_out_cloze', 'slice_c01_out.jsonl')

    count = process_file(input_file, output_file)

    if count >= 0:
        print(f"완료 {count}건")
    else:
        print(f"오류 발생", file=sys.stderr)
        sys.exit(1)
