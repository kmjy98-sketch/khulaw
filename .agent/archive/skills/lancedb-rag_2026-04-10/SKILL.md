---
name: lancedb-rag
description: 벡터 검색 RAG 시스템. "검색", "인용", "관련 청크" 요청 시 사용.
---

# LanceDB RAG Skill

<!-- @rule: AGENTS.md#13-15 RAG 2.0 운영 -->
<!-- @rule: AGENTS.md#13-15 RAG 2.0 운영 -->
<!-- @rule: GEMINI.md#13-15 RAG 2.0 운영 -->

> 49개 교재 파일을 벡터 인덱싱하여 정밀한 페이지 인용 검색 제공

---

## Quick Start

### 검색

```powershell
python .agent/skills/lancedb-rag/scripts/search.py --query "동시이행항변권 요건"
```

### 인덱싱 (초기 1회)

```powershell
# 기본 인덱싱
python .agent/skills/lancedb-rag/scripts/ingest.py --dir "<청크폴더>"

# 목차 기반 챕터 메타데이터 포함
python .agent/skills/lancedb-rag/scripts/ingest.py --dir "<청크폴더>" --toc "<목차파일>"
```

---

## 주요 기능

### 1. 벡터 검색

```powershell
python scripts/search.py --query "검색어" --top_k 5
```

- 관련 청크 + 페이지 번호 + 챕터 정보 반환
- 소크라틱 문답 시 근거 인용에 활용

### 2. 배치 인덱싱

```powershell
python scripts/ingest.py --dir <청크폴더> [--toc <목차파일>] [--batch 10]
```

- `--- Page N ---` 마커 기준 페이지별 분할
- `--toc` 옵션: 목차 파일 기반 챕터 메타데이터 자동 추가
- 임베딩: `all-MiniLM-L6-v2`

---

## 데이터베이스

| 항목 | 경로 |
|------|------|
| DB 위치 | `%LOCALAPPDATA%/lancedb/law-study` |
| 청크 테이블 | `chunks` |
| 임베딩 차원 | 384 |

---

## 스키마

```python
{
    "chunk_id": str,       # "1-01_p001"
    "book_id": str,        # "민법_송영곤_기본민강_권리주체(26)"
    "book_code": str,      # "1-01"
    "page": int,           # 1
    "text": str,           # 청크 텍스트
    "chapter": str,        # "제1장 자연인" (목차 기반)
    "part": str,           # "제1편 권리의 주체와 대리" (목차 기반)
    "chapter_range": str,  # "p013-042" (목차 기반)
    "source_file": str,    # 원본 파일명
    "vector": List[float]  # 384 dim
}
```

---

## 워크플로우 연계

- `/socratic` → 검색 후 근거 인용
- 채점 → reverseRAG로 문장별 각주 강제

