# 형법 작업 규칙

## 교재 우선순위
- 김기용(우선, 기본강의) > 서보학(학설 설명) > 김성돈(보완)
- 서보학 교수님 난이도 상승 추세 반영 — 변사기 쟁점 복합 출제 대비
- 홍형철 자료는 판례 원문 확인용

## 과목별 세부
- 형법1 (서보학): 교수님 주장 종합표 유지, 객관적 귀속설(개괄적 고의) 반영
- 위전착 판례: 엄격책임설(68도370) — 기존 오류 수정됨

## 결과물 저장
- 정리노트: sync/노트/형법/ 하위
- 답안·사례 연습 산출물: sync/노트/답안/
- 교재 추출본 백업: 5.기타/교재원문_백업/sync이관_2026-06-11/ (구 sync/_교재원문)
- 암기장: outputs/02_cards_v37/ 또는 sync/노트/형법/ 하위

## 소스 파일 위치
- 김기용 교안: 교재 추출본 내
- 서보학 교재: 20.서보학_형법1/
- 김성돈: 경로 미확인 — 사용 전 파일 검색으로 위치 확인
- 이인규 변사기: 경로 미확인 — 사용 전 파일 검색으로 위치 확인

## OCR 교정 (LlamaParse 로컬 — Colab 폐기 2026-06-21, 루트 CLAUDE.md #13 준수)
- 추출 (LlamaParse 로컬): → `outputs/01_ocr_llamaparse/`  (구 Colab 노트북 ocr_extract_v2·ocr_compare_v2.ipynb은 레거시·연동끊김 — 신규작업 미사용)
- 교정 (Claude Code): `python .agent/scripts/haiku_ocr_correct.py`
- 검증 (Claude Code): `python .agent/scripts/sonnet_review.py`
- 적용 (Claude Code): `python .agent/scripts/apply_corrections.py`
- 조문/판례 검증: `.auto-memory/ocr_state/verification_targets.json` → `python .agent/lib/law_api.py verify-text`(직접 API, MCP 은퇴)
