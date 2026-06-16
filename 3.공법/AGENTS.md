# AGENTS.md

## 적용 범위
- 이 문서는 `H:\내 드라이브\3.공법` 하위 공법 작업에 적용합니다.
- 루트 `H:\내 드라이브\AGENTS.md`를 함께 적용합니다. 충돌 시 과목별 자료 위치·우선순위는 이 문서를 우선합니다.
- 법리·사실 단정은 루트 근거 규칙에 따라 사용자 제공 소스와 정확한 위치가 있을 때만 출력합니다.

## 교재 우선순위
- 이진 자료(우선, 범위 한정) > 강성민 자료(전범위 OX·변사기)
- 헌법1 기말 범위는 통치구조 중심으로 처리하고, 기본권은 범위 외인지 먼저 확인합니다.
- 사례용 판례 정리와 객관식 숫자 정리를 병행합니다.

## 과목별 기준
- 헌법1: 이진 PPT와 결정례 숙제를 우선하고, OX는 강성민 자료를 참조합니다.
- 헌정사: 차수(제X공화국) 옆에 정권명(이승만, 장면 등)을 병기합니다.

## 현재 확인된 자료 위치
- 이진 헌법원리1 자료: `_강의/1-1_지난학기/10.이진_헌법원리1/`, `94.교재/`, `96.기타/`
- 헌법300: `헌법300/`
- 해커스 헌법 사례: `해커스헌사례/`
- 유니온 헌법 객관식: `유니온헌객/`
- 강성민 헌법 OX: `강성민헌법OX/`
- 강성민 단권화노트·보관 자료: `91.보관/`

## 결과물 저장
- 정리노트: `H:\내 드라이브\sync\노트\헌법\` 하위
- 답안·사례 연습 산출물: `H:\내 드라이브\sync\노트\답안\` 또는 루트 분류 규칙의 해당 위치
- 새 추출본·OCR 산출물: 루트 `AGENTS.md`의 PDF·OCR 규칙 및 `.agent/workflows/classification-rules_v2.md`를 확인한 뒤 저장합니다.

## OCR 교정
- 추출: `.agent/notebooks/ocr_extract_v2.ipynb` 또는 `.agent/notebooks/ocr_extract_v2.py`
- 비교: `.agent/notebooks/ocr_compare_v2.ipynb` 또는 `.agent/notebooks/ocr_compare_v2.py`
- 교정: `.agent/scripts/haiku_ocr_correct.py`
- 검증: `.agent/scripts/sonnet_review.py`
- 적용: `.agent/scripts/apply_corrections.py`
- 조문·판례 검증은 루트 규칙에 따라 korean-law-mcp 또는 허용된 공적 원문 소스로 확인합니다.
