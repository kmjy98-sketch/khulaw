---
name: pdf-ingest
description: PDF → 마크다운 청크 추출. 네이티브(pypdf/pdfplumber)와 스캔본(easyocr OCR) 양쪽 지원. 표 구조 자동 탐지·마크다운 변환 + 페이지 경계 문맥 복원. "PDF 인덱싱", "교재 추출", "PDF 읽어줘", "PDF 내용", "스캔본 OCR", "PDF 마크다운화" 요청 시 사용. (2026-04-24 표 탐지·pdfplumber 추가, 2026-04-10 LanceDB 인덱싱 제거)
---

# PDF Ingest Skill

<!-- @rule: CLAUDE.md#9 PDF Handling -->

PDF → 마크다운 청크 추출 전용. 인덱싱은 `outputs/01_ocr_llamaparse/` 하위에 파일 배치 후 `qmd update && qmd embed`가 자동 처리한다(#46 정본. 구 경로 `sync/_교재원문/`은 이관됨).

---

## Quick Start

### 배치 추출

```powershell
# 전체 추출
python .agent/skills/pdf-ingest/scripts/ingest.py --pdf-dir <폴더> --out <출력폴더>

# 패턴 지정
python .agent/skills/pdf-ingest/scripts/ingest.py --pdf-dir <폴더> --out <출력폴더> --pattern "**/1-*.pdf"
```

### 후속 단계 (인덱싱)

```powershell
# 1) 추출된 청크를 outputs/01_ocr_llamaparse/{과목}/{교재}/ 하위로 배치 (#46 정본, 구 경로 sync/_교재원문/는 이관됨)
# 2) qmd 재인덱싱
qmd update
qmd embed
```

### 단일 파일 텍스트 추출

```powershell
python .agent/skills/pdf-ingest/scripts/pdf_reader.py <pdf_path> [--output <output.md>] [--pages <1-10>]
```

**옵션:**

- `--output, -o`: 출력 파일 경로 (.md 또는 .txt)
- `--pages, -p`: 페이지 범위 (예: 1-10)
- `--quiet, -q`: 콘솔 출력 생략

---

## 폴백 전략

PDF 텍스트 추출 시 다음 순서로 시도:

1. **Native 우선**: Claude API에 PDF 직접 전달 시도
2. **폴백 A - pypdf 페이지별 추출**: 인식 실패 시 → `pdf_reader.py --pages` 분할 추출
3. **폴백 B - 배치 처리**: 대용량(>50MB) 시 → 30페이지 단위 배치 처리 (`ingest.py`)
4. **폴백 C - OCR (스캔본)**: `pypdf`로 텍스트가 거의 빈값이면 → `ocr_extract.py` (easyocr + pymupdf) 사용
5. **리플로우**: 추출 결과가 구조가 깨져 있으면 → `textbook-reflow` 스킬로 Obsidian 최적 레이아웃으로 재정렬

---

## OCR 경로 (스캔본 PDF 전용)

`pypdf`는 텍스트 레이어가 없는 스캔본에서 빈 문자열을 반환한다. 이 경우 `ocr_extract.py`를 사용.

### 사용법

```powershell
# 기본 (전체 페이지, 30페이지 청크, 200 DPI)
python .agent/skills/pdf-ingest/scripts/ocr_extract.py --pdf "2.형사/20.서보학_형법1/교재/서보학_형법총론_18.pdf" --out "pdf_extracts/서보학"

# 페이지 범위 제한 + DPI 조정
python .agent/skills/pdf-ingest/scripts/ocr_extract.py --pdf <pdf경로> --out <출력> --start 50 --end 200 --dpi 250 --chunk-size 20
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--pdf` | (필수) | PDF 경로 |
| `--out` | (필수) | 청크 출력 폴더 |
| `--chunk-size` | 30 | 페이지 분할 단위 |
| `--dpi` | 200 | 렌더링 해상도 (높을수록 정확·느림) |
| `--start` | 1 | 시작 페이지 (1-base) |
| `--end` | 0 | 종료 페이지 (0=마지막) |

### 의존성

- `pymupdf` (fitz) — 페이지 렌더링
- `easyocr` — 한국어/영어 OCR (GPU 없이 CPU 모드, 최초 실행 시 모델 다운로드)

```powershell
pip install pymupdf easyocr
```

### 스캔본 판별

추출 결과가 빈 문자열이거나 페이지당 50자 미만이면 스캔본으로 간주. `ocr_test.py`로 샘플 페이지(예: 50·100·200 페이지) 품질 확인 가능.

### 성능 기준

- 200 DPI 기준: 페이지당 약 3~6초 (CPU)
- 청크 단위 증분 저장 — 중단 후 재실행 시 동일 source는 chunks만 재갱신

---

## 주요 옵션 (배치)

| 옵션 | 설명 |
|------|------|
| `--pdf-dir` | PDF 소스 디렉토리 (필수) |
| `--out` | 마크다운 출력 디렉토리 |
| `--pattern` | 파일 패턴 (예: `**/1-*.pdf`) |
| `--chunk-size` | 페이지 분할 단위 (기본 30) |
| `--index` / `--index-only` / `--md-dir` / `--reset` | **폐기됨** (경고만 출력). qmd가 자동 인덱싱. 레거시 코드: `scripts/_legacy/ingest_with_lancedb.py` |

---

## 출력 형식

```markdown
--- Page 1 ---
[페이지 1 텍스트 또는 마크다운 표]

--- Page 2 ---
[페이지 2 텍스트]
...
```

- 배치 마크다운: `{out_dir}/{파일명}_p001-030.md`
- 청크 인덱스: `{out_dir}/chunks_index.json`
- **표 블록**: 표 구조가 탐지되면 청크 내부에 `| 헤더 | 헤더 |` 마크다운 표로 삽입
- **페이지 병합**: 이전 페이지가 종결기호 없이 끝나고 다음 페이지가 조사로 시작하면 `--- Page N ---` 마커 제거 후 본문 이어 붙임 → 페이지 마커 개수가 원본 페이지 수와 다를 수 있음
- **인덱싱 대상**: `outputs/01_ocr_llamaparse/` 하위 배치 후 qmd law-notes 컬렉션이 자동 처리(#46 정본, 구 경로 `sync/_교재원문/`는 이관됨)

---

## 표 구조 탐지 (2026-04-24)

### 네이티브(pdfplumber) 경로
- `ingest.py`는 `pdfplumber.page.find_tables()`를 우선 시도하고, 표 영역을 제외한 나머지 텍스트는 Y 순서로 인터리브
- 미설치/실패 시 pypdf로 자동 폴백

### OCR(easyocr) 경로
- `ocr_extract.py`는 `detail=1, paragraph=False`로 바운딩박스 확보
- Y 좌표 ±18px 클러스터 → 행, 여러 행에서 반복되는 X 좌표 → 컬럼 앵커
- 연속 3행+ 다중 컬럼 감지 시 마크다운 표로 변환, 그 외는 줄글 이어붙임

### 사후 처리
- 기존 추출 .md 파일의 표 구조 복원은 `.agent/scripts/fix_table_structure.py` 별도 실행
- 백업: `5.기타/교재원문_백업/{date}/table_fix/`

### `reflow_batch.py` 연동 주의
- `|` 시작 줄은 표 행으로 간주하고 병합 대상에서 제외됨 (2026-04-24 수정)
- OCR 후처리 3종(`fix_ocr_hanja/line_breaks/spacing.py`)은 표 행을 이미 정상 보존

---

---

## 의존성

- `pypdf` — 네이티브 PDF 추출 (자동 설치)
- `pymupdf` + `easyocr` — OCR 경로 (스캔본, 수동 설치 필요)

---

## 파이프라인 위치

```
PDF 원본
  ↓
pdf-ingest (← 본 스킬)
  ├─ 네이티브: ingest.py / pdf_reader.py (pypdf)
  └─ 스캔본:   ocr_extract.py (easyocr+pymupdf)
  ↓
textbook-reflow (OCR 후처리·구조 정리)
  ↓
outputs/01_ocr_llamaparse/{과목}/{교재}/  (#46 정본, 구 경로 sync/_교재원문/는 이관됨)
  ↓
qmd update && qmd embed  (자동 인덱싱)
  ↓
socratic-core / law-note-supplement / case-answer-review (RAG 검색)
```

---

## 관련 작업

- 교재 페이지 인용 시 사용
- 전사문 교정 시 원본 대조용
- qmd RAG 검색 대상 추가 (outputs/01_ocr_llamaparse/ 배치, #46 정본)
- OCR 산출물의 Obsidian 최적화 → `textbook-reflow` 스킬 연계

