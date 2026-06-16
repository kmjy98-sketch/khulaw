"""레인보우 OX OCR 정규화

원칙:
- raw 보존: 단어 자체는 변경하지 않는다 (이미 백업 완료)
- 보수적: 명백한 띄어쓰기 분리 오류만 수정
- 추측 보정 금지: 의심 시 [확인필요]
- 백링크 정규화는 OCR 노이즈가 너무 높아 deferred (재OCR 후 batch 처리 권고)
"""
import re
from pathlib import Path

ROOT = Path(r"H:/내 드라이브/sync/_교재원문/형법/김기용_레인보우OX")

NEW_FRONTMATTER_TPL = """---
tags: [교재원문, 형법, 김기용_레인보우OX, OX, 형법총론, 보조자료, OCR_저품질]
source: 《Rainbow 핵심 OX 형법》(2026)
subject: 형법
author: 이인규·정현석
book_type: OX
page_range: {prange}
filing: 김기용_레인보우OX (보조자료, 김기용 compact OX와 별개)
extracted_at: 2026-04-30
extractor: EasyOCR (ko+en, CPU, scale=2.0)
ocr_quality: low
ocr_notes: |
  EasyOCR 한국어 OCR 노이즈 다수 (예: 있올/있을, 해심/핵심, 대판수/대판(전)).
  본문은 raw OCR 그대로 보존. 단어 단위 교정은 의미 변경 우려로 제외.
  사건번호 백링크 정규화는 OCR 노이즈로 deferred (재OCR 후 batch).
  조문번호(§N) 백링크도 OCR 신뢰도 낮아 deferred.
backup: sync/_백업/2026-04-30/_교재원문/형법/김기용_레인보우OX/
---
"""

OCR_NOTICE = """
> [!warning] OCR 품질 주의 (2026-04-30)
> EasyOCR(CPU) 결과로 한국어 인식 노이즈가 매우 높습니다. 본 청크는 raw OCR 보존본이며 다음에 해당하는 경우 **본 파일을 인용하지 마세요**:
> - 판례 사건번호 (다수 누락·오인식: 예 `205도3557` → 실제 `2005도3557`)
> - 조문번호 (예 `제I7조` → 실제 `제17조`)
> - 한자 표현 (대부분 갑/을/병 등 누락)
>
> 사용 가능 범위: 목차·구조·논점 추출용으로만. 인용 시 원본 PDF 또는 재OCR 결과 확인 필수 ([확인필요]).

---
"""


def normalize_chunk(path: Path):
    raw = path.read_text(encoding="utf-8")

    # 기존 frontmatter 제거 (--- ... --- 첫 블록)
    if raw.startswith("---"):
        m = re.match(r"^---\n.*?\n---\n", raw, re.DOTALL)
        if m:
            body = raw[m.end():]
        else:
            body = raw
    else:
        body = raw

    # 기존 # 제목 + 0. 소스 범위 섹션 제거 (raw OCR 시작 전까지)
    body = re.sub(r"^# .*?\n+## 0\. 소스 범위.*?(?=\n<!--|\n---|\Z)", "",
                  body, count=1, flags=re.DOTALL)
    body = body.lstrip("\n-")

    # 보수적 whitespace 교정
    # 1) 줄 내부 다중 공백 → 단일 공백 (탭/들여쓰기는 제외)
    def collapse_multispace(line: str) -> str:
        # 줄 시작 들여쓰기는 보존
        m = re.match(r"^(\s*)(.*)$", line)
        indent, rest = m.group(1), m.group(2)
        rest = re.sub(r"  +", " ", rest)
        return indent + rest

    # 2) 콤마 앞 공백 제거
    # 3) 마침표 앞 공백 제거 (단, 약어 보호 어려움 → 보수적으로 ", . ," 패턴만)
    out_lines = []
    for line in body.split("\n"):
        if line.startswith("<!--") or line.startswith("---") or line.startswith("```"):
            out_lines.append(line)
            continue
        line = collapse_multispace(line)
        line = re.sub(r" ,", ",", line)
        line = re.sub(r" \.(?=[\s\)」』])", ".", line)
        out_lines.append(line)
    body = "\n".join(out_lines)

    # 페이지 범위 추출 (파일명에서)
    fname = path.stem
    pm = re.search(r"p(\d+)-(\d+)", fname)
    if pm:
        prange = f"{int(pm.group(1))}-{int(pm.group(2))}"
    else:
        prange = "unknown"

    # 새 헤더 작성
    new_header = NEW_FRONTMATTER_TPL.format(prange=prange) + \
                 f"\n# Rainbow 핵심 OX 형법 — p.{prange} (raw OCR)\n" + \
                 OCR_NOTICE

    new_text = new_header + body.lstrip("\n")
    return new_text


def main():
    files = sorted(ROOT.glob("김기용_레인보우OX_26_p*.md"))
    print(f"대상 파일 {len(files)}건")
    stats = []
    for fp in files:
        before = fp.read_text(encoding="utf-8")
        new_text = normalize_chunk(fp)
        fp.write_text(new_text, encoding="utf-8")
        stats.append({
            "file": fp.name,
            "before_size": len(before),
            "after_size": len(new_text),
            "delta": len(new_text) - len(before),
        })
        print(f"  {fp.name}: {len(before)} → {len(new_text)} ({len(new_text)-len(before):+d})")
    print("완료")


if __name__ == "__main__":
    main()
