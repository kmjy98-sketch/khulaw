# AGENTS.md

## 적용 범위
- 이 문서는 `H:\내 드라이브\4.선택법` 하위 선택법 작업에 적용합니다.
- 루트 `H:\내 드라이브\AGENTS.md`를 함께 적용합니다. 충돌 시 과목별 자료 위치·우선순위는 이 문서를 우선합니다.
- 법리·사실 단정은 루트 근거 규칙에 따라 사용자 제공 소스와 정확한 위치가 있을 때만 출력합니다.

## 과목 기준
- 국제법: 기출, 빈출 표시가 있는 소스, 선배 찌라시를 근거 확인 후 합칩니다.
- 법조윤리: 기출별 주요 문항을 정리합니다.
- "기출/빈출" 라벨은 루트 규칙에 따라 소스 표지와 근거가 있을 때만 사용합니다.

## 현재 확인된 자료 위치
- 국제법 기출: `90.기출/국제법/`
- 국제법 보관 자료: `91.보관/국제법/백범석_국제법/`
- 법조윤리 정리본: `법조윤리_정리본_2026.pdf`
- 노동법 한권탁 자료: `91.보관/노동법/한권탁_노동법/`
- 기타 선택법 보관 자료: `91.보관/` 하위에서 과목별로 확인 후 사용합니다.

## 결과물 저장
- 국제법 정리노트: `H:\내 드라이브\sync\노트\국제법\` 하위
- 법조윤리 정리노트: `H:\내 드라이브\sync\노트\법조윤리\` 하위
- 선택법 공통 산출물: `H:\내 드라이브\sync\노트\선택법\`이 없으면 루트 분류 규칙을 먼저 확인하고 생성 여부를 판단합니다.
- 새 추출본·OCR 산출물: 루트 `AGENTS.md`의 PDF·OCR 규칙 및 `.agent/workflows/classification-rules_v2.md`를 확인한 뒤 저장합니다.

## OCR 교정
- 추출: `.agent/notebooks/ocr_extract_v2.ipynb` 또는 `.agent/notebooks/ocr_extract_v2.py`
- 비교: `.agent/notebooks/ocr_compare_v2.ipynb` 또는 `.agent/notebooks/ocr_compare_v2.py`
- 교정: `.agent/scripts/haiku_ocr_correct.py`
- 검증: `.agent/scripts/sonnet_review.py`
- 적용: `.agent/scripts/apply_corrections.py`
- 조문·판례 검증은 루트 규칙에 따라 korean-law-mcp 또는 허용된 공적 원문 소스로 확인합니다.
