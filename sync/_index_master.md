# 자료 인덱스 마스터 — 작업용 폴더 맵

> 생성: 2026-06-11 (D-1 간이판 — 작업용 폴더 기준). 세션 시작 시 위치 파악용.
> 상세 내용은 각 폴더의 manifest·진행상태 파일이 진실. 새 작업 폴더가 생기면 여기 한 줄 추가.

## 1. Anki 카드·덱 (md→Anki 파이프라인)

| 무엇 | 어디 |
|------|------|
| 임포트용 TSV 16파일 (#deck·html·줄바꿈 내장, 27,376장) | `outputs/anki/v4/` + `_manifest_v4.md` |
| 카드 원본 md 250여 개 (김준호* = 교수저, 임포트 제외) | `outputs/02_cards/` |
| 진행상태·임포트 계획 | `outputs/_진행상태_md2anki.md`, `outputs/_계획_위키화_카드임포트_2026-06-09.md` |
| 빌드 스크립트 (재빌드 시 한글화·줄바꿈·요건cloze 자동) | `.agent/scripts/anki_deck_build_v4.py` |
| 덱 구조·운영 가이드 (v4: 기본서/암기장-객·사례/교수저) | `프롬프트 등 개선/claude_code_package_v2/prompts/05_anki_덱구조_태그_모델라우팅.md` |

## 2. OCR·교재 추출본 (PDF 재추출 금지 — CLAUDE.md #46)

| 무엇 | 어디 |
|------|------|
| 교재 전권 OCR 마크다운 (책별 청크, 1차 소스) | `outputs/01_ocr_llamaparse/` |
| easyocr 구판 추출본 | `outputs/01_ocr/` |
| 스캔 원본 분할 PDF (대용량) | `작업용/{책}_chunks/` |
| 헌법 1-1 기말 추출본 (핵정·유니온 plumber/TOC) | `sync/1-1_기말/원문_추출본/`, `.agent/temp_toc/`, `.agent/temp_pdf_extract/` |
| 교재원문 md 백업 (라이브 `sync/_교재원문/`은 2026-05-22부터 비어 있음) | `sync/_백업/교재원문_문서_백업_2026-05-22/`, `.agent/data/ocr_chunks_reviewed/` |

## 3. Wiki (쟁점 아티클)

| 무엇 | 어디 |
|------|------|
| 쟁점 아티클 31개 (조문/요건+각주/일반론 판례/예외/클러스터) | `sync/wiki/쟁점/` — 진입점 `sync/wiki/_index.md` §III |
| 생성 규칙 (카드 roll-up) | `프롬프트 등 개선/claude_code_package_v2/prompts/03-wiki-rollup_쟁점아티클_v1.md` |
| 주제 태그 인벤토리 (13,112개) | `.agent/state/wiki_topic_inventory.json` |

## 4. 검증 상태

| 무엇 | 어디 |
|------|------|
| 사건번호 일괄 검증 결과 (7,493건 — verified 6,481·선고일 포함) | `.agent/state/anchor_verify_results.jsonl` + `anchor_verify_summary.md` |
| 검증 배치 스크립트 (law.go.kr DRF, 재실행 시 이어서) | `.agent/scripts/anchor_verify_batch.py` |
| 미교정: not_found 136건 + 카드 충돌 2건 | 칩 "검증 실패 사건번호 카드 교정" 참조 |

## 5. 헌법 원자료 (1-1 기말 작업분)

| 무엇 | 어디 |
|------|------|
| 핵정300·유니온·해커스 분할 PDF | `3.공법/_분할/` |
| 이진 강의자료·결정례 숙제 | `3.공법/10.이진_헌법원리1/` |
| 변시·모의 기출 PDF | `3.공법/90.기출/` |
| 기말 종합노트·계획서 | `sync/1-1_기말/` |

## 6. 도구 가용성 (검증 2026-05-25 ~ 06-11)

- **pdfplumber**(Python): 한글 추출 가장 안정 — 권장 / pdftotext: 빠르나 한자·기호 깨짐 / Read PDF(pdftoppm): 큰 PDF 실패
- **LlamaParse**(키 `.env`)·**easyocr 로컬**(`.agent/scripts/local_easyocr_*.py`): 스캔본 이미지 OCR
- **korean-law-mcp**(`.agent/skills/korean-law-mcp/.env`): 판례·조문 실시간 검증 — 대량은 `anchor_verify_batch.py`
