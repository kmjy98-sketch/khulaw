#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""빈괄호 카드 → cloze 변환 (결정적, #45-B).

`앞:` 줄의 (①)·(②)·(   ) 빈괄호를 같은 블록 `뒤:`의 ①②③ 답으로 {{cN::답}} 치환.
- (①)/(②) 숫자형: 원문자 번호 N → 뒤[N]
- (   ) 공란형: 등장 순서대로 1,2,3 → 뒤[1],뒤[2],뒤[3]
`뒤:`·`빈칸:` 줄은 그대로 둠(빌더는 cloze면 앞만 사용 — Basic 중복 안 남).

기본 dry-run: <stem>.converted.md + 리포트만. --apply 로 덮어쓰기(원본은 호출측에서 백업).
"""
import re, sys, argparse
from pathlib import Path

CIRCLED = "①②③④⑤⑥⑦⑧⑨"
def cnum(c): return CIRCLED.index(c) + 1

def parse_back(back: str) -> dict:
    back = back.strip()
    if not any(c in back for c in CIRCLED):
        return {1: back} if back else {}
    out, ms = {}, list(re.finditer(r'[①②③④⑤⑥⑦⑧⑨]', back))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(back)
        out[cnum(m.group())] = back[m.end():end].strip()
    return out

def convert_front(line: str, answers: dict, stats: dict, blk_no: int) -> str:
    def repl_num(m):
        n = cnum(m.group(1)); a = answers.get(n)
        if a is None:
            stats['warn'].append(f"블록{blk_no}: (#{n}) 답 없음"); return m.group(0)
        stats['conv'] += 1; return "{{c%d::%s}}" % (n, a)
    body = re.sub(r'\(([①②③④⑤⑥⑦⑧⑨])\)', repl_num, line)
    seq = [0]
    def repl_empty(m):
        seq[0] += 1; n = seq[0]; a = answers.get(n)
        if a is None:
            stats['warn'].append(f"블록{blk_no}: 공란#{n} 답 없음"); return m.group(0)
        stats['conv'] += 1; return "{{c%d::%s}}" % (n, a)
    body = re.sub(r'\([\s　]+\)', repl_empty, body)
    return body

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--apply", action="store_true", help="원본 덮어쓰기(기본: .converted.md)")
    a = ap.parse_args()
    src = Path(a.file); lines = src.read_text(encoding="utf-8").split("\n")
    stats = {'conv': 0, 'warn': [], 'blocks': 0}
    blk_no = 0
    for i, line in enumerate(lines):
        if line.startswith("앞:"):
            blk_no += 1
            back = None
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].startswith("뒤:"):
                    back = lines[j][len("뒤:"):].strip(); break
            if back is None:
                stats['warn'].append(f"앞{i+1}행: 뒤: 없음"); continue
            new = convert_front(line, parse_back(back), stats, blk_no)
            if new != line:
                stats['blocks'] += 1; lines[i] = new
    # 블록헤더 정규화: 단독 [속성] 줄 → ### [속성] (빌더 blocks_of 인식; 이미 ###이면 무시)
    stats['hdr'] = 0
    for i, line in enumerate(lines):
        if re.match(r'^\[[^\]\n]+\]\s*$', line):
            lines[i] = "### " + line.strip(); stats['hdr'] += 1
    out = "\n".join(lines)
    # 잔존 빈괄호 점검
    remain = len(re.findall(r'\(([①②③④⑤⑥⑦⑧⑨])\)|\([\s　]+\)', out))
    dst = src if a.apply else src.with_suffix(".converted.md")
    dst.write_text(out, encoding="utf-8")
    print(f"[{'APPLY' if a.apply else 'DRY'}] {src.name}")
    print(f"  변환 블록: {stats['blocks']} / 빈칸 치환: {stats['conv']} / ### 헤더부여: {stats.get('hdr',0)} / 잔존 빈괄호: {remain}")
    print(f"  경고: {len(stats['warn'])}")
    for w in stats['warn'][:20]:
        print("   - " + w)
    print(f"  출력: {dst}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
