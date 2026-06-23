# 헌법 작업 규칙

## 교재 우선순위
- 이진(우선, 범위 한정 — 중간: 헌법총론, 기말: 통치구조) > 강성민(전범위, OX+변사기)
- 헌법1 기말 = 통치구조만 (기본권은 범위 외)
- 사례용 판례 + 객관식 숫자 정리 병행

## 과목별 세부
- 헌법1 (이진): PPT + 결정례 숙제 기반, OX는 강성민 교재 참조
- 헌정사: 차수(제X공화국) 옆에 정권명(이승만, 장면 등) 반드시 병기

## 결과물 저장
- 정리노트: sync/노트/헌법/ 하위
- 답안·사례 연습 산출물: sync/노트/답안/
- 교재 추출본 백업: 5.기타/교재원문_백업/sync이관_2026-06-11/ (구 sync/_교재원문)
- 암기장: outputs/02_cards_v37/ 또는 sync/노트/헌법/ 하위

## 소스 파일 위치
- 이진 자료: 10.이진_헌법원리1/
- 강성민 OX: 강성민헌법OX/ (3.공법/AGENTS.md 기준)
- 강성민 단권화노트·보관 자료: 91.보관/ (3.공법/AGENTS.md 기준)

## OCR 교정 (LlamaParse 로컬 — Colab 폐기 2026-06-21, 루트 CLAUDE.md #13 준수)
- 추출 (LlamaParse 로컬): → `outputs/01_ocr_llamaparse/`  (구 Colab 노트북 ocr_extract_v2·ocr_compare_v2.ipynb은 레거시·연동끊김 — 신규작업 미사용)
- 교정 (Claude Code): `python .agent/scripts/haiku_ocr_correct.py`
- 검증 (Claude Code): `python .agent/scripts/sonnet_review.py`
- 적용 (Claude Code): `python .agent/scripts/apply_corrections.py`
- 조문/판례 검증: `.auto-memory/ocr_state/verification_targets.json` → `python .agent/lib/law_api.py verify-text`(직접 API, MCP 은퇴)
