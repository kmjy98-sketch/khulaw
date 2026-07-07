---
name: pdf-ingest
description: 신규 PDF 교재/자료를 마크다운 청크로 추출 (qmd가 outputs/01_ocr_llamaparse/ 하위 자동 인덱싱, 구 경로 sync/_교재원문/는 이관됨, 2026-04-10 LanceDB 제거). 트리거 "PDF 인덱싱", "교재 등록", "pdf ingest", "새 교재"
---

`E:\법학볼트\.agent\skills\pdf-ingest\SKILL.md` 를 읽고 지침을 따른다.

신규 교재 투입 순서: `pdf-ingest` → `outputs/01_ocr_llamaparse/{과목}/{교재}/` 배치(#46 정본, 구 경로 `sync/_교재원문/{과목}/{교재}/`는 이관됨) → `qmd update && qmd embed` → `textbook-problem-intake` → `problem-index`
RAG 검색: qmd `law-notes` 컬렉션 (정리노트 + 교재원문 통합). helper: `.agent/lib/qmd_search.py`
