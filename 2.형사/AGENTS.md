# AGENTS.md

## 적용 범위
- 이 문서는 `H:\내 드라이브\2.형사` 하위 형사법 작업에 적용합니다.
- 루트 `H:\내 드라이브\AGENTS.md`를 함께 적용합니다. 충돌 시 과목별 자료 위치·우선순위는 이 문서를 우선합니다.
- 법리·사실 단정은 루트 근거 규칙에 따라 사용자 제공 소스와 정확한 위치가 있을 때만 출력합니다.

## 교재 우선순위
- 김기용 자료(우선, 기본강의) > 서보학 자료(학설 설명) > 김성돈 자료(보완)
- 서보학 교수님 난이도 상승 추세와 변사기 쟁점 복합 출제 대비를 반영합니다.
- 홍형철 자료는 판례 원문 확인용으로만 사용합니다.

## 과목별 기준
- 형법1: 서보학 교수님 주장 종합표를 유지하고, 객관적 귀속설·개괄적 고의 쟁점을 반영합니다.
- 위전착 판례: 엄격책임설 관련 기존 오류 수정 취지를 유지하되, 사건번호·판례 원문은 반드시 재확인합니다.

## 현재 확인된 자료 위치
- 김기용 형법총론: `김기용형총/`
- 반반형법: `반반형법/`
- 작은변사기: `작은변사기/`
- compact 형총 OX: `compact형총OX/`
- 서보학 형법2 및 보관 자료: `91.보관/서보학_형법2/`
- 김성돈·이인규 자료는 현재 직접 경로가 확인되지 않았으므로, 사용 전 파일 검색으로 위치를 확인합니다.

## 결과물 저장
- 정리노트: `H:\내 드라이브\sync\노트\형법\` 하위
- 답안·사례 연습 산출물: `H:\내 드라이브\sync\노트\답안\` 또는 루트 분류 규칙의 해당 위치
- 새 추출본·OCR 산출물: 루트 `AGENTS.md`의 PDF·OCR 규칙 및 `.agent/workflows/classification-rules_v2.md`를 확인한 뒤 저장합니다.

## OCR 교정
- 추출: `.agent/notebooks/ocr_extract_v2.ipynb` 또는 `.agent/notebooks/ocr_extract_v2.py`
- 비교: `.agent/notebooks/ocr_compare_v2.ipynb` 또는 `.agent/notebooks/ocr_compare_v2.py`
- 교정: `.agent/scripts/haiku_ocr_correct.py`
- 검증: `.agent/scripts/sonnet_review.py`
- 적용: `.agent/scripts/apply_corrections.py`
- 조문·판례 검증은 루트 규칙에 따라 korean-law-mcp 또는 허용된 공적 원문 소스로 확인합니다.
