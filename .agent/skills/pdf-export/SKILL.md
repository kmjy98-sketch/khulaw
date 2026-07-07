---
name: pdf-export
description: 정리노트 마크다운(.md) → PDF 배치 변환. playwright+Chromium 렌더링, A4 레이아웃, 한국어 서체. "PDF 변환", "정리노트 PDF", "md to pdf", "노트 출력" 요청 시 사용.
---

# PDF Export Skill

<!-- @rule: CLAUDE.md#8 Output Minimalism -->
<!-- @rule: CLAUDE.md #42 파일 생성 위치(비노트 산출 문서) -->

마크다운 정리노트를 시험용 A4 PDF로 배치 변환한다. 추출(PDF → md)은 `pdf-ingest`, 이 스킬은 **출력(md → PDF)** 전용.

---

## Quick Start

### 단일/다중 파일 변환

```powershell
# 단일 .md 파일
python .agent/skills/pdf-export/generate_notes_pdf.py --src "sync/민법/쟁점노트.md" --out "5.기타/정리노트PDF/2026-04-21"

# 폴더 내 모든 .md 일괄
python .agent/skills/pdf-export/generate_notes_pdf.py --src "sync/민법" --out "5.기타/정리노트PDF/2026-04-21"

# 여러 소스 혼합
python .agent/skills/pdf-export/generate_notes_pdf.py --src "파일1.md" "파일2.md" "폴더/" --out "출력폴더"
```

### 출력 경로 규정

CLAUDE.md #42(파일 생성 위치)에 따라 모든 PDF 산출물은 다음 경로에 둔다:

```
5.기타/정리노트PDF/{YYYY-MM-DD}/
  ├─ 1-1_중간/   (중간고사 대비)
  └─ 1-1_기말/   (기말고사 대비)
```

**금지**: `sync/` 볼트(Obsidian, .md 전용)에 PDF 저장 금지.

---

## 주요 옵션

| 옵션 | 설명 |
|------|------|
| `--src` | 소스 `.md` 파일 또는 폴더 (공백 구분 다중 지정 가능, 필수) |
| `--out` | PDF 출력 폴더 (필수, 자동 생성) |

폴더 지정 시 **최상위 `.md`만** 재귀 없이 수집(`p.glob("*.md")`).

---

## 출력 형식

- **용지**: A4 (210×297mm)
- **여백**: 상하 15mm, 좌우 12mm
- **서체**: Malgun Gothic / 맑은 고딕 (한글 기본)
- **본문**: 10pt / line-height 1.6
- **헤딩**: H1 18pt · H2 14pt · H3 12pt
- **테이블**: 9pt · 줄무늬 · 회색 헤더
- **각주**: 8.5pt · 구분선

CSS는 `generate_notes_pdf.py` 상단 `CSS` 변수에 인라인 정의. 수정 시 해당 파일 직접 편집.

---

## Markdown 확장 기능

`markdown` 파이썬 패키지의 다음 확장을 활성화:

- `tables` — 표
- `fenced_code` — \`\`\`코드블록
- `toc` — 자동 목차 (`[TOC]` 지시어)
- `footnotes` — 각주 (`[^1]` 형식, CLAUDE.md §1-4 준수)
- `nl2br` — 줄바꿈을 `<br>`로 처리

---

## 의존성

- `markdown` (파이썬) — `pip install markdown`
- `playwright` + Chromium — `pip install playwright && playwright install chromium`

Chromium 미설치 시 `playwright install chromium` 선행 필요.

---

## 파이프라인 위치

```
study-notes / law-note-supplement  (노트 작성·보완)
  ↓
sync/{과목}/*.md                    (Obsidian 볼트, qmd 인덱싱 대상)
  ↓
pdf-export  (← 본 스킬, 시험 직전 출력)
  ↓
5.기타/정리노트PDF/{YYYY-MM-DD}/
```

---

## 관련 작업

- 시험 직전 `.md` → PDF 일괄 출력
- 오프라인 열람·인쇄용 배포본 생성
- 중간·기말 대비 pack 빌드 (`card-wiki-pipeline.md` 워크플로우 연계)

---

## 제약 사항

- `sync/` 볼트에 PDF를 **저장하면 안 됨** (CLAUDE.md #42).
- Mermaid·KaTeX 등 고급 렌더링은 현재 미지원(필요 시 CSS·확장 추가 후 확장).
- 한자 렌더링은 시스템 서체 의존. CLAUDE.md 피드백(feedback_no_hanja)에 따라 노트 원본 단계에서 한자 제거 권장.
