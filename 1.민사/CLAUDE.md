# 민법 작업 규칙

## 교재 우선순위
- 송영곤(전체 구성+사례) > 강혜림(민1 학설·판례) > 전경운(민3 학설·판례)
- 전경운 교수님 고유 표현은 [전경운] 태그로 별도 표시
- 강혜림 교수님 강조 요건은 우선 반영

## 과목별 세부
- 민법1 (강혜림): 김준호 《민법강의》 참조, 요건사실론 기반 청구-항변 구조
- 민법3 (전경운): 송영곤 《논점민법강의》 우선, 전경운 교재 학설 보강

## 결과물 저장
- 정리노트: sync/노트/민법/ 하위
- 답안·사례 연습 산출물: sync/노트/답안/
- 교재 추출본 백업: 5.기타/교재원문_백업/sync이관_2026-06-11/ (구 sync/_교재원문, 2026-06-11 이관)
- 암기장: outputs/02_cards_v37/ (md→Anki 카드 빌드 산출) 또는 sync/노트/민법/ 하위

## 소스 파일 위치
- 송영곤 기본민강: 30.송영곤_기본민법/
- 송영곤 쟁점노트: 31.송영곤_사례/ + 32.송영곤_사례연습2/
- 강혜림 교재: 10.강혜림_민법1/
- 전경운 교재: 20.전경운_민법3/

## OCR 교정 (LlamaParse 로컬 — Colab 폐기 2026-06-21, 루트 CLAUDE.md #13 준수)
- 추출 (LlamaParse 로컬): → `outputs/01_ocr_llamaparse/`  (구 Colab 노트북 ocr_extract_v2·ocr_compare_v2.ipynb은 레거시·연동끊김 — 신규작업 미사용)
- 교정 (Claude Code): `python .agent/scripts/haiku_ocr_correct.py`
- 검증 (Claude Code): `python .agent/scripts/sonnet_review.py`
- 적용 (Claude Code): `python .agent/scripts/apply_corrections.py`
- 조문/판례 검증: `.auto-memory/ocr_state/verification_targets.json` → `python .agent/lib/law_api.py verify-text`(직접 API, MCP 은퇴)
