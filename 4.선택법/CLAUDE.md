# 선택법 작업 규칙

## 과목
- 국제법: 기출 + 빈출 + 선배 찌라시 합치기
- 법조윤리: 기출별 주요 문항 정리 (한권탁 기출 참조)

## 결과물 저장
- 국제법 정리노트: sync/노트/국제법/ 하위
- 법조윤리 정리노트: sync/노트/법조윤리/ 하위
- 선택법 공통 산출물: sync/노트/선택법/ (없으면 루트 분류 규칙 확인 후 생성 판단)

## 상태
- 국제법·법조윤리 정리본 산출 진행(상태는 4.선택법/AGENTS.md 자료 위치 기준으로 관리)

## OCR 교정 (marker-pdf 파이프라인)
- 추출 (Colab): `.agent/notebooks/ocr_extract_v2.ipynb` → `sync/_ocr_extracted/`
- 비교 (Colab): `.agent/notebooks/ocr_compare_v2.ipynb` → `.auto-memory/ocr_state/corrections/{교재}.jsonl`
- 교정 (Claude Code): `python .agent/scripts/haiku_ocr_correct.py`
- 검증 (Claude Code): `python .agent/scripts/sonnet_review.py`
- 적용 (Claude Code): `python .agent/scripts/apply_corrections.py`
- 조문/판례 검증: `.auto-memory/ocr_state/verification_targets.json` → korean-law-mcp
